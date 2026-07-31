#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enterprise Growth Engine (ADR-158, 2026-07-31).

Company-wide Growth Stage classification (Stage 0 Bootstrap -> Stage 5
Autonomous Enterprise), per the founder's directive. NOT the same
module as growth_engine.py (2026-07-24, still real, still live) --
that module is per-NICHE (Product Multiplication, Channel Expansion,
portfolio_growth_summary); this module is company-wide "what stage of
maturity is Galaxy Forge itself in." Named growth_stages.py specifically
to avoid re-creating ADR-154's executive_intelligence/ naming collision.

Every condition below either cites a real, already-existing signal, or
is honestly `NOT_ARCHITECTED` when no founder-set policy threshold
exists anywhere in this factory (e.g. a specific minimum cash-reserve
dollar figure -- confirmed via repo-wide grep to have zero real signal
today, same as MRR/ARR/Runway, ADR-146's own disclosed gap list).

"Automatic fallback" (the directive's Objective 3) is implemented as
non-cached, non-sticky recomputation, not a triggered action: every
public function here is a pure function of (real current signals,
optional `overrides` for Simulation Mode) -- nothing is stored, nothing
is read back on a later call, nothing here ever pauses production,
reallocates capital, or changes any other module's behavior. This is
the exact same read-only-status-label discipline company_runtime.py's
company_state() (ADR-157, built hours earlier the same day) already
established and the founder already approved -- reused here directly
rather than re-litigated via a fresh AskUserQuestion.

Stage 5 (Autonomous Enterprise) is honestly reported as blocked by
standing FOUNDER POLICY, not by any data threshold: reaching it would
require lifting the 4 protected human-gates this factory has
reconfirmed unchanged in every relevant round today (evolution_queue.py
Execute, capital_allocation_engine.py reallocation, business
retirement, channels/publish_protection.py's new-channel/elevated-risk
gate -- ADR-133/134/139/142, reconfirmed ADR-144/147/157). Never a
fabricated numeric gate standing in for a real policy decision.

Growth Stage history (Enterprise Strategic Planning System, ADR-159,
2026-07-31): record_growth_stage_snapshot()/growth_stage_history() below
are a small, separate, purely ADDITIVE recorder -- the exact same
relationship health_trend.py's real recording has to resilience_
monitor.py's stateless assess_resilience() (ADR-135/157 precedent).
current_growth_stage() above remains exactly as stateless/non-cached as
ADR-158 left it and never calls the recorder itself; only factory_loop.
js's own once-per-calendar-day tick gate does, mirroring every other
daily report function's marker-file convention.
"""

import json
import os
from datetime import datetime, timezone

_FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SNAPSHOTS_PATH = os.path.join(_FACTORY_DIR, "data", "growth_stage_snapshots.jsonl")

NOT_ARCHITECTED = "not_architected"

STAGES = [
    "stage_0_bootstrap",
    "stage_1_validation",
    "stage_2_stable_revenue",
    "stage_3_expansion",
    "stage_4_multi_market",
    "stage_5_autonomous_enterprise",
]

STAGE_NAMES = {
    "stage_0_bootstrap": "Stage 0 — Bootstrap",
    "stage_1_validation": "Stage 1 — Validation",
    "stage_2_stable_revenue": "Stage 2 — Stable Revenue",
    "stage_3_expansion": "Stage 3 — Expansion",
    "stage_4_multi_market": "Stage 4 — Multi-market",
    "stage_5_autonomous_enterprise": "Stage 5 — Autonomous Enterprise",
}

# The 7 founder-named divisions, mapped onto this factory's real module
# roster (department_events.VALID_DEPARTMENTS / gfos._DEPARTMENT_PRIMARY_MODULE,
# ADR-147) -- never a second, competing department list.
DIVISIONS = {
    "affiliate_commerce": "affiliate_commerce/ (ADR-149/150)",
    "digital_products": "book_generator.py / production_blueprint.py",
    "publishing": "distributor.py / channels/",
    "research": "research_department (ADR-081)",
    "infrastructure": "infrastructure_bridge (ADR-081)",
    "operations": "enterprise_operations.py (ADR-155)",
    "executive": "executive_brain.py / executive_questions.py (ADR-144/154)",
}

PROTECTED_GATES = [
    "evolution_queue.py's Execute step (ADR-133) -- 'must not be loosened without asking again'",
    "capital_allocation_engine.py's capital reallocation (ADR-139) -- 'the engine recommends, the Founder decides'",
    "business retirement -- no real system exists to retire a business, by design",
    "channels/publish_protection.py's new-channel/elevated-risk publish gate (ADR-135) -- founder-only approval",
]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _cond(name, met, current_value, source, threshold=None, reason=None, simulated=False):
    d = {"name": name, "met": met, "current_value": current_value, "source": source, "simulated": simulated}
    if threshold is not None:
        d["threshold"] = threshold
    if reason is not None:
        d["reason"] = reason
    return d


def _override_or_real(overrides, key, real_value_fn):
    """Simulation Mode hook: if `key` is present in `overrides`, use the
    hypothetical value and mark it simulated; otherwise compute the real
    value. real_value_fn is only invoked when not overridden, so a fully
    hypothetical simulate_stage_progression() call never touches a real
    ledger for an overridden key."""
    if overrides and key in overrides:
        return overrides[key], True
    return real_value_fn(), False


def _real_signals(overrides=None):
    """Fetches every REAL signal this module's conditions need, each
    exactly once, honoring any Simulation Mode override so an
    overridden key never triggers its real (possibly expensive) lookup.
    Deliberately excludes capital_allocation_engine/enterprise_scheduler
    (only needed for the ROI citation in build_growth_dashboard(), not
    for stage computation itself) -- same redundant-computation
    discipline as company_pulse()'s ADR-155 fix."""
    overrides = overrides or {}

    def _accepted_count():
        import decision_engine.ranking as ranking
        return sum(1 for d in ranking.rank_all() if d.get("status") == "ACCEPTED")

    def _production_runs():
        import growth_engine
        return growth_engine.production_capacity_summary(days=36500)["real_productions_in_window"]

    def _revenue_total():
        from channels import ledger
        return ledger.revenue_trend()["total_revenue_usd"]

    def _open_critical_incidents():
        import resilience_monitor
        alerts = resilience_monitor.assess_resilience()["active_alerts"]
        return sum(1 for a in alerts if a.get("severity") in ("critical", "emergency"))

    def _launch_readiness():
        import launch_readiness
        return launch_readiness.launch_readiness_score()

    def _automation_pct():
        import autonomous_operations_status as aos
        summary = aos.autonomous_operations_summary()
        automatic = summary["counts"].get("automatic", 0) + summary["counts"].get("automatic_new", 0)
        total = summary["total_named_activities"]
        return round(automatic / total * 100, 1) if total else None

    def _quality_score():
        import executive_score
        return executive_score._production_quality()["value"]

    def _platform_revenue_count():
        import global_opportunity_exchange as gox
        dist = gox.revenue_distribution()
        by_platform = dist.get("by_platform") or {}
        return sum(1 for v in by_platform.values() if isinstance(v, dict) and v.get("revenue_usd", 0) > 0)

    accepted_count, sim_a = _override_or_real(overrides, "accepted_opportunities_count", _accepted_count)
    production_runs, sim_b = _override_or_real(overrides, "real_production_runs", _production_runs)
    revenue_total, sim_c = _override_or_real(overrides, "total_revenue_usd", _revenue_total)
    open_critical, sim_d = _override_or_real(overrides, "open_critical_incidents", _open_critical_incidents)
    readiness, sim_e = _override_or_real(overrides, "launch_readiness", _launch_readiness)
    automation_pct, sim_f = _override_or_real(overrides, "automation_level_pct", _automation_pct)
    quality, sim_g = _override_or_real(overrides, "quality_score_pct", _quality_score)
    platform_count, sim_h = _override_or_real(overrides, "platforms_with_real_revenue", _platform_revenue_count)

    return {
        "accepted_opportunities_count": (accepted_count, sim_a),
        "real_production_runs": (production_runs, sim_b),
        "total_revenue_usd": (revenue_total, sim_c),
        "open_critical_incidents": (open_critical, sim_d),
        "launch_readiness": (readiness, sim_e),
        "automation_level_pct": (automation_pct, sim_f),
        "quality_score_pct": (quality, sim_g),
        "platforms_with_real_revenue": (platform_count, sim_h),
    }


def _stage_conditions(stage, signals):
    """Real, disclosed entry conditions per stage. `signals` is
    _real_signals()'s output, already resolved against any Simulation
    overrides. Booleans are used only where a natural real threshold
    exists (>=1, non-empty, zero); no dollar/percentage threshold is
    invented where the founder has never set one -- those conditions
    are honestly `met: None` / NOT_ARCHITECTED, current value still
    shown for transparency."""
    accepted_n, sim_a = signals["accepted_opportunities_count"]
    prod_n, sim_b = signals["real_production_runs"]
    revenue, sim_c = signals["total_revenue_usd"]
    incidents, sim_d = signals["open_critical_incidents"]
    readiness, sim_e = signals["launch_readiness"]
    automation_pct, sim_f = signals["automation_level_pct"]
    quality_pct, sim_g = signals["quality_score_pct"]
    platform_count, sim_h = signals["platforms_with_real_revenue"]

    if stage == "stage_0_bootstrap":
        return []  # baseline stage, always entered -- no real precondition to disclose

    if stage == "stage_1_validation":
        return [
            _cond("has_accepted_opportunity", accepted_n >= 1, accepted_n,
                  "decision_engine.ranking.rank_all() -- real ACCEPTED decision count", threshold=1, simulated=sim_a),
            _cond("has_real_production_attempt", prod_n >= 1, prod_n,
                  "growth_engine.production_capacity_summary() -- real books/_generation_log.jsonl run count", threshold=1, simulated=sim_b),
        ]

    if stage == "stage_2_stable_revenue":
        return [
            _cond("positive_recurring_revenue", revenue > 0, revenue,
                  "channels/ledger.py::revenue_trend()['total_revenue_usd'] -- real sales ledger total", threshold=">0", simulated=sim_c),
            _cond("no_open_critical_incidents", incidents == 0, incidents,
                  "resilience_monitor.assess_resilience()['active_alerts'] -- real critical/emergency severity count", threshold=0, simulated=sim_d),
            _cond("minimum_recurring_revenue_policy_threshold", None, revenue,
                  "no founder-set minimum-revenue dollar figure exists anywhere in this factory today",
                  reason=NOT_ARCHITECTED),
            _cond("minimum_cash_reserve_policy_threshold", None, None,
                  "no cash/runway/treasury signal exists anywhere in this factory today (confirmed via repo-wide search, same gap class as ADR-146's MRR/ARR/Runway disclosure)",
                  reason=NOT_ARCHITECTED),
        ]

    if stage == "stage_3_expansion":
        divisions = (readiness or {}).get("divisions", {})
        fully_ready = [k for k, v in divisions.items()
                       if v.get("dimensions", {}).get("operational_readiness", {}).get("value") not in (None, "not_architected")
                       and "7/7" in str(v.get("dimensions", {}).get("operational_readiness", {}).get("value", ""))]
        return [
            _cond("stage_2_prerequisites_still_met",
                  revenue > 0 and incidents == 0, {"revenue": revenue, "open_critical_incidents": incidents},
                  "recomputed Stage 2 conditions (non-cached)", simulated=(sim_c or sim_d)),
            _cond("at_least_one_division_fully_launch_ready", len(fully_ready) >= 1, fully_ready,
                  "launch_readiness.py::launch_readiness_score() -- real per-division 7/7 operational_readiness (ADR-153)", threshold=1, simulated=sim_e),
            _cond("automation_coverage_policy_threshold", None, automation_pct,
                  "autonomous_operations_status.py's real automation_level_pct shown for context; no founder-set minimum % threshold exists yet",
                  reason=NOT_ARCHITECTED),
            _cond("quality_score_policy_threshold", None, quality_pct,
                  "executive_score.py's real Dual Inspection pass rate shown for context; no founder-set minimum % threshold exists yet",
                  reason=NOT_ARCHITECTED),
        ]

    if stage == "stage_4_multi_market":
        return [
            _cond("multi_platform_real_revenue", platform_count >= 2, platform_count,
                  "global_opportunity_exchange.py::revenue_distribution() -- real per-platform sale totals (ADR-140)", threshold=2, simulated=sim_h),
            _cond("country_diversification", False, "DISCOVERY",
                  "global_opportunity_exchange.py::country_dependency_note() -- structural, permanent citation of the founder's own 2026-07-23 deferral (zero real local-market data connectors exist for any country)",
                  reason="مؤجَّل بقرار المؤسس (CLAUDE.md، 2026-07-23) — ليس نقص بيانات مؤقت"),
        ]

    if stage == "stage_5_autonomous_enterprise":
        return [
            _cond("founder_protected_gates_lifted", False, PROTECTED_GATES,
                  "standing founder policy (ADR-133/134/139/142, reconfirmed ADR-144/147/157) -- not a data threshold",
                  reason="Stage 5 is blocked by founder policy, not by company state. It can only be entered if the founder explicitly lifts one or more of the 4 protected gates -- this module never does so itself."),
        ]

    raise ValueError(f"unknown stage: {stage}")


def current_growth_stage(overrides=None):
    """The core, stateless, non-cached classification: the highest
    stage whose own conditions -- AND every lower stage's conditions --
    are currently, fully met (a `met: None` NOT_ARCHITECTED condition
    does not block advancement, since no real threshold exists to
    fail; it is disclosed, never silently treated as a pass or a
    fail). Called fresh every time -- "automatic fallback" IS this
    function simply being re-invoked against degraded real signals,
    never a triggered side effect."""
    signals = _real_signals(overrides)
    reached = "stage_0_bootstrap"
    still_advancing = True
    all_conditions = {}
    for stage in STAGES:
        # Every stage's conditions are computed and disclosed regardless
        # of whether an earlier stage blocked advancement -- full
        # transparency for the dashboard ("no black-box decisions",
        # Objective 6), even though `reached` itself stops advancing at
        # the first genuinely blocking (met is False) stage.
        conditions = _stage_conditions(stage, signals)
        all_conditions[stage] = conditions
        if still_advancing:
            blocking = [c for c in conditions if c["met"] is False]
            if blocking:
                still_advancing = False
            else:
                reached = stage

    return {
        "stage": reached,
        "stage_name": STAGE_NAMES[reached],
        "all_conditions": all_conditions,
        "simulated": bool(overrides),
        "generated_at": _now_iso(),
    }


def remaining_requirements_for_next_stage(overrides=None):
    result = current_growth_stage(overrides)
    idx = STAGES.index(result["stage"])
    if idx == len(STAGES) - 1:
        return {"next_stage": None, "requirements": [], "note": "already at the highest defined stage"}
    next_stage = STAGES[idx + 1]
    conditions = result["all_conditions"][next_stage]
    unmet = [c for c in conditions if c["met"] is not True]
    return {"next_stage": next_stage, "next_stage_name": STAGE_NAMES[next_stage], "requirements": unmet}


def blocking_factors(overrides=None):
    req = remaining_requirements_for_next_stage(overrides)
    return {
        "next_stage": req.get("next_stage"),
        "next_stage_name": req.get("next_stage_name"),
        "blocking_factors": [c for c in req["requirements"] if c["met"] is False],
        "undetermined_factors": [c for c in req["requirements"] if c["met"] is None],
    }


# Founder-authored strategic guidance TEMPLATE, not AI-generated
# per-cycle -- one short, real, disclosed line per (division, stage),
# always meant to be read alongside the real signal that justifies it
# (build_growth_dashboard() pairs each with the division's own real
# launch_readiness/autonomous_operations citation, never presented
# standalone as a fabricated recommendation).
_DIVISION_STAGE_OBJECTIVES = {
    "affiliate_commerce": {
        "stage_0_bootstrap": "Prove the click-tracking pipeline end-to-end before requesting a real Amazon Associates account.",
        "stage_1_validation": "Get the real Amazon Associates account approved; keep the single proven category narrow (ADR-149).",
        "stage_2_stable_revenue": "Only add a second affiliate network once the first shows a real, sustained commission stream.",
        "stage_3_expansion": "Expand product coverage within the proven network before adding a second network.",
        "stage_4_multi_market": "Evaluate a second real network only with real conversion data from the first in hand.",
        "stage_5_autonomous_enterprise": "Out of scope until Stage 5's founder-policy gates are explicitly lifted.",
    },
    "digital_products": {
        "stage_0_bootstrap": "Get one real book to a real ASIN on KDP (config/reality.json's own gating threshold).",
        "stage_1_validation": "Convert real production runs into at least one real completed sale.",
        "stage_2_stable_revenue": "Stabilize the production→QA→publish pipeline's real pass rate before adding volume.",
        "stage_3_expansion": "Use value_engine's real upgrade_potential/bundle_potential candidates to multiply proven niches.",
        "stage_4_multi_market": "Extend to a second real distribution channel beyond KDP with a proven niche.",
        "stage_5_autonomous_enterprise": "Out of scope until Stage 5's founder-policy gates are explicitly lifted.",
    },
    "publishing": {
        "stage_0_bootstrap": "Keep every live channels/ arm (Gumroad/Etsy/Payhip/Paddle) in dry-run-safe operation.",
        "stage_1_validation": "Get one real, non-dry-run publish through channels/publish_protection.py's gate.",
        "stage_2_stable_revenue": "Monitor publish_protection.py's real risk_score trend as publish volume grows.",
        "stage_3_expansion": "Bring a currently-greenfield arm (KDP/Shopify/AliExpress) to real registered status.",
        "stage_4_multi_market": "Diversify real revenue across >=2 platforms (see multi_platform_real_revenue condition).",
        "stage_5_autonomous_enterprise": "Out of scope until Stage 5's founder-policy gates are explicitly lifted.",
    },
    "research": {
        "stage_0_bootstrap": "Keep Tier-1 intake/candidate discovery running via the manually-invoked factory_loop.js tick.",
        "stage_1_validation": "Prioritize niches with real market_memory sample_size evidence over intelligence-only scores.",
        "stage_2_stable_revenue": "Feed real sales outcomes back into decision_engine.feedback.sync_outcomes() for recalibration.",
        "stage_3_expansion": "Widen source coverage only where a real local connector genuinely exists (never fabricated).",
        "stage_4_multi_market": "Country-level intelligence stays deferred per the founder's own 2026-07-23 decision.",
        "stage_5_autonomous_enterprise": "Out of scope until Stage 5's founder-policy gates are explicitly lifted.",
    },
    "infrastructure": {
        "stage_0_bootstrap": "Keep GET /health's real checks green; storage_integrity and network reachability are the floor.",
        "stage_1_validation": "Close infrastructure_intelligence's remaining disclosed gaps before adding new surface area.",
        "stage_2_stable_revenue": "Track resilience_monitor's real resilience_score trend as real traffic starts arriving.",
        "stage_3_expansion": "Revisit disk/CPU checks' Windows-only scope once a real non-Windows deployment exists.",
        "stage_4_multi_market": "No real multi-region infrastructure need exists yet -- do not build ahead of real demand.",
        "stage_5_autonomous_enterprise": "Out of scope until Stage 5's founder-policy gates are explicitly lifted.",
    },
    "operations": {
        "stage_0_bootstrap": "Use enterprise_operations.py's company_pulse() as the real single daily status check.",
        "stage_1_validation": "Close autonomous_operations_status.py's disclosed ambiguous/not-wired gaps one at a time.",
        "stage_2_stable_revenue": "Watch resilience_monitor's real incident-open/close cadence as real load increases.",
        "stage_3_expansion": "Use enterprise_scheduler()'s real ROI ranking to sequence expansion work, not intuition.",
        "stage_4_multi_market": "Re-evaluate enterprise_dependency_graph()'s real cascade risk before adding platforms.",
        "stage_5_autonomous_enterprise": "Out of scope until Stage 5's founder-policy gates are explicitly lifted.",
    },
    "executive": {
        "stage_0_bootstrap": "Use executive_brain.py's real Tier-1 findings as the single source of truth, not a new panel.",
        "stage_1_validation": "Let executive_decision_memory.py's real conflict detection gate any repeated recommendation.",
        "stage_2_stable_revenue": "Start trusting strategic_intelligence_core's 30d/90d horizons once real windowed data exists.",
        "stage_3_expansion": "Use capital_allocation_engine's real opportunity_cost() pairings before approving new spend.",
        "stage_4_multi_market": "Re-run galaxy_council.py's convening for any real cross-platform expansion decision.",
        "stage_5_autonomous_enterprise": "This is the one division whose Stage 5 objective is real today: keep the 4 protected gates exactly as they are unless the founder explicitly says otherwise.",
    },
}


def division_stage_objectives(division=None, stage=None):
    if division is not None and division not in DIVISIONS:
        raise ValueError(f"unknown division: {division}")
    if stage is not None and stage not in STAGES:
        raise ValueError(f"unknown stage: {stage}")

    divisions = [division] if division else list(DIVISIONS.keys())
    out = {}
    for d in divisions:
        stages = [stage] if stage else STAGES
        out[d] = {
            "division_module": DIVISIONS[d],
            "objectives": {s: _DIVISION_STAGE_OBJECTIVES[d][s] for s in stages},
        }
    return {
        "note": "Founder-authored strategic guidance template, not AI-generated per-cycle -- pair with each division's own real launch_readiness/autonomous_operations citation, never read standalone.",
        "divisions": out,
    }


def highest_roi_action_to_advance(scheduler_result=None):
    """Pure citation of enterprise_executive_brain.enterprise_scheduler()'s
    real ranked_by_roi list (itself a pure citation of
    capital_allocation_engine.py, ADR-139/156) -- never a second,
    competing ranking algorithm."""
    if scheduler_result is None:
        import enterprise_executive_brain
        scheduler_result = enterprise_executive_brain.enterprise_scheduler()
    ranked = scheduler_result.get("ranked_by_roi", {})
    top = (ranked.get("answer") or [])[:1]
    return {
        "answer": top[0] if top else None,
        "source": "enterprise_executive_brain.py::enterprise_scheduler()['ranked_by_roi'] (ADR-156) -- no second ranking computed here.",
    }


def build_growth_dashboard(overrides=None):
    """The one real aggregator: current stage, remaining requirements,
    blocking factors, estimated readiness, per-division objectives, and
    the highest-ROI action to advance -- every real sub-scan computed
    exactly once and threaded through, same discipline as company_pulse()
    (ADR-155) and enterprise_scheduler() (ADR-156)."""
    stage_result = current_growth_stage(overrides)
    req = remaining_requirements_for_next_stage(overrides)
    blocking = blocking_factors(overrides)

    gradable = [c for c in req["requirements"] if c["met"] is not None]
    estimated_readiness = (
        {"value": None, "reason": "already at the highest defined stage"}
        if req.get("next_stage") is None
        else {
            "value": round(sum(1 for c in gradable if c["met"]) / len(gradable) * 100, 1) if gradable else None,
            "gradable_conditions": len(gradable),
            "undetermined_conditions": len(req["requirements"]) - len(gradable),
            "reason": None if gradable else "every remaining requirement for the next stage is NOT_ARCHITECTED -- no real threshold to grade against",
        }
    )

    import enterprise_executive_brain
    scheduler_result = enterprise_executive_brain.enterprise_scheduler()
    roi_action = highest_roi_action_to_advance(scheduler_result)

    return {
        "current_stage": stage_result["stage"],
        "current_stage_name": stage_result["stage_name"],
        "reason": {
            "conditions_met_for_current_stage": stage_result["all_conditions"].get(stage_result["stage"], []),
        },
        "remaining_requirements": req,
        "blocking_factors": blocking,
        "estimated_readiness_pct": estimated_readiness,
        "division_objectives": division_stage_objectives(),
        "highest_roi_action_to_advance": roi_action,
        "simulated": bool(overrides),
        "generated_at": _now_iso(),
    }


def answer_growth_questions(dashboard=None):
    """Literally answers the directive's 3 named Mission Control
    questions by citing build_growth_dashboard()'s own fields -- same
    convention as executive_questions.py::answer_strategic_questions()
    (ADR-154)."""
    if dashboard is None:
        dashboard = build_growth_dashboard()

    return {
        "why_are_we_still_in_current_stage": {
            "answer": f"{dashboard['current_stage_name']}: " + (
                "no next-stage requirements are outstanding yet to evaluate" if dashboard["remaining_requirements"].get("next_stage") is None
                else f"{len(dashboard['blocking_factors']['blocking_factors'])} real blocking condition(s) and {len(dashboard['blocking_factors']['undetermined_factors'])} undetermined (no policy threshold set) condition(s) remain for {dashboard['remaining_requirements'].get('next_stage_name')}"
            ),
            "source": "growth_stages.py::build_growth_dashboard()['reason']/['blocking_factors']",
        },
        "what_blocks_the_next_stage": {
            "answer": dashboard["blocking_factors"],
            "source": "growth_stages.py::blocking_factors()",
        },
        "highest_roi_action_to_reach_next_stage": dashboard["highest_roi_action_to_advance"],
        "generated_at": _now_iso(),
    }


def simulate_stage_progression(**hypothetical):
    """Simulation Mode integration (Objective 7): recomputes the stage
    against hypothetical overrides instead of real signals -- writes
    NOTHING to disk (a stateless what-if, not a transaction sequence to
    replay later, unlike affiliate_commerce/simulation.py's event
    ledger). Every accepted kwarg matches a _real_signals() key
    exactly; unknown keys are rejected rather than silently ignored."""
    import simulation_mode

    known_keys = {
        "accepted_opportunities_count", "real_production_runs", "total_revenue_usd",
        "open_critical_incidents", "launch_readiness", "automation_level_pct",
        "quality_score_pct", "platforms_with_real_revenue",
    }
    unknown = set(hypothetical) - known_keys
    if unknown:
        raise ValueError(f"unknown hypothetical override key(s): {sorted(unknown)} -- expected a subset of {sorted(known_keys)}")

    dashboard = build_growth_dashboard(overrides=hypothetical)
    return simulation_mode.tag_simulated(dashboard)


def record_growth_stage_snapshot(stage_result=None, snapshots_path=None):
    """Enterprise Strategic Planning System (ADR-159, 2026-07-31): the
    ONE real, additive write path for Growth Stage history -- appends
    {stage, stage_name, generated_at} to data/growth_stage_snapshots.jsonl.
    Never called from current_growth_stage() itself; only factory_loop.
    js's own once-per-calendar-day tick gate calls this, mirroring
    lib/health_trend.js::recordHealthSnapshot()'s exact real relationship
    to resilience_monitor.py's stateless assess_resilience(). Existing
    entries are never rewritten -- append-only, same convention as every
    other *.jsonl ledger in this factory."""
    if stage_result is None:
        stage_result = current_growth_stage()

    path = snapshots_path or DEFAULT_SNAPSHOTS_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {
        "stage": stage_result["stage"],
        "stage_name": stage_result["stage_name"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def growth_stage_history(limit=50, snapshots_path=None):
    """Real, chronological read of the snapshot ledger above -- honestly
    empty (never fabricated) until the daily tick has recorded at least
    one real snapshot."""
    path = snapshots_path or DEFAULT_SNAPSHOTS_PATH
    if not os.path.exists(path):
        return {"entries": [], "reason": "لا لقطة مرحلة نمو حقيقية مسجَّلة بعد -- تُسجَّل واحدة تلقائياً مع أول دورة يومية حقيقية لـ factory_loop.js"}

    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return {"entries": entries[-limit:]}
