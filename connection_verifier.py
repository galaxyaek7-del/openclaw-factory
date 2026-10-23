#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge -- connection verifier: "connected" only with evidence (2026-10-22).

WHY THIS EXISTS
---------------
integration_registry.py decides `configured` from environment-variable
presence alone ("never a live test connection call", by design). That is
the wrong question for "is this part of the factory working": Telegram is
`configured: True` while no message can be delivered (no chat id), and n8n
is `configured: True` while its workflows failed for 12 days.

This module answers it with evidence of one of two kinds, recorded per check:
  probe          a read-only call made now (no writes, no spend)
  runtime_record a real execution record with its timestamp and age

Status vocabulary: VERIFIED, DEGRADED, FAILED, UNKNOWN. Nothing is VERIFIED
from configuration. Secrets are never printed or stored.

    python connection_verifier.py            # prints a table, writes data/connection_status.json
    python connection_verifier.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STATUS_PATH = ROOT / "data" / "connection_status.json"
LOOP_LOG = ROOT / "factory_loop.log"
AI_COST_LOG = ROOT / "data" / "ai_cost_log.jsonl"
VERIFIED, DEGRADED, FAILED, UNKNOWN = "VERIFIED", "DEGRADED", "FAILED", "UNKNOWN"


def _now():
    return datetime.now(timezone.utc)


def _row(name, kind, status, evidence, method, **extra):
    return {"name": name, "kind": kind, "status": status, "evidence": evidence, "method": method, **extra}


def _age_hours(ts, now):
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (now - t).total_seconds() / 3600


# ---- runtime records ----------------------------------------------------------

def _tail_lines(path, max_bytes=8_000_000):
    p = Path(path)
    if not p.exists():
        return []
    size = p.stat().st_size
    with open(p, "rb") as f:
        f.seek(max(0, size - max_bytes))
        data = f.read().decode("utf-8", "replace")
    lines = data.splitlines()
    # Only a read that started mid-file can begin with a partial line.
    return lines[1:] if size > max_bytes else lines


def loop_steps(now, window_hours=24, log_path=LOOP_LOG):
    """Per factory_loop step, from the real tick log: runs, failures and last
    action in the window. A step is VERIFIED when it ran and its last run did
    not fail, DEGRADED when some runs failed, FAILED when every run failed."""
    runs = defaultdict(Counter)
    last = {}
    last_tick = None
    cutoff = now - timedelta(hours=window_hours)
    for line in _tail_lines(log_path):
        m = re.match(r'\{"timestamp":"([^"]+)"', line)
        if not m:
            continue
        ts = datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
        if ts < cutoff:
            continue
        last_tick = m.group(1)
        for step, action in re.findall(r'"step":"([a-z0-9_]+)","action":"([a-z_]+)"', line):
            runs[step][action] += 1
            last[step] = (action, m.group(1))
    rows = []
    for step, c in sorted(runs.items()):
        total, failed = sum(c.values()), c.get("failed", 0)
        status = FAILED if failed == total else DEGRADED if failed else VERIFIED
        if last[step][0] == "failed" and status == VERIFIED:
            status = DEGRADED
        note = ""
        # Some steps (e.g. diagnose) are logged only when they fail. If the loop
        # kept ticking for 30+ min after the step's last failure, it recovered.
        if status == FAILED and last_tick and last[step][1] < last_tick:
            gap = (_age_hours(last[step][1], now) or 0) - (_age_hours(last_tick, now) or 0)
            if gap >= 0.5:
                status, note = DEGRADED, f"; no failure logged in the {gap:.1f} h since (ticks continued)"
        rows.append(_row(f"loop:{step}", "factory_loop_step", status,
                         f"{total} runs in {window_hours} h, {failed} failed; last={last[step][0]} at {last[step][1]}"
                         + note, "runtime_record", runs=total, failed=failed))
    age = _age_hours(last_tick, now) if last_tick else None
    head = _row("factory_loop", "scheduler",
                VERIFIED if age is not None and age < 0.5 else FAILED if age is not None else UNKNOWN,
                f"last tick {last_tick} ({age:.2f} h ago)" if age is not None else "no tick in the window",
                "runtime_record")
    return [head] + rows


