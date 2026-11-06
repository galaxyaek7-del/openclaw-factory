#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily research-only run of the Scout -> QA chain while new products are frozen (2026-11-06).

The product chain is frozen with the rest of production, so Scout and QA produced no new evidence for days and their
KPIs (data/agent_tasks.jsonl, scripts/agent_kpis.py) could not show whether the v2 Scout prompt keeps working. This runs
the research chain (scripts/run_research_chain.js): today's sensed trends -> brief -> QA review. It never builds or publishes
anything (its last step is a protected stub), costs cents, and runs at most once a day (a failed attempt may be retried
up to 3 times a day, never a success twice). Loop step contract: prints one JSON line {action, detail}.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "research_chain_state.json"
MAX_ATTEMPTS = 3


def decide(state, today):
    """-> 'run' or a reason to skip."""
    if state.get("day") != today:
        return "run"
    if state.get("ok"):
        return "already succeeded today"
    return "run" if state.get("attempts", 0) < MAX_ATTEMPTS else f"{MAX_ATTEMPTS} attempts used today"


def summarize(stdout):
    """Reads the runner's JSON (it prints one pretty JSON document). -> (ok, detail)."""
    try:
        d = json.loads(stdout[stdout.index("{"):])
    except (ValueError, TypeError):
        return False, "runner printed no JSON"
    brief, qa = d.get("brief"), d.get("qa")
    if d.get("status") == "completed" or (brief and qa):
        return True, f"brief '{str((brief or {}).get('title'))[:60]}' ${(brief or {}).get('price')}; QA {(qa or {}).get('verdict')}"
    return bool(d.get("status") in ("stopped", "done")), f"chain {d.get('status')}; trends {d.get('trends_used')}; brief {'yes' if brief else 'none'}; QA {(qa or {}).get('verdict')}"


def run_once(now=None, state_path=STATE, runner=None):
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()
    try:
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    why = decide(state, today)
    if why != "run":
        return {"action": "none", "detail": why}
    if runner is None:
        def runner():
            return subprocess.run(["node", str(ROOT / "scripts" / "run_research_chain.js"), today], cwd=str(ROOT), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=300, env=dict(os.environ, PYTHONIOENCODING="utf-8")).stdout
    try:
        ok, detail = summarize(runner())
    except Exception as e:  # noqa: BLE001 reported to the loop, never thrown
        ok, detail = False, f"{type(e).__name__}"
    attempts = (state.get("attempts", 0) if state.get("day") == today else 0) + 1
    Path(state_path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(state_path) + ".tmp")
    tmp.write_text(json.dumps({"day": today, "ok": ok, "attempts": attempts, "detail": detail}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, state_path)
    return {"action": "ran" if ok else "failed", "detail": detail}


def main():
    sys.stdout.write(json.dumps(run_once(), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
