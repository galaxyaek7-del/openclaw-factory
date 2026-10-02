"""Arm Rotation Engine (multi-arm company mode). Pure logic + JSON state.

7 arms, each with: signal (NONE/LOW/HIGH), blocked (bool mynd/or reason),
last_run. rotate() picks next arm: priority boost on HIGH signal, else
round-robin skipping blocked, fairness via least-recently-run.
NEXT_ARM is never NONE unless security stop (caller decides that).
"""
import datetime
import json
import os

ARMS = ["AI_SERVICES", "MICRO_B2B", "RESEARCH", "AI_OPS", "AFFILIATE",
        "DIGITAL_PRODUCTS", "DATA_DOCS"]
STATE_PATH = "data/arm_rotation.json"


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def load():
    try:
        st = json.load(open(STATE_PATH, encoding="utf-8"))
        for a in ARMS:
            st.setdefault(a, {"signal": "NONE", "blocked": False,
                              "last_run": None, "runs": 0})
        return st
    except (OSError, ValueError):
        return {a: {"signal": "NONE", "blocked": False, "last_run": None,
                    "runs": 0} for a in ARMS}


def save(st):
    json.dump(st, open(STATE_PATH, "w", encoding="utf-8"), indent=1)


def set_signal(arm, signal, blocked=False):
    st = load()
    st[arm]["signal"] = signal
    st[arm]["blocked"] = blocked
    save(st)


def rotate():
    """Returns (current_arm, reason). Priority: HIGH signal first, else
    least-recently-run unblocked arm (fairness)."""
    st = load()
    live = [a for a in ARMS if not st[a]["blocked"]]
    if not live:
        return None, "all blocked (security/environment stop only)"
    for a in live:
        if st[a]["signal"] == "HIGH":
            st[a]["runs"] += 1
            st[a]["last_run"] = _now()
            save(st)
            return a, "priority-boost on HIGH signal"
    nxt = min(live, key=lambda a: (st[a]["last_run"] or "", st[a]["runs"]))
    st[nxt]["runs"] += 1
    st[nxt]["last_run"] = _now()
    save(st)
    return nxt, "fairness rotation"


def heartbeat_patch():
    st = load()
    return {"company_mode": "ACTIVE_ROTATION",
            "arms": {a: {"signal": v["signal"], "blocked": v["blocked"],
                         "runs": v["runs"]} for a, v in st.items()}}
