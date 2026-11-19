"""Galaxy Forge read-only MCP pilot server (2026-10-15).

A Model Context Protocol server over STDIO: newline-delimited JSON-RPC 2.0
on stdin/stdout, as the MCP stdio transport specifies. It opens no network
listener. Approved as "Option B" in reports/MCP_FEASIBILITY_AUDIT_2026-10-15.md.

It exposes twelve READ-ONLY tools, each a thin wrapper over code or files that
already exist and are already tested:

  ci_status               ci_health_detector.detect()   (anonymous GitHub GETs)
  write_gate_status       data/gumroad_auth_state.json  (status + age only)
  verify_render           kids_studio/tools/verify_video.analyze()
  factory_products        data/product_registry.json                 (2026-10-24)
  distribution_status     data/distribution_dashboard.json           (2026-10-24)
  pinterest_queue_status  data/pinterest_queue.json + Metricool records (2026-10-24)
  video_studio_status     video_studio/projects + build records      (2026-10-24)
  factory_status          supervisor.log + data/factory_state.json + /health  (2026-11-18)
  tasks_status            TASKS.md + WORKLOG.md                      (2026-11-18)
  test_status             data/regression_status.json, read not run  (2026-11-18)
  revenue_evidence        data/verified_transactions.jsonl + registry (2026-11-18)
  recent_logs             tail of a whitelisted log, secrets redacted (2026-11-18)
The 2026-10-24 and 2026-11-18 tools read fixed files only: no arguments that
name a path, no caller-supplied file.

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


# --- agent-facing state readers (2026-11-18) --------------------------------
# Founder mission: expose factory state to agents, read-only. Same discipline as
# the 2026-10-24 readers: fixed files, no caller path, no writes, no .env.
# Every path is a module global so a test can point it at a temp file.

SUPERVISOR_LOG = ROOT / "supervisor.log"
FACTORY_STATE = ROOT / "data" / "factory_state.json"
TASKS_MD = ROOT / "TASKS.md"
WORKLOG_MD = ROOT / "WORKLOG.md"
REGRESSION_STATUS = ROOT / "data" / "regression_status.json"
VERIFIED_TX = ROOT / "data" / "verified_transactions.jsonl"
FINANCE_JSON = ROOT / "finance_data.json"
HEALTH_URL = os.environ.get("GF_MCP_HEALTH_URL", "http://127.0.0.1:3000/health")
HEALTH_TIMEOUT_S = 2.0
LOG_SOURCES = {
    "factory_loop": ROOT / "factory_loop.log",
    "supervisor": ROOT / "supervisor.log",
    "server_crashes": ROOT / "server_crashes.log",
    "server_errors": ROOT / "errors.log",
}
LOG_TAIL_BYTES = 256 * 1024
REGISTRY_STALE_S = 36 * 3600   # a recorded test result older than this is STALE, not PASS

_ENV_ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?[A-Z][A-Z0-9_]{1,60}\s*=")


def _age_or_none(iso):
    return _age_s(iso)


def _read_tail(path, max_bytes=LOG_TAIL_BYTES):
    """Last max_bytes of a file, decoded, as a list of complete lines.

    A partial first line (the window cut it) is dropped, never reported as a
    real log line.
    """
    p = Path(path)
    with p.open("rb") as fh:
        fh.seek(0, 2)
        size = fh.tell()
        start = max(0, size - max_bytes)
        fh.seek(start)
        raw = fh.read()
    text = raw.decode("utf-8", "replace")
    if start > 0:
        nl = text.find("\n")
        text = text[nl + 1:] if nl != -1 else ""
    return text.splitlines(), size


def _probe_health():
    """Bounded localhost GET. Returns OBSERVED status or an explicit absence.

    Uses http.client against the parsed host/port with a 2 s timeout: no
    arbitrary URL is ever fetched and no redirect is followed.
    """
    if os.environ.get("GF_MCP_PROBE_HEALTH", "1").strip() == "0":
        return {"state": "NOT_MEASURED", "why": "health probe disabled for this process"}
    try:
        import http.client
        from urllib.parse import urlsplit

        u = urlsplit(HEALTH_URL)
        if u.hostname not in ("127.0.0.1", "localhost", "::1"):
            return {"state": "NOT_MEASURED", "why": "health URL is not loopback"}
        conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=HEALTH_TIMEOUT_S)
        try:
            conn.request("GET", u.path or "/", headers={"Accept": "application/json"})
            resp = conn.getresponse()
            body = json.loads(resp.read(256 * 1024).decode("utf-8", "replace"))
        finally:
            conn.close()
        return {"state": "OBSERVED", "http": resp.status,
                "status": body.get("status"), "status_source": body.get("status_source"),
                "timestamp": body.get("timestamp"),
                "reality": body.get("reality"), "publish_gate": body.get("publish_gate")}
    except Exception as exc:  # noqa: BLE001 -- absence must be reported, never guessed
        if isinstance(exc, TimeoutError) or "timed out" in str(exc).lower():
            return {"state": "UNREACHABLE", "why": "health endpoint did not answer within 2s"}
        return {"state": "UNREACHABLE", "why": f"{type(exc).__name__}"}


def tool_factory_status(args):
    _no_args("factory_status", args)
    state = _read_json(FACTORY_STATE, "factory state")
    try:
        lines, log_bytes = _read_tail(SUPERVISOR_LOG)
    except FileNotFoundError:
        lines, log_bytes = [], 0
    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    by_target = {}
    crashes_24h = 0
    cutoff = time.time() - 24 * 3600
    for ev in events:
        try:
            ts = datetime.fromisoformat(str(ev.get("at")).replace("Z", "+00:00")).timestamp()
        except (TypeError, ValueError):
            ts = None
        if ev.get("event") == "crash" and ts and ts >= cutoff:
            crashes_24h += 1
        target = Path(str(ev.get("target") or "")).name
        if not target:
            continue
        if target not in by_target or (ts and ts >= by_target[target].get("_ts", 0)):
            by_target[target] = {k: ev.get(k) for k in ("at", "event")}
            by_target[target]["_ts"] = ts or 0
    for rec in by_target.values():
        rec.pop("_ts", None)
    updated = state.get("updated_at")
    age = _age_or_none(updated)
    task = state.get("current_task") or {}
    checkpoint = state.get("last_successful_checkpoint") or {}
    healthy = (age is not None and age < 1200) and not state.get("recovery_info", {}).get("interrupted")
    return {
        "status": "OK" if healthy else "DEGRADED",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "loop": {
            "state_age_seconds": age,
            "updated_at": updated,
            "current_task": task.get("name") or None,
            "current_step": task.get("step") or None,
            "task_started_at": task.get("started_at"),
            "last_checkpoint": {"stage": checkpoint.get("stage"), "at": checkpoint.get("at")},
            "interrupted": bool((state.get("recovery_info") or {}).get("interrupted")),
            "pending_retries": len(state.get("pending_retries") or []),
        },
        "supervisor": {"log_bytes": log_bytes, "last_event_by_target": by_target,
                       "crashes_24h": crashes_24h},
        "server_health": _probe_health(),
        "note": ("state is OBSERVED from files on disk; loop freshness uses a 20-minute "
                 "threshold for a ~10-minute tick"),
    }


def _md_rows(text, prefix):
    rows = []
    current = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            current = line[3:].strip()
        stripped = line.lstrip()
        if stripped.startswith("[x] ") or stripped.startswith("[ ] "):
            rows.append({"section": current, "done": stripped[1].lower() == "x",
                         "text": stripped[4:].strip()[:300]})
    return rows


def tool_tasks_status(args):
    _no_args("tasks_status", args)
    try:
        tasks_text = Path(TASKS_MD).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        tasks_text = ""
    try:
        worklog_text = Path(WORKLOG_MD).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        worklog_text = ""
    rows = _md_rows(tasks_text, "[")
    blocked = [r["text"] for r in rows if "BLOCKED" in r["text"].upper()]
    done = sum(1 for r in rows if r["done"])
    sections = []
    for r in rows:
        if r["section"] and r["section"] not in sections:
            sections.append(r["section"])
    entries = []
    for block in worklog_text.split("\n### ")[1:]:
        head = block.splitlines()[0].strip()
        first_bullet = next((ln.strip("- ").strip() for ln in block.splitlines()[1:]
                             if ln.strip().startswith("-")), None)
        entries.append({"heading": head[:180], "first_item": (first_bullet or "")[:240]})
    return {
        "status": "OK" if rows else "UNKNOWN",
        "source": "TASKS.md + WORKLOG.md (parsed, nothing executed)",
        "tasks": {"total": len(rows), "done": done, "pending": len(rows) - done},
        "sections": sections,
        "blocked_items": blocked,
        "items": [{"done": r["done"], "text": r["text"]} for r in rows],
        "worklog_recent": entries[-5:][::-1],
        "note": ("a [ ] row is pending; BLOCKED text marks a row that needs a founder "
                 "decision or an external credential"),
    }


def tool_test_status(args):
    _no_args("test_status", args)
    doc = _read_json(REGRESSION_STATUS, "recorded regression result")
    age = _age_or_none(doc.get("at"))
    failed = int(doc.get("failed") or 0)
    if age is None:
        verdict = "UNKNOWN"
    elif failed:
        verdict = "FAILED"
    elif age > REGISTRY_STALE_S:
        verdict = "STALE"
    else:
        verdict = "PASS"
    return {
        "status": verdict,
        "recorded_at": doc.get("at"),
        "age_seconds": age,
        "stale_after_seconds": REGISTRY_STALE_S,
        "python": doc.get("python"),
        "node": doc.get("node"),
        "failed": failed,
        "failures": (doc.get("failures") or [])[:20],
        "skipped_missing": (doc.get("skipped_missing") or [])[:20],
        "source": "data/regression_status.json — RECORDED by scripts/factory_regression.py; this tool never runs a test",
    }


def _verified_rows():
    rows = []
    try:
        text = Path(VERIFIED_TX).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None, 0
    bad = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if row.get("simulation") is True or row.get("test") is True:
            continue                    # simulated/test money is never revenue
        rows.append(row)
    return rows, bad


def tool_revenue_evidence(args):
    _no_args("revenue_evidence", args)
    rows, bad_lines = _verified_rows()
    registry = _read_json(PRODUCT_REGISTRY, "product registry")
    products = registry.get("products") or []
    units = sum(int(p.get("sales_count") or 0) for p in products)
    cents = sum(int(p.get("sales_usd_cents") or 0) for p in products)
    try:
        finance = json.loads(Path(FINANCE_JSON).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        finance = None
    if rows is None:
        evidence = {"state": "NO_VERIFIED_TRANSACTION_RECORD",
                    "source": "data/verified_transactions.jsonl is absent",
                    "transactions": [], "verified_revenue_usd": 0}
    else:
        total = sum(int(r.get("amount_cents") or 0) for r in rows)
        evidence = {"state": "VERIFIED_ROWS_PRESENT" if rows else "EMPTY_LEDGER",
                    "source": "data/verified_transactions.jsonl",
                    "transactions": [{"offer_id": r.get("offer_id"), "platform": r.get("platform"),
                                      "amount_cents": r.get("amount_cents"),
                                      "currency": r.get("currency") or "USD",
                                      "at": r.get("at") or r.get("recorded_at")} for r in rows[:20]],
                    "row_count": len(rows),
                    "unparseable_lines": bad_lines,
                    "verified_revenue_usd": round(total / 100.0, 2)}
    return {
        "status": "OK",
        "verified": evidence,
        "registry": {"sales_units": units, "sales_usd": round(cents / 100.0, 2),
                     "generated_at": registry.get("generated_at"),
                     "age_seconds": _age_or_none(registry.get("generated_at"))},
        "finance_file": None if finance is None else {
            "totalSales": finance.get("totalSales"), "lastUpdated": finance.get("lastUpdated")},
        "note": ("only data/verified_transactions.jsonl rows count as verified revenue; "
                 "page views, drafts, clicks and simulated rows never do. 0 with an explicit "
                 "state means no verified transaction exists"),
    }


def _log_source(name):
    if not isinstance(name, str) or name not in LOG_SOURCES:
        raise ToolError(f"source must be one of {sorted(LOG_SOURCES)}")
    return LOG_SOURCES[name]


def tool_recent_logs(args):
    extra = set(args) - {"source", "lines"}
    if extra:
        raise ToolError(f"unexpected argument(s): {sorted(extra)}")
    src = _log_source(args.get("source", "factory_loop"))
    lines_wanted = args.get("lines", 40)
    if not isinstance(lines_wanted, int) or isinstance(lines_wanted, bool) or not 1 <= lines_wanted <= 200:
        raise ToolError("lines must be an integer between 1 and 200")
    try:
        lines, size = _read_tail(src)
    except FileNotFoundError:
        raise ToolError(f"log not found ({Path(src).name}); it may not have been written yet")
    except OSError as exc:
        raise ToolError(f"log unreadable ({type(exc).__name__})")
    out, dropped = [], 0
    for line in lines[-lines_wanted:]:
        if _ENV_ASSIGNMENT.match(line):
            dropped += 1                  # an env-style assignment never leaves the server
            continue
        out.append(sanitize_text(line[:500]))
    return {"status": "OK", "source": Path(src).name, "log_bytes": size,
            "returned_lines": len(out), "dropped_env_style_lines": dropped,
            "lines": out,
            "note": "credential-shaped text is redacted; env-style assignments are dropped, not shown"}


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
    "factory_status": {
        "fn": tool_factory_status,
        "description": ("Read-only. Factory runtime: supervisor last event per target and crashes in 24 h, loop "
                        "state age, current task/step, last checkpoint, and a bounded 2 s GET to the local "
                        "/health endpoint. Starts no cycle and writes nothing."),
        "inputSchema": _schema({}),
    },
    "tasks_status": {
        "fn": tool_tasks_status,
        "description": ("Read-only. Parses TASKS.md checkboxes (done/pending, BLOCKED rows) and the last five "
                        "WORKLOG.md entries. Executes nothing."),
        "inputSchema": _schema({}),
    },
    "test_status": {
        "fn": tool_test_status,
        "description": ("Read-only. Last RECORDED regression result from data/regression_status.json with age "
                        "and a PASS/FAILED/STALE/UNKNOWN verdict. Never runs a test."),
        "inputSchema": _schema({}),
    },
    "revenue_evidence": {
        "fn": tool_revenue_evidence,
        "description": ("Read-only. Verified revenue only: rows from data/verified_transactions.jsonl (test and "
                        "simulation rows excluded), plus registry and finance totals. Returns 0 with an explicit "
                        "state when no verified transaction exists; invents nothing."),
        "inputSchema": _schema({}),
    },
    "recent_logs": {
        "fn": tool_recent_logs,
        "description": ("Read-only. Tail of one whitelisted log (factory_loop, supervisor, server_crashes, "
                        "server_errors). Credential-shaped text is redacted and env-style assignments are "
                        "dropped. No caller-supplied path."),
        "inputSchema": _schema({
            "source": {"type": "string", "enum": sorted(LOG_SOURCES), "default": "factory_loop"},
            "lines": {"type": "integer", "minimum": 1, "maximum": 200, "default": 40},
        }),
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
