"""
Per-opportunity lifecycle reconstruction (ADR-053).

Reconstructs Signal -> Analysis -> Decision -> Queue -> Production ->
Publishing -> Revenue -> Learning for one niche purely by reading
already-recorded real sources — no new recording mechanism, so this can
never diverge from what actually happened:

  Signal      no independent record exists — equivalent to the first
              real market_intelligence timeline entry's started_at,
              documented as an equivalence here, never invented.
  Analysis    orchestrator timeline records for the "market_intelligence"
              stage, matched via the SAME deterministic idempotency key
              orchestrator.py itself computes (reused, not re-derived).
  Decision    orchestrator timeline records for the "decision" stage,
              plus the full Decision record(s) from decision_engine.store
              (status + real, already-stored reasoning).
  Queue       the real decided_at timestamp(s) whenever a Decision's
              status was ACCEPTED — a state entry, not a separate engine.
  Production  orchestrator timeline records for the "production" stage.
  Publishing  orchestrator timeline records for the "publishing" stage.
  Revenue     matched Outcome record(s) from decision_engine.store, i.e.
              a real sale (channels/ledger.py) confirmed linked to this
              niche's decision.
  Learning    orchestrator timeline records for the "learning" stage
              (factory-wide work, but keyed per niche+tier for
              traceability the same way every other stage is).
"""

import re
from datetime import datetime

from decision_engine import store as decision_store
from orchestrator import timeline as orch_timeline
from orchestrator.orchestrator import make_idempotency_key
from orchestrator.types import EXECUTION_ORDER


def _normalize(niche):
    return re.sub(r"\s+", " ", str(niche or "").strip().lower())


def _duration_seconds(record):
    try:
        started = datetime.fromisoformat(record["started_at"])
        finished = datetime.fromisoformat(record["finished_at"])
        return round((finished - started).total_seconds(), 3)
    except (KeyError, ValueError, TypeError):
        return None


def _stage_events(stage, niche, tier, all_records):
    key = make_idempotency_key(stage, niche, tier)
    matches = sorted(
        (r for r in all_records if r.get("idempotency_key") == key),
        key=lambda r: r.get("started_at") or "",
    )
    return [
        {
            "status": r.get("status"),
            "started_at": r.get("started_at"),
            "finished_at": r.get("finished_at"),
            "duration_seconds": _duration_seconds(r),
            "error": r.get("error"),
            # ADR-055: the real, unabridged engine output (e.g. publishing's
            # per-platform outcomes) — additive only, every existing key
            # above is unchanged, so no existing caller is affected.
            "output": r.get("output", {}),
        }
        for r in matches
    ]


def build_lifecycle(niche, tier="tier4", timeline_path=None, decisions_path=None, outcomes_path=None):
    all_records = list(orch_timeline.read_timeline(path=timeline_path))
    stages = {stage: _stage_events(stage, niche, tier, all_records) for stage in EXECUTION_ORDER}

    decision_history = decision_store.find_decisions_by_niche(niche, path=decisions_path)
    queue_events = [
        {"decided_at": d.get("decided_at"), "opportunity_score": d.get("opportunity_score")}
        for d in decision_history if d.get("status") == "ACCEPTED"
    ]

    key = _normalize(niche)
    revenue_events = [
        o for o in decision_store.read_outcomes(path=outcomes_path)
        if _normalize(o.get("niche")) == key
    ]

    signal_events = stages["market_intelligence"]
    if signal_events:
        signal = {"at": signal_events[0]["started_at"], "note": "يُطابق أول تنفيذ market_intelligence حقيقي — لا سجل 'إشارة' مستقل"}
    else:
        signal = {"at": None, "note": "لم تُكتشَف هذه الفرصة بعد — صفر تنفيذ market_intelligence حقيقي مسجَّل"}

    return {
        "niche": niche,
        "tier": tier,
        "signal": signal,
        "analysis": stages["market_intelligence"],
        "decision": stages["decision"],
        "decision_records": decision_history,
        "queue": queue_events,
        "production": stages["production"],
        "publishing": stages["publishing"],
        "revenue": revenue_events,
        "learning": stages["learning"],
    }
