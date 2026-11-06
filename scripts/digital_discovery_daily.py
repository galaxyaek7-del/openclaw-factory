#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Loop step: run the digital-product discovery at most every 4 hours (2026-11-06). Prints one JSON line {action, detail}.

    python scripts/digital_discovery_daily.py --once

Each run translates up to GF_DISCOVERY_MAX (default 20) NEW real signals into digital-product candidates (see
golden_hunter/digital_discovery.py); about one model call per signal, cents per run. Never builds or publishes anything.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
STATE = ROOT / "data" / "digital_discovery_run.json"
MIN_GAP = timedelta(hours=4)


def due(state, now):
    try:
        last = datetime.fromisoformat(str(state.get("last_run")).replace("Z", "+00:00"))
    except ValueError:
        return True
    return now - last >= MIN_GAP


def run_once(now=None, state_path=STATE, runner=None):
    now = now or datetime.now(timezone.utc)
    try:
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    if not due(state, now):
        return {"action": "none", "detail": f"discovery ran at {state.get('last_run')}; next run 4 h after"}
    if runner is None:
        from golden_hunter import digital_discovery
        runner = digital_discovery.run
    r = runner()
    Path(state_path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(state_path) + ".tmp")
    tmp.write_text(json.dumps({"last_run": now.isoformat(timespec="seconds"), "last_result": r}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, state_path)
    return {"action": "ran" if r.get("processed") or r.get("errors") else "none",
            "detail": f"{r.get('processed', 0)} signals processed: {r.get('proposed', 0)} proposed, {r.get('declined', 0)} declined, "
                      f"{r.get('duplicate', 0)} duplicate of a live product, {r.get('contract_failed', 0)} malformed, {r.get('errors', 0)} errors; "
                      f"{r.get('signals_waiting', 0)} signals waiting, {r.get('candidates_total', 0)} candidates stored"}


def main():
    try:
        r = run_once()
    except Exception as e:  # noqa: BLE001
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:160]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
