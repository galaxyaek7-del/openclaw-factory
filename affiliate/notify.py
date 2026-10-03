#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — affiliate material-event notifier (decide-only side).

`--check` compares live material state vs data/affiliate_notify_state.json
and prints {"notifications":[...]}. Sending is the tick caller's job
(factory_loop.js via lib/telegram_direct). Only material events, deduped:
new QUALIFIED program, link health change, first verified REAL commission,
program discontinuation. Internal test clicks never notify.
"""
import json
import sys
from pathlib import Path
from . import daily_health as dh
from . import performance as perf

FACTORY_DIR = Path(__file__).resolve().parent.parent
STATE = FACTORY_DIR / "data" / "affiliate_notify_state.json"


def _load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"seen_qualified": [], "link_status": {}, "commissions_seen": 0,
            "seen_discontinued": []}


def _save_state(state):
    tmp = STATE.parent / f"{STATE.name}.tmp"
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE)


def check():
    health = dh.daily_health(probe=False)
    programs = perf.classify_all()["programs"]
    state = _load_state()
    notes = []
    qualified_now = sorted(p["opportunity_id"] for p in programs
                           if p["status"] == "QUALIFIED")
    for oid in qualified_now:
        if oid not in state["seen_qualified"]:
            notes.append({"kind": "NEW_QUALIFIED_PROGRAM",
                          "text": f"Affiliate: newly qualified program {oid} — needs founder application + link."})
    state["seen_qualified"] = qualified_now
    for row in health["link_health"]:
        key = str(row.get("domain"))
        cur = str(row.get("http_status"))
        if state["link_status"].get(key) not in (None, cur) and cur not in ("None", "null"):
            notes.append({"kind": "LINK_STATUS_CHANGE",
                          "text": f"Affiliate link health changed for {key}: {cur}."})
        state["link_status"][key] = cur
    total_comms = health["performance_totals"]["verified_commissions"]
    if total_comms > state.get("commissions_seen", 0):
        notes.append({"kind": "FIRST_VERIFIED_COMMISSION",
                      "text": "Affiliate: first verified REAL commission recorded. See commission ledger."})
    state["commissions_seen"] = total_comms
    disc_now = sorted(p["opportunity_id"] for p in programs
                      if p["status"] == "DISCONTINUED")
    for oid in disc_now:
        if oid not in state.get("seen_discontinued", []):
            notes.append({"kind": "PROGRAM_DISCONTINUED",
                          "text": f"Affiliate program discontinued: {oid}."})
    state["seen_discontinued"] = disc_now
    _save_state(state)
    return {"notifications": notes}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if "--check" in sys.argv:
        print(json.dumps(check(), ensure_ascii=False))
    else:
        print(json.dumps({"hint": "run with --check"}, ensure_ascii=False))
