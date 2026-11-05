#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily autonomy watch for factory_loop.js (2026-11-05).

Once per UTC day: run the read-only stage check (scripts/autonomy_selfcheck.collect), append one line to
data/autonomy_status_history.jsonl, restate data/autonomy_status.json, and compare with the previous day.
A stage that was OK and no longer is (a regression) raises an alert through gf_ops.alerts: Telegram when the
chat id is configured, otherwise the local fallback ledger data/ops_alerts_fallback.jsonl, so nothing is lost.
A stage that is simply still BLOCKED/WAITING is not re-alerted; it is listed in the status file.

The purpose is fewer human check-ups: the founder (or the agent) reads one file or gets one alert only when
something that worked stops working. Nothing is written to any platform.

    python scripts/autonomy_daily.py --once
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

STATE = ROOT / "data" / "autonomy_daily_state.json"
HISTORY = ROOT / "data" / "autonomy_status_history.jsonl"
LATEST = ROOT / "data" / "autonomy_status.json"


_TOOL_STATUS = {"VERIFIED": "OK", "VERIFIED_CONNECTED": "OK", "DEGRADED": "DEGRADED", "FAILED": "FAILED", "UNKNOWN": "UNKNOWN"}
_SKIP_TOOLS = {"loop:low_disk_mode"}  # conditional by design, not a failure signal


def tool_rows(verify=None):
    """Connection-verifier rows (probes and runtime records of every tool) as stage rows keyed 'T:<name>'."""
    if verify is None:
        import connection_verifier
        verify = lambda: connection_verifier.verify(live=True)  # noqa: E731
    out = []
    for r in verify().get("rows", []):
        if r["name"] in _SKIP_TOOLS:
            continue
        out.append({"stage": "T:" + r["name"], "name": r["name"], "status": _TOOL_STATUS.get(r["status"], "UNKNOWN"),
                    "detail": str(r.get("evidence", ""))[:160], "owner": "tool"})
    return out


def regressions(prev_rows, rows):
    """Stages that were OK in the previous snapshot and are not OK now."""
    before = {r["stage"]: r for r in (prev_rows or [])}
    out = []
    for r in rows:
        p = before.get(r["stage"])
        if p and p.get("status") == "OK" and r.get("status") != "OK":
            out.append({"stage": r["stage"], "name": r["name"], "was": "OK", "now": r["status"], "detail": r["detail"]})
    return out


def _last_snapshot(history_path):
    try:
        lines = Path(history_path).read_text(encoding="utf-8").strip().splitlines()
        return json.loads(lines[-1]).get("rows") if lines else None
    except (OSError, ValueError, IndexError):
        return None


def run_once(today=None, state_path=STATE, history_path=HISTORY, latest_path=LATEST, collector=None, alerter=None, tools=None):
    today = today or datetime.now(timezone.utc).date().isoformat()
    try:
        last = json.loads(Path(state_path).read_text(encoding="utf-8")).get("last_day")
    except (OSError, ValueError):
        last = None
    if last == today:
        return {"action": "none", "detail": f"autonomy already checked for {today}"}
    if collector is None:
        import autonomy_selfcheck
        collector = autonomy_selfcheck.collect
        if tools is None:
            tools = tool_rows
    rows = collector()
    if tools is not None:
        try:
            rows = rows + tools()
        except Exception as e:  # the stage check must still be recorded
            rows = rows + [{"stage": "T:verifier", "name": "connection verifier", "status": "UNKNOWN",
                            "detail": f"{type(e).__name__}", "owner": "tool"}]
    prev = _last_snapshot(history_path)
    regs = regressions(prev, rows)
    counts = {}
    for r in rows:
        k = ("tools " if str(r["stage"]).startswith("T:") else "") + r["status"]
        counts[k] = counts.get(k, 0) + 1
    snap = {"day": today, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "counts": counts, "rows": rows,
            "regressions": regs}
    Path(history_path).parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(snap, ensure_ascii=False) + "\n")
    tmp = Path(str(latest_path) + ".tmp")
    tmp.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, latest_path)
    alerted = None
    if regs:
        if alerter is None:
            from gf_ops import alerts
            alerter = alerts.send_alert
        body = "\n".join(f"- stage {g['stage']} {g['name']}: OK -> {g['now']} ({g['detail']})" for g in regs)
        alerted = alerter(subject=f"{len(regs)} automatic stage(s) or tool(s) stopped working", body=body, category="OPS",
                          evidence="data/autonomy_status.json", retry_status="the next daily check re-reads every stage",
                          next_step="python scripts/autonomy_selfcheck.py", window_hours=20)
    tmp = Path(str(state_path) + ".tmp")
    tmp.write_text(json.dumps({"last_day": today}), encoding="utf-8")
    os.replace(tmp, state_path)
    detail = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
    if regs:
        detail += "; REGRESSED: " + ", ".join(g["name"] for g in regs)
    return {"action": "regressed" if regs else "ok", "detail": detail}


def main():
    try:
        r = run_once()
    except Exception as e:  # reported to the loop, never thrown
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