def ai_provider(now, log_path=AI_COST_LOG, max_age_hours=48):
    lines = _tail_lines(log_path, 400_000)
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        age = _age_hours(e.get("timestamp"), now)
        status = VERIFIED if age is not None and age <= max_age_hours else DEGRADED
        return [_row("ai:groq", "model_provider", status,
                     f"last real call {e.get('timestamp')} model={e.get('model')} latency={e.get('latency_ms')} ms"
                     + (f" ({age:.1f} h ago)" if age is not None else ""), "runtime_record")]
    return [_row("ai:groq", "model_provider", UNKNOWN, "no call recorded", "runtime_record")]


# ---- read-only probes -----------------------------------------------------------

def _get_json(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "GalaxyForge-verifier/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8", "replace") or "{}")


def server(probe=_get_json):
    try:
        code, body = probe("http://127.0.0.1:3000/health")
    except Exception as e:  # noqa: BLE001
        return [_row("server.js", "service", FAILED, f"/health unreachable: {type(e).__name__}", "probe")]
    st = body.get("status")
    bad = sorted(k for k, v in (body.get("checks") or {}).items() if isinstance(v, dict) and v.get("ok") is False)
    status = VERIFIED if st in ("ok", "healthy") else DEGRADED if st else UNKNOWN
    return [_row("server.js", "service", status,
                 f"/health HTTP {code}, status={st}" + (f"; failing checks: {', '.join(bad)}" if bad else ""), "probe")]


def n8n(run=subprocess.run):
    try:
        out = run([sys.executable, str(ROOT / "scripts" / "n8n_workflow_health.py"), "--json"],
                  capture_output=True, text=True, timeout=60, cwd=str(ROOT))
        data = json.loads(out.stdout)
    except Exception as e:  # noqa: BLE001
        return [_row("n8n", "workflow_engine", UNKNOWN, f"health script failed: {type(e).__name__}", "runtime_record")]
    rows = [_row("n8n", "workflow_engine", VERIFIED if data.get("service_up") else FAILED,
                 f"service_up={data.get('service_up')}", "probe")]
    mapping = {"OK": VERIFIED, "FAILING": FAILED, "STALE": DEGRADED}
    for name, w in (data.get("workflows") or {}).items():
        rows.append(_row(f"n8n:{name}", "workflow", mapping.get(w.get("verdict"), UNKNOWN),
                         f"verdict={w.get('verdict')} last={w.get('last_status')}@{w.get('last_started_at')} "
                         f"runs={w.get('runs_total')} errors={w.get('errors_total')}"
                         + (f"; error: {str(w.get('last_error'))[:80]}" if w.get("last_error") else ""), "runtime_record"))
    return rows


def telegram(probe=_get_json):
    from channels.env_config import read_env_value
    token = read_env_value("TELEGRAM_BOT_TOKEN", ROOT / ".env")
    chat = read_env_value("OPENCLAW_TELEGRAM_CHAT_ID", ROOT / ".env") or read_env_value("TELEGRAM_CHAT_ID", ROOT / ".env")
    if not token:
        return [_row("telegram", "notification", FAILED, "no bot token configured", "probe")]
    try:
        _code, body = probe(f"https://api.telegram.org/bot{token}/getMe")
        valid = bool(body.get("ok"))
    except Exception as e:  # noqa: BLE001  (message never includes the token)
        return [_row("telegram", "notification", UNKNOWN, f"getMe failed: {type(e).__name__}", "probe")]
    if not valid:
        return [_row("telegram", "notification", FAILED, "getMe: token rejected", "probe")]
    if not chat:
        return [_row("telegram", "notification", DEGRADED,
                      "bot token valid (getMe ok) but no chat id configured: messages cannot be delivered", "probe")]
    return [_row("telegram", "notification", VERIFIED, "bot token valid and chat id configured (delivery not sent)", "probe")]


