#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Execution Status (Autonomous Global Execution Engine,
2026-07-23).

The real, per-opportunity status view the founder named: current phase,
current owner, completion %, blocking issue, business value, estimated
revenue, estimated effort, confidence, priority, expected completion.

Pure aggregation over already-real, already-computed sources — never a
new scoring or estimation model:
  - value_engine.compute_value_profile() for lifecycle_stage, at_risk,
    board_summary (Priority Score, Strategic Value, cost/lifetime-value
    estimates), all built ADR-102/105.
  - opportunity_pipeline.annotate_decision() for the real "confidence"
    field already recorded on the decision itself.

"Expected completion" has no real source anywhere in this factory today
(no historical per-stage duration tracking exists) — reported honestly
as Unknown, never a guessed date. "Current owner" is a real, static
mapping from each of the 10 real lifecycle stages to the real subsystem
that actually owns it; the 4 stages with no real capability (customer
testing, localization, global expansion, long-term maintenance) honestly
report no real owner rather than inventing one.
"""

from datetime import datetime, timezone

# Real subsystem ownership per real lifecycle stage
# (value_engine.classify_lifecycle_stage()'s 10 named stages). The 4
# stages with no real capability in this factory today (see ADR-105/
# ADR-103) honestly have no owner, never a fabricated one.
_OWNER_BY_STAGE = {
    "global_opportunity_discovery": "Golden Hunter / Market Intelligence",
    "evidence_based_validation": "Decision Engine",
    "prototype": "Production Pipeline",
    "customer_testing": None,
    "premium_production": "Production Pipeline (Dual Inspection)",
    "commercial_launch": "Distribution / Channels",
    "continuous_improvement": "Enterprise Readiness",
    "localization": None,
    "global_expansion": None,
    "long_term_maintenance": None,
}

_NO_OWNER_REASON = "لا قدرة حقيقية لهذه المرحلة في هذا المصنع اليوم (راجع ADR-103/ADR-105)"


def build_execution_status(niche, decisions_path=None, board_path=None, alerts_path=None,
                            reopen_log_path=None, evidence_path=None, timeline_path=None, outcomes_path=None,
                            profile=None):
    """Real execution status for one niche. Returns None (never
    fabricated) when this niche has no real ACCEPTED decision on record —
    matching value_engine.compute_value_profile()'s own scope.

    `profile` lets a caller that already has a real value_engine profile
    (e.g. build_execution_status_report(), batching over
    build_value_engine_report()'s own output) pass it straight through
    instead of triggering a second, redundant compute_value_profile()
    call for the same niche."""
    import value_engine
    import factory_orchestrator as fo
    import opportunity_pipeline as op

    if profile is None:
        profile = value_engine.compute_value_profile(
            niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
            timeline_path=timeline_path, outcomes_path=outcomes_path,
        )
    if profile is None:
        return None

    decision = fo.find_decision(niche, decisions_path=decisions_path)
    annotated = op.annotate_decision(decision, board_path=board_path, alerts_path=alerts_path, reopen_log_path=reopen_log_path)

    lifecycle = profile["lifecycle_stage"]
    stages = lifecycle["stages"]
    reached_count = sum(1 for s in stages.values() if s.get("reached"))
    completion_pct = round(100 * reached_count / len(stages), 1)

    current_phase = lifecycle.get("current_stage")
    owner = _OWNER_BY_STAGE.get(current_phase) if current_phase else None
    current_owner = owner if owner else {"value": None, "reason": _NO_OWNER_REASON}

    blocking_issue = _derive_blocking_issue(profile, stages)

    board_summary = profile["board_summary"]

    return {
        "niche": niche,
        "current_phase": current_phase,
        "current_owner": current_owner,
        "completion_pct": completion_pct,
        "blocking_issue": blocking_issue,
        "business_value": board_summary.get("strategic_value"),
        "estimated_revenue": board_summary.get("estimated_lifetime_value"),
        "estimated_effort": board_summary.get("estimated_build_cost"),
        "confidence": annotated.get("confidence"),
        "priority": board_summary.get("priority_score"),
        "expected_completion": {"value": None, "reason": "لا نموذج تقدير مدة حقيقي (لا تتبّع تاريخي لمدة كل مرحلة) في هذا المصنع بعد"},
        "final_outcome": lifecycle.get("final_outcome"),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def _derive_blocking_issue(profile, stages):
    """The real, honest blocker: an active at_risk flag takes priority
    (it's an active negative signal, not just 'not done yet'); otherwise
    the next unreached stage's own recorded reason IS the real blocker —
    never a separately invented explanation."""
    at_risk = profile.get("at_risk") or {}
    if at_risk.get("flagged"):
        return "؛ ".join(at_risk.get("reasons") or []) or None
    for stage in stages.values():
        if not stage.get("reached"):
            return stage.get("evidence")
    return None


def build_execution_status_report(decisions_path=None, board_path=None, alerts_path=None,
                                   reopen_log_path=None, evidence_path=None, timeline_path=None, outcomes_path=None):
    """Every real ACCEPTED opportunity's execution status, ranked by real
    Priority Score descending — reuses value_engine.build_value_engine_
    report()'s own real ranking and already-computed profiles directly,
    never a second ranking pass or a redundant compute_value_profile()
    call per niche."""
    import value_engine

    portfolio = value_engine.build_value_engine_report(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    statuses = [
        build_execution_status(
            p["niche"], decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
            timeline_path=timeline_path, outcomes_path=outcomes_path, profile=p,
        )
        for p in portfolio.get("profiles", [])
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(statuses),
        "opportunities": statuses,
    }
