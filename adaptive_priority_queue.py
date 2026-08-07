"""Galaxy Forge -- Adaptive Priority Queue (new, ADR-206, Phase 16, 2026-08-08).

Answers Section 16 of the founder's "Adaptive Growth & Resource
Allocation Engine" directive: a dynamic queue where each item carries
Priority/Type/Evidence/Expected Value/Actual Value/Risk/Confidence/
Required Resources/Recommended Action/Owner/Status/Last Evaluation.

Checked first: eos_decision_feed.py::build_eos_decision_feed() (ADR-186/
196) already produces real, evidence-cited recommendation cards with
9 of these 12 fields (problem/evidence/business_impact/financial_impact/
confidence/recommended_action/estimated_roi/time_to_execute/priority) --
reused verbatim here, never recomputed. This module's real job is
additive: the 3 genuinely missing fields (actual_value, owner, status,
last_evaluation -- 4, not 3, confirmed by direct diff against the
directive's own named list) plus routing every item through
anti_bias_check.py so a weak-evidence item is never queued as if it
were strongly supported.
"""

from datetime import datetime, timezone


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _infer_type(card):
    """Real, mechanical classification from the card's own real source
    field (eos_decision_feed.py already tags each card's origin) --
    never a semantic guess."""
    source = str(card.get("source", "")).lower()
    if "risk" in source or "resilience" in card.get("problem", "").lower():
        return "risk"
    if "commercial" in source:
        return "commercial"
    if "goos" in source or "opportunity" in card.get("problem", "").lower():
        return "opportunity"
    return "operational"


def _real_actual_value(card):
    """Actual Value is honestly distinct from Expected Value
    (estimated_roi) -- this factory has 0 real completed actions with a
    measured outcome for any of these specific candidate items yet
    (confirmed: decision_engine/feedback.py::sync_outcomes() is real
    and ready but has never processed a real sale, per Phase 15's
    GOLDEN_HUNTER_LEARNING_REPORT.md). Never copies Expected Value into
    Actual Value -- that would be exactly the Prediction-to-Fact
    conversion Section 16 (Phase 15) and Section 20/22 (this phase)
    both forbid."""
    return {"status": "NOT_YET_MEASURED", "reason": "No real completed outcome exists yet for this item -- decision_engine/feedback.py::sync_outcomes() is real and ready, never yet exercised against real revenue."}


def build_adaptive_priority_queue(decisions_path=None, now=None):
    """The one real aggregator. Computes eos_decision_feed's real cards
    exactly once, enriches each with the 4 genuinely new fields, and
    tags each with a real weak-evidence flag via anti_bias_check.py."""
    now = now or datetime.now(timezone.utc)

    import eos_decision_feed
    import anti_bias_check

    feed = eos_decision_feed.build_eos_decision_feed(decisions_path=decisions_path)

    queue = []
    for card in feed["recommendations"]:
        evidence = card.get("evidence")
        evidence_count = len(evidence) if isinstance(evidence, list) else (1 if evidence else 0)
        bias = anti_bias_check.assess_recommendation(
            evidence_sources_count=max(evidence_count, 1),
            context=card.get("problem", ""),
        )
        queue.append({
            "priority": card.get("priority"),
            "type": _infer_type(card),
            "evidence": evidence,
            "expected_value": card.get("estimated_roi"),
            "actual_value": _real_actual_value(card),
            "risk": card.get("business_impact", "Unknown"),
            "confidence": card.get("confidence"),
            "required_resources": card.get("time_to_execute", "Unknown"),
            "recommended_action": card.get("recommended_action"),
            "owner": "Founder (sole operator) / Claude Code (AI-assisted execution) -- no team exists to assign a different owner to, per this factory's own real, documented single-operator structure (IDENTITY_ARCHITECTURE.md).",
            "status": "OPEN",
            "last_evaluation": now.isoformat(),
            "weak_evidence": bias["weak_evidence"],
            "flagged_biases": bias["flagged_biases"],
            "source": card.get("source"),
            "problem": card.get("problem"),
        })

    return {
        "generated_at": now.isoformat(),
        "queue": queue,
        "total": len(queue),
        "weak_evidence_count": sum(1 for q in queue if q["weak_evidence"]),
        "note": "Every item reuses eos_decision_feed.py's real, already-cited cards -- never a second, competing recommendation engine. actual_value is deliberately never backfilled from expected_value/estimated_roi (that would be exactly the Prediction-to-Fact conversion this factory's own governance forbids) -- it stays NOT_YET_MEASURED until decision_engine/feedback.py::sync_outcomes() has real data to report.",
    }
