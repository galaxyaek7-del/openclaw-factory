#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Factory Change Queue (V70, Tier-1 safe).

Three tiers (V70 s23):

- TIER_1_AUTO: whitelisted read-only/record/report actions the factory may
  run itself: drift_snapshot, health_check, consistency_check,
  test_run (local pytest, bounded), report_render.
- TIER_2_PREPARE: changes needing extra verification first -- prepared
  (proposal + impact note) but NEVER applied by this module.
- TIER_3_FOUNDER_GATE: money, permissions, sensitive external publish,
  legal/financial commitments, strategy -- merged into founder packets,
  never executed.

Append-only JSONL queue (data/factory_change_queue.jsonl). `run_tier1()`
executes ONLY the whitelist; anything else is recorded as HELD with its
tier and reason. No external calls, no code modification, no deletions.
"""
import json
import os
import subprocess
from datetime import datetime, timezone

_FACTORY_ROOT = os.path.dirname(os.path.abspath(__file__))
QUEUE_PATH = os.path.join(_FACTORY_ROOT, "data", "factory_change_queue.jsonl")

TIER_1_WHITELIST = {
    "drift_snapshot", "health_check", "consistency_check",
    "test_run", "report_render",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def classify_change(action, target=""):
    a = str(action).lower()
    t = str(target).lower()
    if a in TIER_1_WHITELIST:
        return "TIER_1_AUTO"
    if any(k in a or k in t for k in (
            "spend", "payment", "publish", "credential", "secret", "contract",
            "legal", "price", "external_post", "account", "strategy")):
        return "TIER_3_FOUNDER_GATE"
    return "TIER_2_PREPARE"


def enqueue(action, target="", detail="", proposer="factory_gap_engine"):
    entry = {"at": _now_iso(), "action": action, "target": target,
             "detail": detail, "proposer": proposer,
             "tier": classify_change(action, target), "state": "QUEUED"}
    with open(QUEUE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def list_queue(limit=50):
    if not os.path.exists(QUEUE_PATH):
        return []
    out = []
    for line in open(QUEUE_PATH, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out[-limit:]


def _exec_whitelist(action, target):
    if action == "drift_snapshot":
        import sys
        sys.path.insert(0, os.path.join(_FACTORY_ROOT, "scripts"))
        import drift_detector
        return drift_detector.snapshot()
    if action == "health_check":
        import factory_health_vector
        return factory_health_vector.health_vector()
    if action == "consistency_check":
        import canonical_inventory
        return canonical_inventory.detect_view_divergence()
    if action == "test_run":
        # Bounded local pytest over the V70 Tier-1 test files only.
        r = subprocess.run(
            ["python", "-m", "pytest", "tests/test_experiment_governor.py",
             "tests/test_canonical_inventory.py",
             "tests/test_factory_health_vector.py",
             "tests/test_factory_change_queue.py",
             "tests/test_factory_gap_engine.py", "-q"],
            capture_output=True, text=True, cwd=_FACTORY_ROOT, timeout=300)
        return {"returncode": r.returncode, "tail": r.stdout[-500:]}
    if action == "report_render":
        import factory_gap_engine
        return factory_gap_engine.run_cycle(write_report=False)
    raise ValueError("not whitelisted: %r" % action)


def run_tier1(limit=10):
    """Execute queued TIER_1_AUTO entries only. Everything else: HELD."""
    results = []
    for entry in list_queue(limit=200)[-limit:]:
        if entry.get("state") != "QUEUED" or entry.get("tier") != "TIER_1_AUTO":
            continue
        try:
            output = _exec_whitelist(entry["action"], entry.get("target", ""))
            results.append({"action": entry["action"], "state": "EXECUTED",
                            "output_keys": list(output.keys()) if isinstance(output, dict) else "n/a"})
        except Exception as e:
            results.append({"action": entry["action"], "state": "FAILED", "error": str(e)[:200]})
    return results
