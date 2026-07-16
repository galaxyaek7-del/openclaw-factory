"""
Production Evidence Record (ADR-055) — the 9 required fields for one
opportunity, assembled by calling validation_layer.lifecycle.
build_lifecycle() (reused directly, never re-implemented — that function
is the one place that already matches orchestrator timeline records to a
niche via orchestrator.orchestrator.make_idempotency_key()) plus honest
extraction of the handful of fields that function does not already
surface on its own: platform, customer feedback, and one final-outcome
classification.
"""

from validation_layer import lifecycle as lifecycle_module


def _latest(records):
    return records[-1] if records else None


def _extract_platforms(publishing_stage_events):
    """Real platforms actually attempted/succeeded, read straight from
    publishing's own recorded output (channels/registry.py arm names as
    orchestrator/engines/publishing.py already records them) — never
    guessed, never inferred from decision text."""
    attempted, succeeded = [], []
    for event in publishing_stage_events:
        for o in (event.get("output") or {}).get("outcomes") or []:
            if o.get("attempted"):
                attempted.append(o.get("arm"))
            if o.get("ok"):
                succeeded.append(o.get("arm"))
    if not attempted:
        return {"attempted": [], "succeeded": [], "reason": "لا محاولة نشر حقيقية مسجَّلة بعد"}
    return {"attempted": attempted, "succeeded": succeeded}


def _extract_customer_feedback(revenue_events):
    """Best-effort only: this factory has no connected review/feedback
    channel of any kind — confirmed, no such module exists anywhere in
    this codebase. A real sale's raw payload is checked for a small set
    of plausible field names (Gumroad's own documented sale shape); if
    none are present, this is honestly Unknown, never invented."""
    feedback = []
    for event in revenue_events:
        raw = (event.get("raw_sale_event") or {}).get("raw", {}) or {}
        for field in ("review", "rating", "comment", "feedback"):
            if raw.get(field) is not None:
                feedback.append({"decision_id": event.get("decision_id"), field: raw[field]})
    if not feedback:
        return {"answer": "Unknown", "reason": "لا قناة ملاحظات عملاء حقيقية متصلة بهذا المصنع بعد"}
    return {"answer": feedback}


def _classify_final_outcome(decision_records, production_events, publishing_events, revenue_events):
    latest_decision = _latest(decision_records)
    if latest_decision is None:
        return "NOT_YET_EVALUATED"
    if latest_decision.get("status") == "REJECTED":
        return "REJECTED"
    if revenue_events:
        return "SOLD"

    production_succeeded = any(e.get("status") == "SUCCESS" for e in production_events)
    publishing_succeeded = any(e.get("status") == "SUCCESS" for e in publishing_events)
    if production_succeeded and publishing_succeeded:
        return "PRODUCED_AND_PUBLISHED_NOT_YET_SOLD"
    if production_succeeded:
        return "PRODUCED_NOT_YET_PUBLISHED"
    if latest_decision.get("status") == "ACCEPTED":
        return "ACCEPTED_PENDING_EXECUTION"
    return "DEFERRED"


def build_evidence_record(niche, tier="tier4", timeline_path=None, decisions_path=None, outcomes_path=None):
    lc = lifecycle_module.build_lifecycle(
        niche, tier=tier, timeline_path=timeline_path, decisions_path=decisions_path, outcomes_path=outcomes_path,
    )
    latest_decision = _latest(lc["decision_records"])

    return {
        "niche": lc["niche"],
        "tier": lc["tier"],
        "discovery_timestamp": lc["signal"]["at"],
        "evidence_snapshot": latest_decision.get("evaluation_snapshot") if latest_decision else None,
        "decision": (
            {
                "status": latest_decision.get("status"),
                "ai_ceo_decision": latest_decision.get("ai_ceo_decision"),
                "reasoning": latest_decision.get("reasoning"),
            }
            if latest_decision else
            {"status": "Unknown", "reason": "لم يُتَّخَذ قرار بعد لهذا النيتش"}
        ),
        "execution_status": lc["production"],
        "publishing_status": lc["publishing"],
        "platform": _extract_platforms(lc["publishing"]),
        "revenue_events": lc["revenue"],
        "customer_feedback": _extract_customer_feedback(lc["revenue"]),
        "final_outcome": _classify_final_outcome(lc["decision_records"], lc["production"], lc["publishing"], lc["revenue"]),
        "source": "validation_layer.lifecycle.build_lifecycle()",
    }
