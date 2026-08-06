#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enterprise Capital Allocation Engine (ADR-165, 2026-07-31).

The founder's directive labeled itself "ADR-163" -- already allocated
to Enterprise Evidence Engine (committed `dac990a`). This is the real
next number, ADR-165, same renumbering convention CONSTITUTION.md's
own amendment history and ADR-164 already established.

Extends -- never duplicates -- the real, already-live 14-dimension
Investment Score (capital_allocation_engine.py::investment_score(),
ADR-139) and its real dashboard (build_capital_allocation_dashboard()).
12 of this directive's 15 named dimensions are already directly
covered by that real function; 2 more (Expected ROI, Scalability) have
a real signal that was simply never cited yet; only 3 are genuinely
new (Market maturity, Legal risk, Operational risk). This module adds
those 5, plus the genuinely new "manages every strategic resource"
ask (10 named resources, most of which have no real tracking anywhere
in this factory -- honestly disclosed, never invented) and a real
"Projects Overfunded" heuristic (no prior real analog).

INSUFFICIENT EVIDENCE is this directive's own literal required string
for "cannot honestly rank" -- used here specifically, alongside (not
replacing) truth_first.CANONICAL_VOCABULARY's general 9 terms.
"""

from datetime import datetime, timezone

INSUFFICIENT_EVIDENCE = "INSUFFICIENT EVIDENCE"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def extended_investment_score(niche, base_score=None, decisions_path=None, board_path=None,
                               alerts_path=None, reopen_log_path=None, evidence_path=None):
    """The real 14-dim Investment Score (capital_allocation_engine.py,
    ADR-139), reused verbatim via injection (never recomputed), plus 5
    real, disclosed additions: 2 already-real-but-uncited (expected_roi,
    scalability, both already inside value_engine.compute_value_profile()),
    3 genuinely new (market_maturity, legal_risk, operational_risk)."""
    import capital_allocation_engine as cap
    import value_engine
    import executive_quality_gate as eqg
    import resilience_monitor
    import global_opportunity_exchange as gox

    if base_score is None:
        base_score = cap.investment_score(
            niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        )

    profile = value_engine.compute_value_profile(
        niche, decisions_path=decisions_path, board_path=board_path,
        alerts_path=alerts_path, reopen_log_path=reopen_log_path, evidence_path=evidence_path,
    ) or {}
    board = profile.get("board_summary") or {}
    dims = profile.get("dimensions") or {}

    legal = eqg.check_legal_compliance_risk(niche)
    resilience = resilience_monitor.assess_resilience()
    market = gox.market_health()

    return {
        **base_score,
        "expected_roi": {
            "answer": board.get("expected_roi"),
            "source": "value_engine.py::compute_value_profile()['board_summary']['expected_roi'] -- real, already computed, not previously cited by investment_score().",
        },
        "scalability": {
            "answer": dims.get("scalability"),
            "source": "value_engine.py::compute_value_profile()['dimensions']['scalability'] (from global_scalability) -- real, already computed, not previously cited by investment_score().",
        },
        "market_maturity": {
            "value": INSUFFICIENT_EVIDENCE,
            "reason": "No real per-niche product-lifecycle-maturity signal exists anywhere in this factory today.",
            "company_wide_context": {"answer": market, "source": "global_opportunity_exchange.py::market_health() -- real, but company-wide marketplace-saturation, not per-niche maturity; cited for context only, never substituted as a per-niche answer."},
        },
        "legal_risk": {
            "answer": legal,
            "source": "executive_quality_gate.py::check_legal_compliance_risk(niche) (ADR-102) -- real, already-live per-niche check, not previously cited by capital allocation.",
        },
        "operational_risk": {
            "value": resilience.get("active_alerts") if resilience.get("active_alerts") else INSUFFICIENT_EVIDENCE,
            "reason": None if resilience.get("active_alerts") else "No real active resilience alert exists this cycle.",
            "source": "resilience_monitor.py::assess_resilience()['active_alerts'] -- real, but company-wide, not reliably niche-keyed (same honest limitation executive_questions.py::_which_division_is_slowing() already discloses for a similar signal).",
        },
        "generated_at": _now_iso(),
    }


# Real, disclosed citation table for the directive's 10 named
# strategic resources -- confirmed by direct search which have a real
# signal anywhere in this factory and which genuinely do not.
def resource_allocation_map(publish_protection_state_path=None, ai_cost_log_path=None):
    import founder_console
    from ai_capability import registry as ai_registry
    from channels import publish_protection
    import autonomous_operations_status as aos
    from channels import ledger as sales_ledger

    founder_queue = founder_console.build_founder_queue_partial()
    providers = ai_registry.list_providers(cost_log_path=ai_cost_log_path)
    publish_status = publish_protection.list_publish_protection_status(state_path=publish_protection_state_path)
    ops_summary = aos.autonomous_operations_summary()
    revenue = sales_ledger.revenue_trend()

    return {
        "founder_attention": {"answer": founder_queue, "source": "founder_console.py::build_founder_queue_partial() -- real pending-decision queue."},
        "human_review_time": {"answer": founder_queue.get("pending_decisions") if isinstance(founder_queue, dict) else None, "source": "Same real founder_console.py queue -- the real proxy for human review load."},
        "ai_compute": {"answer": providers, "source": "ai_capability/registry.py::list_providers() -- real per-provider call/cost stats."},
        "automation_capacity": {"answer": ops_summary, "source": "autonomous_operations_status.py::autonomous_operations_summary() -- real automatic/human-gated activity counts."},
        "publishing_capacity": {"answer": publish_status, "source": "channels/publish_protection.py::list_publish_protection_status() -- real per-arm daily/hourly caps and usage."},
        "cash": {"answer": revenue, "source": "channels/ledger.py::revenue_trend() -- real sales ledger totals."},
        "infrastructure": {"value": INSUFFICIENT_EVIDENCE, "reason": "infrastructure_bridge.py::get_infrastructure_status() is a real, live check but expensive/network-dependent -- not called from this passive citation map by default; see the executive-infrastructure-status panel for the real live signal."},
        "development_time": {"value": INSUFFICIENT_EVIDENCE, "reason": "No real per-project development-time tracking exists anywhere in this factory (confirmed by direct search) -- distinct from real AI-call-cost tracking, which does exist above."},
        "research_capacity": {"value": INSUFFICIENT_EVIDENCE, "reason": "No real research-hours/capacity tracking exists anywhere in this factory."},
        "marketing_effort": {"value": INSUFFICIENT_EVIDENCE, "reason": "No real marketing-spend/effort tracking exists anywhere in this factory -- CLAUDE.md's own Path 5 (VIP business services) and marketing content generation are named but unbuilt/unmeasured."},
        "generated_at": _now_iso(),
    }


def capacity_utilization(resource_map=None):
    """Real aggregator over resource_allocation_map()'s own real
    citations -- never a fabricated single utilization percentage."""
    if resource_map is None:
        resource_map = resource_allocation_map()

    real_resources = {k: v for k, v in resource_map.items() if k != "generated_at" and v.get("value") != INSUFFICIENT_EVIDENCE}
    insufficient = [k for k, v in resource_map.items() if k != "generated_at" and v.get("value") == INSUFFICIENT_EVIDENCE]

    return {
        "resources_with_real_signal": list(real_resources.keys()),
        "resources_with_insufficient_evidence": insufficient,
        "note": f"{len(real_resources)}/{len(real_resources) + len(insufficient)} named strategic resources have a real, citable signal today -- never a single fabricated utilization percentage blending all 10.",
        "generated_at": _now_iso(),
    }


def projects_overfunded(portfolio=None, log_path=None, top_n=5):
    """Real, disclosed heuristic -- no prior real analog in this
    factory. Real production-run-count per niche (books/_generation_
    log.jsonl) cross-referenced against real priority-score rank
    (value_engine.build_value_engine_report()) -- high real spend +
    low real rank is flagged as overfunded, cited transparently."""
    import json
    import os
    import value_engine

    if portfolio is None:
        portfolio = value_engine.build_value_engine_report()
    profiles = portfolio.get("profiles", [])
    if not profiles:
        return {"value": INSUFFICIENT_EVIDENCE, "reason": "No real ACCEPTED opportunities exist to rank."}

    path = log_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "books", "_generation_log.jsonl")
    run_counts = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                niche = entry.get("niche") or entry.get("title")
                if niche:
                    run_counts[niche] = run_counts.get(niche, 0) + 1

    if not run_counts:
        return {"value": INSUFFICIENT_EVIDENCE, "reason": "No real production runs logged in books/_generation_log.jsonl yet."}

    ranked_niches = [p["niche"] for p in profiles]
    scored = []
    for niche, runs in run_counts.items():
        rank = ranked_niches.index(niche) + 1 if niche in ranked_niches else None
        if rank is None:
            continue
        scored.append({"niche": niche, "real_production_runs": runs, "real_priority_rank": rank, "of_n_ranked": len(ranked_niches)})

    scored.sort(key=lambda s: (s["real_priority_rank"], -s["real_production_runs"]), reverse=True)
    return {
        "answer": scored[:top_n],
        "method": "Real production-run-count (books/_generation_log.jsonl) vs. real priority-score rank (value_engine.py) -- high real spend + low real rank flagged first, a real disclosed proxy, never a fabricated verdict.",
        "generated_at": _now_iso(),
    }


def build_enterprise_capital_allocation_dashboard(decisions_path=None, board_path=None, alerts_path=None,
                                                   reopen_log_path=None, evidence_path=None, timeline_path=None,
                                                   outcomes_path=None):
    """The one real aggregator -- every expensive real sub-scan computed
    exactly once and threaded through via injection, same discipline
    this session established for company_pulse()/enterprise_scheduler()."""
    import capital_allocation_engine as cap
    import value_engine

    base_dashboard = cap.build_capital_allocation_dashboard(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    portfolio = value_engine.build_value_engine_report(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    resource_map = resource_allocation_map()

    return {
        "top_investments": base_dashboard["top_roi_initiatives"],
        "projects_starved_of_resources": base_dashboard["projects_consuming_resources_without_results"],
        "projects_overfunded": projects_overfunded(portfolio=portfolio),
        "expected_long_term_roi": base_dashboard["expected_portfolio_return"],
        "resource_allocation": resource_map,
        "company_capacity_utilization": capacity_utilization(resource_map=resource_map),
        "opportunity_cost_summary": base_dashboard["opportunity_cost_summary"],
        "portfolio_size": base_dashboard["portfolio_size"],
        "generated_at": _now_iso(),
    }


# -- Capital Allocation Engine: Investment Decisions and Portfolio Balance (ADR-176, 2026-08-05) --
# Founder's "Capital Allocation Engine" directive -- the same name as
# ADR-139/ADR-165, both already real. Research found 17 of 20 named
# dimensions already covered (14 from capital_allocation_engine.py +
# 3 from this module's own extended_investment_score()); only 3
# genuinely missing: Expected Monthly/Annual Revenue and Time to First
# Sale as FORWARD projections (the real "expected_revenue" field this
# factory has is retrospective -- real closed-sale revenue TO DATE,
# never a forecast, per extended_investment_score()'s own docstring --
# multiplying it by 12 would be a fabricated projection dressed as real
# data); Customer Trust Impact (no prior citation); Compounding Value
# (no prior citation). The directive's own 4-value decision output
# (INVEST NOW/BUILD LATER/EXPERIMENT/REJECT) is a real relabeling of
# scheduler.py's already-real 5 buckets, never a second decision engine.

NOT_MEASURABLE = "NOT_MEASURABLE"

DECISION_INVEST_NOW = "INVEST NOW"
DECISION_BUILD_LATER = "BUILD LATER"
DECISION_EXPERIMENT = "EXPERIMENT"
DECISION_REJECT = "REJECT"


def _forward_looking_dimensions(niche):
    """Expected Monthly Revenue / Expected Annual Revenue / Time to
    First Sale -- all 3 honestly NOT_MEASURABLE as forward projections.
    This factory's real 'expected_revenue' field (capital_allocation_
    engine.py) is retrospective (real closed-sale revenue to date,
    currently $0 for every niche) -- citing it as a forward monthly/
    annual figure, or deriving one by multiplying by 12, would be a
    fabricated projection, forbidden by this factory's own Truth First
    Constitution (ADR-160)."""
    return {
        "expected_monthly_revenue": {"value": NOT_MEASURABLE, "reason": "No real forward-revenue-forecasting signal exists anywhere in this factory -- the real expected_revenue field is retrospective (real closed-sale revenue to date), never a forecast."},
        "expected_annual_revenue": {"value": NOT_MEASURABLE, "reason": "Same real limitation -- deriving this by multiplying a retrospective figure by 12 would be a fabricated projection, not a real one."},
        "time_to_first_sale": {"value": NOT_MEASURABLE, "reason": "No real historical per-niche time-to-first-sale data exists anywhere in this factory (same disclosed-gap class as execution_status.py's own estimated_completion: Unknown)."},
    }


def customer_trust_impact(text=None):
    """Real citation of brand_dna.py's Trust Framework (ADR-170) --
    never a second trust-scoring mechanism. Honestly Unknown without
    real product-facing text to check."""
    if not text:
        return {"value": "UNKNOWN", "reason": "no real product-facing text supplied for this check", "source": "brand_dna.py::validate_customer_facing_text() (ADR-170)"}
    import brand_dna
    result = brand_dna.validate_customer_facing_text(text)
    return {"value": "PASS" if result["passed"] else "FAIL", "failed_checks": result["failed_checks"], "source": "brand_dna.py::validate_customer_facing_text() (ADR-170)"}


def compounding_value(extended_score=None, niche=None):
    """Real, disclosed combination of 2 already-real dimensions --
    knowledge_reuse (does this asset make future work cheaper) and
    long_term_asset_value (does it keep producing value after launch).
    Never a new, independent scoring computation -- 'compounding' is a
    real property of these 2 existing signals together, not a 3rd one."""
    if extended_score is None:
        if not niche:
            return {"value": NOT_MEASURABLE, "reason": "no real niche or extended_score supplied"}
        extended_score = extended_investment_score(niche)
    knowledge_reuse = extended_score.get("knowledge_reuse", {}).get("value")
    long_term = extended_score.get("long_term_asset_value", {}).get("value")
    if not isinstance(knowledge_reuse, (int, float)) or not isinstance(long_term, (int, float)):
        return {"value": NOT_MEASURABLE, "reason": "knowledge_reuse or long_term_asset_value has no real numeric value for this niche", "source": "extended_investment_score()'s own real dimensions"}
    return {"value": round((knowledge_reuse + long_term) / 2, 1), "source": "avg(knowledge_reuse, long_term_asset_value) -- a disclosed, real combination of 2 already-real dimensions, never a 3rd independent computation"}


def capital_decision(niche, scheduler_result=None, decision_record=None):
    """The directive's own required output: one of INVEST NOW/BUILD
    LATER/EXPERIMENT/REJECT + written reasoning. A real relabeling of
    scheduler.py::decide_next_actions()'s already-real 5 buckets --
    run_now/accelerate -> INVEST NOW, cancel/stop -> REJECT. EXPERIMENT
    is the one genuinely new distinction: within the real 'wait' bucket,
    a niche whose own real decision-confidence level is low/medium is
    tagged EXPERIMENT (worth a small, cheap real test) rather than
    BUILD LATER (already confident, just queued) -- a real, disclosed
    heuristic over the real confidence field decision_engine already
    computes, never a fabricated distinction."""
    import scheduler
    from decision_engine import store

    if scheduler_result is None:
        scheduler_result = scheduler.decide_next_actions()
    buckets = scheduler_result["buckets"]

    for entry in buckets.get("cancel", []) + buckets.get("stop", []):
        if entry["niche"] == niche:
            return {"decision": DECISION_REJECT, "reasoning": entry["reason"], "source": "scheduler.py::decide_next_actions()"}
    for entry in buckets.get("run_now", []) + buckets.get("accelerate", []):
        if entry["niche"] == niche:
            return {"decision": DECISION_INVEST_NOW, "reasoning": entry["reason"], "source": "scheduler.py::decide_next_actions()"}
    for entry in buckets.get("wait", []):
        if entry["niche"] == niche:
            if decision_record is None:
                records = store.find_decisions_by_niche(niche)
                decision_record = records[-1] if records else None
            confidence_level = ((decision_record or {}).get("evaluation_snapshot") or {}).get("confidence", {}).get("level")
            if confidence_level in ("منخفضة", "متوسطة", "low", "medium"):
                return {"decision": DECISION_EXPERIMENT, "reasoning": f"{entry['reason']} -- real confidence level: {confidence_level} (real, disclosed threshold, not a new evaluation)", "source": "scheduler.py + decision_engine's real confidence field"}
            return {"decision": DECISION_BUILD_LATER, "reasoning": entry["reason"], "source": "scheduler.py::decide_next_actions()"}
    return {"decision": None, "reasoning": f"{niche!r} not found in any real scheduler bucket -- likely not a real ACCEPTED opportunity today", "source": "scheduler.py::decide_next_actions()"}


def portfolio_balance(portfolio=None, decisions_path=None):
    """Portfolio thinking, not single-product optimization: real
    aggregation by ladder category -- profit_oracle.LADDER_RANKS
    already encodes recurring-income-vs-one-time character (ai_saas/
    b2b_systems = recurring, kdp_books/reusable_assets = closer to
    one-time), never an invented taxonomy."""
    from decision_engine import ranking

    recurring_ladders = {"ai_saas", "b2b_systems", "automation_tools"}
    one_time_ladders = {"kdp_books", "reusable_assets", "educational"}

    counts = {"recurring_income": 0, "one_time_sales": 0, "unclassified": 0}
    accepted = [d for d in ranking.rank_all(path=decisions_path) if d.get("status") == "ACCEPTED"]
    for d in accepted:
        ladder = d.get("ladder")
        if ladder in recurring_ladders:
            counts["recurring_income"] += 1
        elif ladder in one_time_ladders:
            counts["one_time_sales"] += 1
        else:
            counts["unclassified"] += 1

    return {
        "real_accepted_portfolio_size": len(accepted),
        "by_character": counts,
        "high_risk_innovations": NOT_MEASURABLE,
        "stable_cash_flow_products": NOT_MEASURABLE,
        "long_term_strategic_assets": NOT_MEASURABLE,
        "note": "High-risk-innovation/stable-cash-flow/long-term-strategic need a real per-niche risk-maturity signal this factory doesn't compute yet -- honestly NOT_MEASURABLE rather than guessed from the same 2 ladder-derived buckets above.",
        "source": "profit_oracle.LADDER_RANKS' real recurring-vs-one-time character + decision_engine.ranking.rank_all()",
        "generated_at": _now_iso(),
    }


def resource_optimization_recommendation():
    """'Where should the next hour/day/week/month be invested' -- real
    citation of strategic_planning.py's real rolling_roadmap() (ADR-159),
    never a new time-bucketing mechanism. 'Next hour' has no real signal
    finer than 'Today' anywhere in this factory -- both cite the same
    real Today bucket, disclosed rather than invented."""
    import strategic_planning
    roadmap = strategic_planning.rolling_roadmap()
    today = roadmap.get("today")
    return {
        "next_hour": {"value": today, "note": "No real signal exists at finer granularity than Today -- cites the same real bucket."},
        "next_day": today,
        "next_week": roadmap.get("this_week"),
        "next_month": roadmap.get("this_month"),
        "source": "strategic_planning.py::rolling_roadmap() (ADR-159)",
        "generated_at": _now_iso(),
    }


def self_improvement_sources():
    """Pure citation -- never a 4th competing learning loop (same
    discipline as evolution_engine.py's own function of this name,
    ADR-173)."""
    return {
        "successful_and_failed_launches": "decision_engine/learning.py::recalibration_report() -- real per-dimension historical-evidence statistics, deliberately never auto-applied.",
        "outcome_tracking": "evolution_queue.py's real measure_outcome() -- IMPROVED/DEGRADED/NO_CHANGE/NOT_ENOUGH_DATA.",
        "revenue_concentration": "global_opportunity_exchange.py's real concentration_risk_report() (platform/product_family/country/ai_provider vs named thresholds).",
        "market_shifts": "competitor_discovery.py's real cached database + market_hunter.py's real live HN/GitHub/Amazon/Etsy/Gumroad ingestion.",
        "note": "All 4 feed real, already-existing signal sources -- never a second, parallel learning loop.",
    }


def build_capital_decisions_report(limit=20, decisions_path=None):
    """The one real aggregator for this round -- computes scheduler.py's
    real buckets exactly once, produces a real decision + reasoning for
    every real niche found in them, plus portfolio balance and resource
    optimization, all computed exactly once."""
    import scheduler

    scheduler_result = scheduler.decide_next_actions()
    buckets = scheduler_result["buckets"]
    all_niches = []
    for bucket_name in ("run_now", "accelerate", "wait", "cancel", "stop"):
        all_niches.extend(e["niche"] for e in buckets.get(bucket_name, []))

    decisions = [
        {"niche": n, **capital_decision(n, scheduler_result=scheduler_result)}
        for n in all_niches[:limit]
    ]

    return {
        "decisions": decisions,
        "portfolio_balance": portfolio_balance(decisions_path=decisions_path),
        "resource_optimization": resource_optimization_recommendation(),
        "self_improvement_sources": self_improvement_sources(),
        "forward_looking_dimensions_note": "Expected Monthly/Annual Revenue and Time to First Sale are honestly NOT_MEASURABLE for every real niche -- see _forward_looking_dimensions() for the real reason.",
        "generated_at": _now_iso(),
    }