def commerce_reads():
    rows = []
    try:
        from channels import gumroad_publisher as g
        n = len(g.list_products(g.load_token()))
        rows.append(_row("gumroad", "commerce_read", VERIFIED, f"read OK: {n} products (writes gated)", "probe"))
    except Exception as e:  # noqa: BLE001
        rows.append(_row("gumroad", "commerce_read", FAILED, f"read failed: {type(e).__name__}", "probe"))
    try:
        from channels import paddle_publisher as p
        p.list_products(p.load_api_key())
        rows.append(_row("paddle", "commerce_read", VERIFIED, "read OK (writes gated)", "probe"))
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        status = FAILED if ("403" in msg or "permitted" in msg.lower()) else UNKNOWN
        rows.append(_row("paddle", "commerce_read", status,
                         "read refused: HTTP 403 (API key lacks permission)" if status == FAILED
                         else f"read failed: {type(e).__name__}", "probe"))
    return rows


AGENT_LOG = ROOT / "data" / "agent_executions.jsonl"
# Sources that mean "a factory component invoked the agent as part of its work".
FACTORY_SOURCES = {"scout_pipeline", "publisher_seo", "loop", "orchestrator", "sensing_trends"}
# Who can call each persona today (static, from the code; 2026-10-23).
AGENT_CALLERS = {
    "scout": "Sensing trend classifier (POST /api/trends, daily n8n run); Scout pipeline (POST /api/scout/run, manual button)",
    "publisher": "Publisher SEO inside runDistributor (POST /api/distribute, gated shut)",
    "builder": "index.html button only", "design": "index.html button only", "qa": "index.html button only",
    "finance": "no caller in the codebase",
}


def ai_agents(now=None, log_path=AGENT_LOG, connected_days=30):
    """The six personas (lib/agent_prompts.js), from data/agent_executions.jsonl.
    VERIFIED_CONNECTED needs an ok run invoked by a factory component within
    `connected_days`; an ok probe or manual API call alone is
    VERIFIED_EXECUTABLE_NOT_CONNECTED; failures only -> FAILED; nothing -> UNKNOWN."""
    now = now or _now()
    names = list(AGENT_CALLERS)
    records = []
    for line in _tail_lines(log_path, 4_000_000):
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    rows = []
    for n in names:
        mine = [r for r in records if r.get("agent") == n]
        ok = [r for r in mine if r.get("outcome") == "ok"]
        factory_ok = [r for r in ok if r.get("source") in FACTORY_SOURCES
                      and (_age_hours(r.get("started_at"), now) or 1e9) <= connected_days * 24]
        if factory_ok:
            status = "VERIFIED_CONNECTED"
        elif ok:
            status = "VERIFIED_EXECUTABLE_NOT_CONNECTED"
        elif mine:
            status = FAILED
        else:
            status = UNKNOWN
        last = mine[-1] if mine else None
        evidence = (f"last {last.get('outcome')} via {last.get('source')} at {last.get('started_at')}; "
                    f"{len(ok)}/{len(mine)} ok" if last else "no execution record") + f"; callers: {AGENT_CALLERS[n]}"
        rows.append(_row(f"agent:{n}", "ai_agent_persona", status, evidence, "runtime_record"))
    return rows


def verify(live=True, now=None):
    now = now or _now()
    rows = loop_steps(now) + ai_provider(now) + ai_agents(now)
    if live:
        rows += server() + n8n() + telegram() + commerce_reads()
    counts = Counter(r["status"] for r in rows)
    return {"checked_at": now.isoformat(), "counts": dict(counts), "rows": rows,
            "rule": "VERIFIED only from a read-only probe or a dated runtime record; never from configuration"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--offline", action="store_true", help="runtime records only, no probes")
    a = ap.parse_args()
    out = verify(live=not a.offline)
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if a.json:
        print(json.dumps(out, ensure_ascii=False))
        return
    print(f"checked_at {out['checked_at']}  {out['counts']}")
    for r in out["rows"]:
        print(f"  {r['status']:9} {r['name']:42} {r['evidence'][:110]}")


if __name__ == "__main__":
    main()
