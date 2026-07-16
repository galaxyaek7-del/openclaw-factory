"""
Real stage-duration statistics (ADR-053) — computed only from timeline
records that actually ran (SKIPPED_* records are excluded: their
duration is ~0 by definition and averaging them in would understate real
processing time dishonestly, not just be a rounding quirk).
"""

from datetime import datetime

from orchestrator import timeline as orch_timeline
from orchestrator.types import EXECUTION_ORDER


def _duration_seconds(record):
    try:
        started = datetime.fromisoformat(record["started_at"])
        finished = datetime.fromisoformat(record["finished_at"])
        return (finished - started).total_seconds()
    except (KeyError, ValueError, TypeError):
        return None


def compute_stage_durations(timeline_path=None):
    records = list(orch_timeline.read_timeline(path=timeline_path))
    by_engine = {}

    for r in records:
        if str(r.get("status", "")).startswith("SKIPPED"):
            continue
        dur = _duration_seconds(r)
        if dur is None:
            continue
        by_engine.setdefault(r.get("engine"), []).append(dur)

    result = {}
    for stage in EXECUTION_ORDER:
        durations = by_engine.get(stage)
        if not durations:
            result[stage] = {
                "maturity": "DISCOVERY",
                "reason": f"لا تنفيذ حقيقي (غير SKIPPED) مسجَّل بعد لمحرّك {stage} لحساب المدة",
            }
            continue
        result[stage] = {
            "maturity": "REAL",
            "sample_size": len(durations),
            "average_seconds": round(sum(durations) / len(durations), 3),
            "min_seconds": round(min(durations), 3),
            "max_seconds": round(max(durations), 3),
        }
    return result
