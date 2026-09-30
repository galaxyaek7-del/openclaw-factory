#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ops snapshot (GF-EVOLVE-01 §15). One machine-readable status file for the
founder: what is happening / waiting / failed / working / needed. Reuses
health vector + blocker registry + governor + finance. Read-only; writing
data/ops_snapshot.json is its only effect."""
import json
import os
from datetime import datetime, timezone

_FACTORY_ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(_FACTORY_ROOT, "data", "ops_snapshot.json")


def build_snapshot():
    snap = {"at": datetime.now(timezone.utc).isoformat()}
    try:
        import factory_health_vector
        v = factory_health_vector.health_vector()
        snap["health"] = {k: x["status"] for k, x in v.items()}
        snap["failing"] = [k for k, x in v.items() if x["status"] in ("CRITICAL", "DEGRADED")]
    except Exception as e:
        snap["health"] = "UNKNOWN (%s)" % e
    try:
        snap["blockers"] = json.load(
            open(os.path.join(_FACTORY_ROOT, "data", "external_blockers.json"),
                 encoding="utf-8"))["blockers"]
    except Exception:
        snap["blockers"] = "UNKNOWN"
    try:
        import experiment_governor
        snap["experiment"] = experiment_governor.protected_window_status()
    except Exception:
        snap["experiment"] = "UNKNOWN"
    try:
        fin = json.load(open(os.path.join(_FACTORY_ROOT, "finance_data.json"),
                             encoding="utf-8"))
        snap["revenue_usd"] = fin.get("totalSales", 0)
    except Exception:
        snap["revenue_usd"] = "UNKNOWN"
    try:
        import gumroad_auth_watch
        st = gumroad_auth_watch.read_state()
        snap["gumroad_auth"] = st.get("status", "UNKNOWN")
        snap["gumroad_auth_at"] = st.get("at", "UNKNOWN")
    except Exception:
        snap["gumroad_auth"] = "UNKNOWN"
    return snap


def write_snapshot():
    snap = build_snapshot()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=1)
    return snap


if __name__ == "__main__":
    print(json.dumps(build_snapshot(), indent=1)[:1500])
