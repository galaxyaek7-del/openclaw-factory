"""Galaxy Forge read-only MCP pilot server (2026-10-15).

A Model Context Protocol server over STDIO: newline-delimited JSON-RPC 2.0
on stdin/stdout, as the MCP stdio transport specifies. It opens no network
listener. Approved as "Option B" in reports/MCP_FEASIBILITY_AUDIT_2026-10-15.md.

It exposes seven READ-ONLY tools, each a thin wrapper over code or files that
already exist and are already tested:

  ci_status               ci_health_detector.detect()   (anonymous GitHub GETs)
  write_gate_status       data/gumroad_auth_state.json  (status + age only)
  verify_render           kids_studio/tools/verify_video.analyze()
  factory_products        data/product_registry.json                 (2026-10-24)
  distribution_status     data/distribution_dashboard.json           (2026-10-24)
  pinterest_queue_status  data/pinterest_queue.json + Metricool records (2026-10-24)
  video_studio_status     video_studio/projects + build records      (2026-10-24)
The four 2026-10-24 tools read fixed files only: no arguments, no caller path.

What it deliberately does NOT do:
  * no shell, no eval, no generic file read/write, no generic HTTP
  * never writes the CI ledger (ci_health_detector.record_state is not called)
  * never calls channels/write_gate.check_write_authorization(): with the
    live flag on, that function fingerprints the live Gumroad credential.
    This server never loads a credential, never reads .env, and never returns
    the recorded fingerprint, a hash, or a token.
  * never writes a .verify.json (analyze() is the write-free half of verify_video)

Run with `python -E -P mcp_pilot/gf_readonly_server.py`: -P keeps the current
directory and the script directory off sys.path, so a stray `select.py` or
`json.py` cannot shadow the standard library. (-I would also drop the user
site-packages, where numpy lives on this machine.) Project modules are loaded
by explicit file path, never through sys.path.

Every call is logged to logs/mcp_readonly_calls.jsonl: tool, sanitised
arguments, status, duration. Never the result body, never a secret.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _drop_unsafe_sys_path():
    """Defence in depth for the import-shadowing class: drop the current
    directory and this script's directory even if the server was started
    without -P. Runs only when this file is the server process (__main__);
    doing it at import time also stripped the repo root from any process that
    merely imported the module, e.g. a pytest run collecting its tests."""
    sys.path[:] = [p for p in sys.path
                   if p not in ("", ".") and Path(p or ".").resolve() not in (Path.cwd().resolve(), _HERE)]


ROOT = _HERE.parent
RENDERS = (ROOT / "kids_studio" / "renders").resolve()
AUTH_STATE = ROOT / "data" / "gumroad_auth_state.json"
LOG = Path(os.environ.get("GF_MCP_CALL_LOG") or ROOT / "logs" / "mcp_readonly_calls.jsonl")   # override: tests only

SERVER_INFO = {"name": "gf-readonly", "version": "0.2.0"}
SUPPORTED_PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
MAX_RESULT_CHARS = 20_000
CI_TIMEOUT_S = 120
VIDEO_TIMEOUT_S = 300
MAX_VIDEO_BYTES = 2 * 1024 ** 3
STALE_AFTER_S = 3600          # same threshold as channels/write_gate.py

_SHA = re.compile(r"^[0-9a-f]{7,40}$")


# --------------------------------------------------------------------------
# sanitising
# --------------------------------------------------------------------------

_SECRET_SHAPES = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"),                 # Telegram bot token
    re.compile(r"(?i)(access_token|api[_-]?key|token|secret|password)=[^&\s\"']+"),
]
_LONG_HEX = re.compile(r"\b[0-9a-fA-F]{16,}\b")
_LONG_OPAQUE = re.compile(r"[A-Za-z0-9_\-]{36,}")


def _known_fingerprint():
    try:
        return str(json.loads(AUTH_STATE.read_text(encoding="utf-8")).get("fingerprint_prefix") or "")
    except (OSError, ValueError):
        return ""


def sanitize_text(s: str) -> str:
    """Redact anything shaped like a credential, hash or fingerprint.

    A 40-character hex string is a git commit id and is kept; every other hex
    run of 16+ characters (SHA-256 digests, the 16-char auth fingerprint) is
    redacted, as is any long opaque token.
    """
    fp = _known_fingerprint()
    if fp:
        s = s.replace(fp, "[REDACTED]")
    for pat in _SECRET_SHAPES:
        s = pat.sub("[REDACTED]", s)
    s = _LONG_HEX.sub(lambda m: m[0] if len(m[0]) == 40 else "[REDACTED]", s)
    s = _LONG_OPAQUE.sub(lambda m: m[0] if _SHA.match(m[0]) else "[REDACTED]", s)
    return s


def sanitize(obj):
    if isinstance(obj, str):
        return sanitize_text(obj)
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    return obj


def _log(tool, args, status, started, error=None):
    rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tool": tool,
           "args": sanitize(args), "status": status,
           "duration_ms": int((time.monotonic() - started) * 1000)}
    if error:
        rec["error"] = sanitize_text(str(error))[:300]
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass                                  # logging must never break a read


class ToolError(Exception):
    """A clear, user-facing refusal or failure. Returned with isError=true."""


# --------------------------------------------------------------------------
# module loading by explicit path (never via sys.path)
# --------------------------------------------------------------------------

_MODULES = {}


def _load(name, rel):
    if name not in _MODULES:
        spec = importlib.util.spec_from_file_location(name, ROOT / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODULES[name] = mod
    return _MODULES[name]


def _with_timeout(fn, seconds):
    box = {}

    def target():
        try:
            box["value"] = fn()
        except Exception as exc:              # noqa: BLE001
            box["error"] = exc

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive():
        raise TimeoutError(f"no result within {seconds}s")
    if "error" in box:
        raise box["error"]
    return box["value"]


# --------------------------------------------------------------------------
# tools
# --------------------------------------------------------------------------

def _git_rev(ref):
    p = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", ref + "^{commit}"],
                       capture_output=True, text=True, timeout=15,
                       stdin=subprocess.DEVNULL)   # never share the JSON-RPC pipe with a child
    if p.returncode != 0:
        raise ToolError(f"git could not resolve {ref}")
    return p.stdout.strip()


def tool_ci_status(args):
    sha = args.get("commit_sha")
    ref = args.get("ref", "origin/main")
    if sha is not None:
        if not isinstance(sha, str) or not _SHA.match(sha):
            raise ToolError("commit_sha must be 7-40 lowercase hex characters")
    else:
        if ref not in ("origin/main", "HEAD"):
            raise ToolError("ref must be 'origin/main' or 'HEAD'")
        sha = _git_rev(ref)
    det = _load("gf_ci_health_detector", "ci_health_detector.py")
    try:
        verdict, reason, payload = _with_timeout(lambda: det.detect(sha), CI_TIMEOUT_S)
    except TimeoutError as exc:
        return {"status": "BLOCKED", "commit_sha": sha, "reason": f"GitHub evidence not readable: {exc}"}
    ev = payload.get("evidence", {})
    err = ev.get("evidence_error") or ""
    network = bool(err) and not err.startswith("no workflow runs") and not err.startswith("no commit")
    jobs = ev.get("jobs") or []
    conclusions = {}
    for j in jobs:
        conclusions[j.get("conclusion") or j.get("status") or "none"] = conclusions.get(
            j.get("conclusion") or j.get("status") or "none", 0) + 1
    return {
        # BLOCKED here means "could not read the evidence" (no network / API refusal);
        # the detector's own verdict is reported separately and never upgraded.
        "status": "BLOCKED" if network else verdict,
        "detector_verdict": verdict,
        "reason": reason,
        "commit_sha": sha,
        "collected_at": ev.get("collected_at"),
        "runs": [{k: r.get(k) for k in ("name", "status", "conclusion")} for r in (ev.get("runs") or [])][:15],
        "job_count": len(jobs),
        "job_conclusions": conclusions,
        "detail": payload.get("detail") or {},
        "evidence_error": err or None,
    }


def tool_write_gate_status(args):
    if args:
        raise ToolError("write_gate_status takes no arguments")
    flag_raw = os.environ.get("FACTORY_LIVE_PUBLISH")
    flag_on = str(flag_raw or "").strip().lower() in ("1", "true", "yes", "on")
    try:
        state = json.loads(AUTH_STATE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        state = None
    except (OSError, ValueError) as exc:
        raise ToolError(f"auth state unreadable ({type(exc).__name__})")
    out = {
        "gate_module_present": (ROOT / "channels" / "write_gate.py").is_file(),
        "scope_module_present": (ROOT / "channels" / "write_scope.py").is_file(),
        "live_publish_flag_in_this_process": flag_on,
        "live_publish_flag_source": ("process environment of this MCP server only; "
                                     ".env is not read by design, so the flag seen by other "
                                     "factory processes is UNKNOWN here"),
        "auth_state": None,
    }
    if state is not None:
        at = state.get("at")
        age = None
        try:
            ts = datetime.fromisoformat(str(at))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = int(time.time() - ts.timestamp())
        except (TypeError, ValueError):
            pass
        # Only these three fields leave the server; fingerprint_prefix never does.
        out["auth_state"] = {"status": state.get("status"), "recorded_at": at, "age_seconds": age,
                             "stale": None if age is None else age > STALE_AFTER_S}
    # The observable part of the gate's decision. The credential-fingerprint
    # step is never performed here, so ALLOW can never be asserted.
    if not flag_on:
        decision, why = "DENY", "FACTORY_LIVE_PUBLISH is not true in this process and no scope was supplied"
    elif state is None:
        decision, why = "DENY", "no auth state on record"
    elif out["auth_state"]["status"] != "VERIFIED":
        decision, why = "DENY", f"auth state is {out['auth_state']['status']}, not VERIFIED"
    elif out["auth_state"]["stale"] is not False:
        decision, why = "DENY", "auth state is stale or undated"
    else:
        decision, why = "UNKNOWN", "remaining check (live credential fingerprint) is not performed by this read-only tool"
    out["observable_decision"] = decision
    out["observable_reason"] = why
    return out


def _render_path(raw):
    if not isinstance(raw, str) or not raw or len(raw) > 260:
        raise ToolError("path must be a non-empty string")
    if "\x00" in raw:
        raise ToolError("path contains a NUL byte")
    p = Path(raw)
    if not p.is_absolute():
        p = ROOT / p
    try:
        real = p.resolve(strict=True)           # follows symlinks and junctions
    except (OSError, RuntimeError):
        raise ToolError("file not found")
    if real != RENDERS and RENDERS not in real.parents:
        raise ToolError("path is outside kids_studio/renders")
    if real.suffix.lower() != ".mp4":
        raise ToolError("only .mp4 files can be verified")
    if not real.is_file():
        raise ToolError("not a regular file")
    if real.stat().st_size > MAX_VIDEO_BYTES:
        raise ToolError("file larger than the 2 GB limit")
    return real


def tool_verify_render(args):
    extra = set(args) - {"path"}
    if extra:
        raise ToolError(f"unexpected argument(s): {sorted(extra)}")
    real = _render_path(args.get("path"))
    vv = _load("gf_verify_video", "kids_studio/tools/verify_video.py")
    try:
        rep = vv.analyze(real, timeout=VIDEO_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise ToolError(f"verification exceeded {VIDEO_TIMEOUT_S}s per FFmpeg step")
    rep["file"] = str(real.relative_to(ROOT)).replace("\\", "/")
    return {"status": rep["verdict"], **rep}


# --- factory state readers (2026-10-24) -------------------------------------
# Each reads fixed, already-committed files under data/ or video_studio/; no
# arguments, no path from the caller, no network, no .env, nothing written.

PRODUCT_REGISTRY = ROOT / "data" / "product_registry.json"
DIST_DASHBOARD = ROOT / "data" / "distribution_dashboard.json"
PINTEREST_QUEUE = ROOT / "data" / "pinterest_queue.json"
METRICOOL_BRAND = ROOT / "data" / "metricool_brand.json"
METRICOOL_ATTEMPTS = ROOT / "data" / "metricool_submissions.jsonl"
VIDEO_PROJECTS = ROOT / "video_studio" / "projects"
VIDEO_OUTPUT = ROOT / "video_studio" / "output"


def _no_args(name, args):
    if args:
        raise ToolError(f"{name} takes no arguments")


def _read_json(path, what):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        p = Path(path)
        shown = p.relative_to(ROOT).as_posix() if ROOT in p.parents else p.name
        raise ToolError(f"{what} not found ({shown}); it has not been generated yet")
    except (OSError, ValueError) as exc:
        raise ToolError(f"{what} unreadable ({type(exc).__name__})")


def _age_s(iso):
    try:
        ts = datetime.fromisoformat(str(iso))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return int(time.time() - ts.timestamp())
    except (TypeError, ValueError):
        return None


def tool_factory_products(args):
    _no_args("factory_products", args)
    reg = _read_json(PRODUCT_REGISTRY, "product registry")
    products = reg.get("products") or []
    states = {}
    for p in products:
        states[p.get("primary_state")] = states.get(p.get("primary_state"), 0) + 1
    drift = reg.get("drift") or {}
    return {"status": "OK", "generated_at": reg.get("generated_at"), "age_seconds": _age_s(reg.get("generated_at")),
            "products": len(products), "states": states,
            "sales_total": sum(int(p.get("sales_count") or 0) for p in products),
            "drift_counts": {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in drift.items()},
            "note": "FIRST_SALE_VERIFIED needs a real sale; sales_total comes from the Gumroad listing data in the registry"}


def tool_distribution_status(args):
    _no_args("distribution_status", args)
    d = _read_json(DIST_DASHBOARD, "distribution dashboard")
    op, com = d.get("operational") or {}, d.get("commercial") or {}
    platforms = {k: {f: v.get(f) for f in ("name", "state", "publish_mode", "why")} for k, v in (op.get("platforms") or {}).items()}
    return {"status": "OK", "generated_at": d.get("generated_at"), "age_seconds": _age_s(d.get("generated_at")),
            "platforms": platforms, "offers": op.get("offers"), "jobs_by_state": op.get("jobs_by_state"),
            "jobs_by_platform": op.get("jobs_by_platform"), "awaiting_approval": len(op.get("awaiting_approval") or []),
            "stuck_or_retrying": len(op.get("stuck_or_retrying") or []),
            "published_verified": len(op.get("published_verified") or []),
            "manual_posts_unverified": len(op.get("manual_posts_unverified") or []),
            "commercial": {"metrics": com.get("metrics"), "verified_revenue_cents": com.get("verified_revenue_cents")},
            "next_actions": (d.get("next_actions") or [])[:8]}


def tool_pinterest_queue_status(args):
    _no_args("pinterest_queue_status", args)
    q = _read_json(PINTEREST_QUEUE, "Pinterest queue")
    brand = _read_json(METRICOOL_BRAND, "Metricool brand record")
    attempts = []
    try:
        for line in METRICOOL_ATTEMPTS.read_text(encoding="utf-8").splitlines():
            try:
                attempts.append(json.loads(line))
            except ValueError:
                continue
    except FileNotFoundError:
        pass
    items = q.get("items") or []
    nxt = next((i for i in items if i.get("status") == "READY"), None)
    return {"status": "OK", "generated_at": q.get("generated_at"), "age_seconds": _age_s(q.get("generated_at")),
            "board_found": bool(q.get("board")), "board_name": (q.get("board") or {}).get("name"),
            "board_lookup": q.get("board_lookup"), "summary": q.get("summary"),
            "items": [{k: i.get(k) for k in ("offer_id", "status", "when_local")} for i in items],
            "next_ready": {k: nxt.get(k) for k in ("offer_id", "title", "when_local", "image")} if nxt else None,
            "metricool": {"brand_label": brand.get("label"), "connected_networks": sorted(brand.get("connected_networks") or {}),
                          "post_creation": brand.get("post_creation")},
            "submissions": {"attempts": len(attempts), "created": sum(1 for a in attempts if a.get("created") is True)},
            "note": "a post counts as created only after a getScheduledPosts read-back; this tool never calls Metricool"}


def tool_video_studio_status(args):
    _no_args("video_studio_status", args)
    videos = []
    for m in sorted(VIDEO_PROJECTS.glob("*.json")):
        if m.name.endswith(".rights.json"):
            continue
        man = _read_json(m, f"video project {m.name}")
        vid = man.get("id") or m.stem
        rights = {}
        rp = m.with_name(m.stem + ".rights.json")
        if rp.is_file():
            rights = _read_json(rp, f"rights manifest {rp.name}")
        build = VIDEO_OUTPUT / vid / f"{vid}.build.json"
        rec = _read_json(build, f"build record {vid}") if build.is_file() else None
        videos.append({"id": vid, "title": man.get("title"), "format": man.get("format"),
                       "rendered": bool(rec and (VIDEO_OUTPUT / vid / f"{vid}.mp4").is_file()),
                       "duration_s": rec.get("duration_s") if rec else None,
                       "sentences": rec.get("sentences") if rec else None,
                       "rights_status": rights.get("status", "UNKNOWN")})
    return {"status": "OK", "videos": videos,
            "publishable": [v["id"] for v in videos if v["rendered"] and v["rights_status"] == "CLEARED"],
            "note": "renders are local only; nothing is uploaded; publication also needs rights CLEARED and a founder approval"}


def _schema(props, required=()):
    return {"type": "object", "properties": props, "required": list(required), "additionalProperties": False}


TOOLS = {
    "ci_status": {
        "fn": tool_ci_status,
        "description": ("Read-only. GitHub Actions verdict (PASS/HOLD/BLOCKED/UNKNOWN) for one commit on "
                        "main of the public repo, via anonymous GETs. Never writes a ledger. "
                        "status=BLOCKED with a reason when GitHub cannot be read."),
        "inputSchema": _schema({
            "commit_sha": {"type": "string", "pattern": "^[0-9a-f]{7,40}$",
                           "description": "Commit to check. Overrides ref."},
            "ref": {"type": "string", "enum": ["origin/main", "HEAD"], "default": "origin/main",
                    "description": "Local git ref to resolve when commit_sha is not given."},
        }),
    },
    "write_gate_status": {
        "fn": tool_write_gate_status,
        "description": ("Read-only. Observable state of the Gumroad write gate: live-publish flag in this "
                        "process, auth-state status and age. Never reads .env or a credential, never returns "
                        "a fingerprint, never mints a scope, never writes."),
        "inputSchema": _schema({}),
    },
    "verify_render": {
        "fn": tool_verify_render,
        "description": ("Read-only. Decode and check one .mp4 under kids_studio/renders (frames, audio, sync, "
                        "Arabic subtitle track). Writes no report file; uploads nothing."),
        "inputSchema": _schema({
            "path": {"type": "string", "maxLength": 260,
                     "description": "Path relative to the project root, e.g. kids_studio/renders/ep01_animatic.mp4"},
        }, required=("path",)),
    },
    "factory_products": {
        "fn": tool_factory_products,
        "description": ("Read-only. Product registry summary: products, listing states, recorded sales, drift "
                        "counts and the registry's age. Reads data/product_registry.json only."),
        "inputSchema": _schema({}),
    },
    "distribution_status": {
        "fn": tool_distribution_status,
        "description": ("Read-only. Distribution engine dashboard: platform states, offer eligibility, campaign "
                        "jobs by state, drafts awaiting approval, commercial evidence. Reads "
                        "data/distribution_dashboard.json only; never approves or posts."),
        "inputSchema": _schema({}),
    },
    "pinterest_queue_status": {
        "fn": tool_pinterest_queue_status,
        "description": ("Read-only. Pinterest/Metricool queue: board found or not, items by status, the next READY "
                        "post, recorded submission attempts. Reads data/ files only; never calls Metricool."),
        "inputSchema": _schema({}),
    },
    "video_studio_status": {
        "fn": tool_video_studio_status,
        "description": ("Read-only. Video studio projects: rendered or not, duration, rights status, and which "
                        "could be published. Reads video_studio/projects and build records only; uploads nothing."),
        "inputSchema": _schema({}),
    },
}


def call_tool(name, args):
    started = time.monotonic()
    if name not in TOOLS:
        _log(name, args, "REFUSED", started, "unknown tool")
        return {"content": [{"type": "text", "text": f"unknown tool: {sanitize_text(str(name))[:80]}"}], "isError": True}
    if not isinstance(args, dict):
        _log(name, {}, "REFUSED", started, "arguments not an object")
        return {"content": [{"type": "text", "text": "arguments must be an object"}], "isError": True}
    try:
        result = sanitize(TOOLS[name]["fn"](args))
        text = json.dumps(result, ensure_ascii=False, indent=1)
        if len(text) > MAX_RESULT_CHARS:
            text = text[:MAX_RESULT_CHARS] + "\n...[truncated]"
        _log(name, args, str(result.get("status", "OK")), started)
        return {"content": [{"type": "text", "text": text}], "isError": False}
    except ToolError as exc:
        _log(name, args, "REFUSED", started, exc)
        return {"content": [{"type": "text", "text": sanitize_text(str(exc))}], "isError": True}
    except Exception as exc:                  # noqa: BLE001 -- report, never crash the server
        _log(name, args, "ERROR", started, f"{type(exc).__name__}: {exc}")
        return {"content": [{"type": "text", "text": f"internal error: {type(exc).__name__}"}], "isError": True}


# --------------------------------------------------------------------------
# JSON-RPC over stdio
# --------------------------------------------------------------------------

def handle(msg):
    """Return a response dict, or None for notifications."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return {"jsonrpc": "2.0", "id": msg.get("id") if isinstance(msg, dict) else None,
                "error": {"code": -32600, "message": "invalid request"}}
    method, mid, params = msg["method"], msg.get("id"), msg.get("params") or {}
    if "id" not in msg:
        return None                           # notification (e.g. notifications/initialized)
    if method == "initialize":
        asked = params.get("protocolVersion")
        version = asked if asked in SUPPORTED_PROTOCOLS else SUPPORTED_PROTOCOLS[0]
        result = {"protocolVersion": version, "capabilities": {"tools": {"listChanged": False}},
                  "serverInfo": SERVER_INFO,
                  "instructions": f"{len(TOOLS)} read-only tools. Nothing here can write, publish or send."}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "description": t["description"], "inputSchema": t["inputSchema"],
                             "annotations": {"readOnlyHint": True, "destructiveHint": False,
                                             "openWorldHint": n == "ci_status"}}
                            for n, t in TOOLS.items()]}
    elif method == "tools/call":
        result = call_tool(params.get("name"), params.get("arguments") or {})
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"[:120]}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _send(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()


def serve():
    for raw in sys.stdin.buffer:              # bytes: immune to the console code page
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            _send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        if isinstance(msg, list):
            _send({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "batches not supported"}})
            continue
        resp = handle(msg)
        if resp is not None:
            _send(resp)


if __name__ == "__main__":
    _drop_unsafe_sys_path()
    serve()
