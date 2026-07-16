"""
Engine health (ADR-052) — real, per-engine health computed entirely from
the immutable orchestrator timeline (data/orchestrator_timeline.jsonl,
ADR-051). An engine with zero recorded executions is reported as
DISCOVERY (no data), never assumed "healthy" by default — a fabricated
green status with nothing behind it is exactly what this factory's
capability-maturity discipline (config/capability_registry.json) forbids.
"""

from orchestrator import timeline as orch_timeline
from orchestrator.types import EXECUTION_ORDER


def compute_engine_health(timeline_path=None):
    records = list(orch_timeline.read_timeline(path=timeline_path))
    health = {}

    for stage in EXECUTION_ORDER:
        stage_records = [r for r in records if r.get("engine") == stage]
        if not stage_records:
            health[stage] = {
                "maturity": "DISCOVERY",
                "total_executions": 0,
                "reason": f"لا تنفيذ واحد مسجَّل بعد لمحرّك {stage} في data/orchestrator_timeline.jsonl",
            }
            continue

        successes = sum(1 for r in stage_records if r.get("status") == "SUCCESS")
        failures = sum(1 for r in stage_records if r.get("status") == "FAILED")
        skips = sum(1 for r in stage_records if str(r.get("status", "")).startswith("SKIPPED"))
        last = stage_records[-1]

        health[stage] = {
            "maturity": "REAL",
            "total_executions": len(stage_records),
            "successes": successes,
            "failures": failures,
            "skips": skips,
            "success_rate": round(100 * successes / (successes + failures), 1) if (successes + failures) else None,
            "last_status": last.get("status"),
            "last_run_at": last.get("finished_at"),
            "source": "data/orchestrator_timeline.jsonl",
        }

    return health
