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
        "expected_roi": board_summary.get("expected_roi"),
        "confidence": annotated.get("confidence"),
        "priority": board_summary.get("priority_score"),
        "dependencies": {"value": None, "reason": "لا تتبّع اعتمادية حقيقي بين الفرص التجارية في هذا المصنع اليوم — dependency_graph.py يحسب اعتمادية ملفات الكود، لا اعتمادية فرص العمل"},
        "learning_feedback": _derive_learning_feedback(profile, annotated),
        "expected_completion": {"value": None, "reason": "لا نموذج تقدير مدة حقيقي (لا تتبّع تاريخي لمدة كل مرحلة) في هذا المصنع بعد"},
        "final_outcome": lifecycle.get("final_outcome"),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def _derive_learning_feedback(profile, annotated):
    """Real, per-opportunity 'what has this factory actually learned
    about this niche so far' signal (Autonomous Global Commercial
    Company Layer, 2026-07-24) — pure aggregation over data
    build_execution_status() already fetched, never a new computation:
    market_memory.py's real commercial evidence (already in `profile`,
    Global Market Learning Engine, ADR-106) + this niche's real Decision
    Re-open history (already in `annotated`, ADR-096). Honestly reports
    zero real learning signal when neither exists yet, rather than
    padding the field with something that looks populated."""
    market_memory_profile = profile.get("market_memory") or {}
    reopen_history = annotated.get("reopen_history") or []

    if not market_memory_profile.get("sample_size") and not reopen_history:
        return {"has_real_signal": False, "reason": "لا أدلة مبيعات حقيقية ولا إعادة فتح قرار حقيقية بعد لهذا النيتش"}

    return {
        "has_real_signal": True,
        "real_sales_sample_size": market_memory_profile.get("sample_size", 0),
        "total_revenue_to_date": market_memory_profile.get("total_revenue"),
        "real_reopen_events": len(reopen_history),
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
                                   reopen_log_path=None, evidence_path=None, timeline_path=None,
                                   outcomes_path=None, limit=None):
    """Every real ACCEPTED opportunity's execution status, ranked by real
    Priority Score descending — reuses value_engine.build_value_engine_
    report()'s own real ranking and already-computed profiles directly,
    never a second ranking pass or a redundant compute_value_profile()
    call per niche.

    `limit` (Autonomous Global Commercial Company Layer, 2026-07-24):
    forwarded to value_engine.build_value_engine_report()'s own real
    scale valve — see its docstring for the measured cost and the
    honest tradeoff. Default None preserves exact prior behavior.

    Global Autonomous Business Operating System (2026-07-24): each
    opportunity also gets a real `next_action` — scheduler.py's own
    5-bucket classification for this exact niche, joined from one real,
    UNLIMITED scheduling pass (never limited even when this report's own
    `limit` is set, so a bucket assignment is never silently wrong for
    an opportunity this report happens to be showing). When `limit` is
    None, the already-computed unlimited portfolio is reused for
    scheduling too — zero redundant computation; a `limit` costs that
    one optimization, not correctness."""
    import value_engine
    import scheduler

    portfolio = value_engine.build_value_engine_report(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path, limit=limit,
    )
    scheduling = scheduler.decide_next_actions(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
        portfolio=portfolio if limit is None else None,
    )
    next_action_by_niche = {}
    for bucket_name, items in scheduling["buckets"].items():
        for item in items:
            next_action_by_niche[item["niche"]] = {"bucket": bucket_name, "reason": item["reason"]}

    statuses = [
        {
            **build_execution_status(
                p["niche"], decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
                reopen_log_path=reopen_log_path, evidence_path=evidence_path,
                timeline_path=timeline_path, outcomes_path=outcomes_path, profile=p,
            ),
            "next_action": next_action_by_niche.get(p["niche"], {"bucket": "wait", "reason": "لا تصنيف حقيقي بعد"}),
        }
        for p in portfolio.get("profiles", [])
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(statuses),
        "total_accepted": portfolio.get("total_accepted"),
        "limited_to": limit,
        "opportunities": statuses,
        "bottleneck_summary": _summarize_bottlenecks(statuses),
    }


def _summarize_bottlenecks(statuses):
    """Real, portfolio-wide tally of blocking_issue reasons — never a
    separately invented category, purely a count over what's already
    real per opportunity."""
    from collections import Counter

    reasons = Counter(s["blocking_issue"] for s in statuses if s.get("blocking_issue"))
    return {
        "opportunities_with_a_real_blocker": sum(reasons.values()),
        "top_reasons": [{"reason": r, "count": c} for r, c in reasons.most_common(5)],
    }
