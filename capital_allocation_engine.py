#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capital Allocation Engine (2026-07-29) — "CAPITAL ALLOCATION ENGINE"
directive: every initiative gets a continuously updated 14-dimension
Investment Score, dynamic resource recommendations, real opportunity-
cost detection, and protection against shiny-object syndrome/sunk-cost
fallacy/founder bias.

A research audit before writing any code found 7 of the 14 named
dimensions directly duplicate strategic_intelligence_core.py::
strategic_score()'s own 11 named dimensions, built the immediately
preceding round. Building a second, parallel citation function for
those 7 would duplicate architecture -- `investment_score()` below
delegates to strategic_score() verbatim for those 7 and adds real
citations only for the genuinely new 7 (Expected Revenue, Customer
Impact, Market Defensibility, Engineering Cost, Maintenance Cost,
Knowledge Reuse, Brand Value), sourced from value_engine.compute_
value_profile()'s own real dimensions/board_summary fields.

Sunk-cost-fallacy protection ("never continue investing simply because
past work exists") is a real, disclosed STRUCTURAL property, not new
code: neither profit_oracle.opportunity_score() nor value_engine.
compute_value_profile() accept any cumulative-past-spend parameter
anywhere in their real signatures -- a decision here is architecturally
incapable of being anchored to money already spent, only to future
evidence. Every function in this module is read-only/recommend-only;
Constitution-first and no-autonomous-high-risk-decisions are already
real everywhere an irreversible action exists in this factory.
"""

from datetime import datetime, timezone

_INVESTMENT_SCORE_SOURCES = {
    "recurring_revenue_potential": "strategic_intelligence_core.strategic_score()'s recurring_revenue dimension",
    "competition_level": "strategic_intelligence_core.strategic_score()'s competition dimension",
    "automation_potential": "strategic_intelligence_core.strategic_score()'s automation dimension",
    "risk": "strategic_intelligence_core.strategic_score()'s risk dimension",
    "strategic_importance": "strategic_intelligence_core.strategic_score()'s strategic_value dimension",
    "long_term_asset_value": "strategic_intelligence_core.strategic_score()'s long_term_value dimension",
    "execution_complexity": "strategic_intelligence_core.strategic_score()'s difficulty dimension",
    "expected_revenue": "value_engine.compute_value_profile()'s board_summary.estimated_lifetime_value (real closed-sale revenue to date, never a forecast)",
    "customer_impact": "value_engine.compute_value_profile()'s dimensions.expected_customer_value",
    "market_defensibility": "value_engine.compute_value_profile()'s dimensions.defensibility",
    "engineering_cost": "value_engine.compute_value_profile()'s board_summary.estimated_build_cost (revenue_pipeline.plan.estimate_production_cost())",
    "maintenance_cost": "value_engine.compute_value_profile()'s board_summary.estimated_maintenance_cost",
    "knowledge_reuse": "value_engine.compute_value_profile()'s dimensions.knowledge_accumulation/synergy_with_existing_products/bundle_potential",
    "brand_value": "value_engine.compute_value_profile()'s dimensions.brand_building_impact",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _knowledge_reuse_citation(dims):
    """Real synthesis of 3 already-real dimensions -- never a new score.
    knowledge_accumulation's own real `level` is the headline value;
    synergy_with_existing_products/bundle_potential are folded into the
    reason as real supporting citations, each only when itself real
    (not honestly Unknown)."""
    source = _INVESTMENT_SCORE_SOURCES["knowledge_reuse"]
    knowledge = dims.get("knowledge_accumulation")
    if not isinstance(knowledge, dict) or knowledge.get("answer") == "Unknown":
        reason = (knowledge or {}).get("reason", "لا بيانات تراكم معرفة حقيقية بعد لهذا القرار")
        return {"value": "Unknown", "source": source, "reason": reason}

    reason_parts = [knowledge.get("note")]
    synergy = dims.get("synergy_with_existing_products")
    if isinstance(synergy, dict) and synergy.get("answer") != "Unknown":
        reason_parts.append(f"تآزر: {synergy.get('note')}")
    bundle = dims.get("bundle_potential")
    if isinstance(bundle, dict) and bundle.get("answer") != "Unknown":
        reason_parts.append(f"حزمة: {bundle.get('note')}")

    return {"value": knowledge.get("level"), "source": source, "reason": "؛ ".join(p for p in reason_parts if p)}


def _engineering_cost_citation(board):
    """board_summary.estimated_build_cost has its own real shape
    ({"maturity": "REAL"/"DISCOVERY", ...}) distinct from every other
    dimension's shape -- a dedicated citation, not force-fit onto a
    generic extractor."""
    source = _INVESTMENT_SCORE_SOURCES["engineering_cost"]
    build_cost = board.get("estimated_build_cost") or {}
    if build_cost.get("maturity") == "REAL":
        return {
            "value": build_cost.get("estimated_cost_usd"), "source": source,
            "reason": f"متوسط تكلفة إنتاج حقيقي عبر {build_cost.get('sample_size')} استدعاء Groq حقيقي مسجَّل",
        }
    return {"value": "Unknown", "source": source, "reason": build_cost.get("reason", "لا بيانات تكلفة إنتاج حقيقية بعد")}


def investment_score(niche, decisions_path=None, board_path=None, alerts_path=None,
                      reopen_log_path=None, evidence_path=None, inspections_log=None):
    """The directive's 14 named Investment Score dimensions -- 7 by
    direct delegation to strategic_score() (never recomputed), 7 by new
    real citation from value_engine.compute_value_profile(). Every
    dimension is `{value, source, reason}`, honestly `"Unknown"` wherever
    the underlying real source has no signal yet, exactly matching
    strategic_score()'s own citation discipline."""
    import strategic_intelligence_core as sic
    import value_engine

    strategic = sic.strategic_score(niche, decisions_path=decisions_path)
    profile = value_engine.compute_value_profile(
        niche, decisions_path=decisions_path, board_path=board_path,
        alerts_path=alerts_path, reopen_log_path=reopen_log_path, evidence_path=evidence_path,
    ) or {}
    dims = profile.get("dimensions") or {}
    board = profile.get("board_summary") or {}

    return {
        "niche": niche,
        # 7 dimensions delegated verbatim to strategic_score() -- never a second computation.
        "recurring_revenue_potential": strategic["recurring_revenue"],
        "competition_level": strategic["competition"],
        "automation_potential": strategic["automation"],
        "risk": strategic["risk"],
        "strategic_importance": strategic["strategic_value"],
        "long_term_asset_value": strategic["long_term_value"],
        "execution_complexity": strategic["difficulty"],
        # 7 genuinely new dimensions, cited from value_engine.compute_value_profile().
        "expected_revenue": sic._extract_signal(board.get("estimated_lifetime_value"), _INVESTMENT_SCORE_SOURCES["expected_revenue"]),
        "customer_impact": sic._extract_signal(dims.get("expected_customer_value"), _INVESTMENT_SCORE_SOURCES["customer_impact"]),
        "market_defensibility": sic._extract_signal(dims.get("defensibility"), _INVESTMENT_SCORE_SOURCES["market_defensibility"]),
        "engineering_cost": _engineering_cost_citation(board),
        "maintenance_cost": sic._extract_signal(board.get("estimated_maintenance_cost"), _INVESTMENT_SCORE_SOURCES["maintenance_cost"]),
        "knowledge_reuse": _knowledge_reuse_citation(dims),
        "brand_value": sic._extract_signal(dims.get("brand_building_impact"), _INVESTMENT_SCORE_SOURCES["brand_value"]),
        "generated_at": _now_iso(),
    }


def opportunity_cost(decisions_path=None, board_path=None, alerts_path=None, reopen_log_path=None,
                      evidence_path=None, timeline_path=None, outcomes_path=None,
                      portfolio=None, scheduling=None):
    """Real opportunity-cost pairing: for every real ACCEPTED opportunity
    scheduler.py's own real buckets have flagged as `wait`/`stop`/
    `cancel`, cites which real `run_now`/`accelerate` opportunities rank
    higher by the exact same real Priority Score order value_engine.
    build_value_engine_report() already computed -- "resources are
    effectively going to X instead of Y" as a real, evidence-based
    pairing, never invented.

    `portfolio`/`scheduling` (optional): lets build_capital_allocation_
    dashboard() below inject its own already-computed real portfolio/
    scheduling result instead of triggering a second, redundant
    ~10s+ full-portfolio scan -- the same real injection point
    scheduler.decide_next_actions()'s own `portfolio` param already
    established, and the same "never recompute" discipline strategic_
    intelligence_core.py::build_executive_brief() enforced last round.
    Omitting them (every standalone caller) computes both fresh here,
    exactly once each."""
    import value_engine
    import scheduler

    if portfolio is None:
        portfolio = value_engine.build_value_engine_report(
            decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
            timeline_path=timeline_path, outcomes_path=outcomes_path,
        )
    if scheduling is None:
        scheduling = scheduler.decide_next_actions(
            decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
            timeline_path=timeline_path, outcomes_path=outcomes_path,
            portfolio=portfolio,
        )
    buckets = scheduling["buckets"]

    rank_by_niche = {p["niche"]: i for i, p in enumerate(portfolio["profiles"])}
    ahead_niches = [m["niche"] for m in (buckets["run_now"] + buckets["accelerate"])]

    pairings = []
    for bucket_name in ("wait", "stop", "cancel"):
        for member in buckets[bucket_name]:
            niche = member["niche"]
            member_rank = rank_by_niche.get(niche)
            if member_rank is None:
                # e.g. a real REJECTED niche in `cancel` never had a real
                # ACCEPTED portfolio entry at all -- no real rank to
                # compare, so no real opportunity-cost claim is made.
                continue
            higher_priority = [n for n in ahead_niches if rank_by_niche.get(n, member_rank) < member_rank]
            if higher_priority:
                pairings.append({
                    "delayed_niche": niche, "delayed_bucket": bucket_name, "delayed_reason": member["reason"],
                    "higher_priority_niches": higher_priority,
                    "evidence": f"مرتبة حقيقية أدنى (Priority Score) من {len(higher_priority)} فرصة حقيقية قيد التشغيل/التسريع فعلاً",
                })

    return {"pairings": pairings, "portfolio_size": len(portfolio["profiles"]), "generated_at": _now_iso()}


def stuck_without_production(decisions_path=None, timeline_path=None, outcomes_path=None, now=None, stuck_after_days=7):
    """"Projects Consuming Resources Without Results": a real ACCEPTED
    decision with zero real production attempt ever logged
    (value_engine.classify_lifecycle_stage()'s own real `prototype`
    stage, citing production_evidence.record.build_evidence_record()
    verbatim) across a real, disclosed elapsed-time threshold since it
    was decided. Modeled on customer_pipeline.py's existing stuck-
    request pattern (stage-based staleness, cited in tool_intelligence/
    proposals.py) -- never a new judgment engine."""
    from decision_engine import ranking
    import value_engine

    now = now or datetime.now(timezone.utc)
    accepted = [d for d in ranking.rank_all(path=decisions_path) if d.get("status") == "ACCEPTED" and d.get("niche")]

    stuck = []
    for d in accepted:
        niche = d["niche"]
        lifecycle = value_engine.classify_lifecycle_stage(
            niche, decisions_path=decisions_path, timeline_path=timeline_path, outcomes_path=outcomes_path,
        )
        prototype = lifecycle["stages"]["prototype"]
        if prototype["reached"]:
            continue

        elapsed_days = None
        try:
            decided_dt = datetime.fromisoformat((d.get("decided_at") or "").replace("Z", "+00:00"))
            elapsed_days = (now - decided_dt).total_seconds() / 86400
        except (TypeError, ValueError):
            pass

        if elapsed_days is not None and elapsed_days >= stuck_after_days:
            stuck.append({
                "niche": niche, "decided_at": d.get("decided_at"), "elapsed_days": round(elapsed_days, 1),
                "evidence": prototype["evidence"],
            })

    return {
        "stuck_after_days_threshold": stuck_after_days,
        "total_accepted": len(accepted),
        "stuck": stuck,
        "generated_at": _now_iso(),
    }


def build_capital_allocation_dashboard(decisions_path=None, board_path=None, alerts_path=None,
                                        reopen_log_path=None, evidence_path=None, timeline_path=None,
                                        outcomes_path=None, stuck_after_days=7):
    """The one real aggregator this factory never had for capital
    allocation: Top ROI Initiatives, Projects Losing Value, Projects
    Consuming Resources Without Results, Resource Distribution, Expected
    Portfolio Return, and the real opportunity-cost pairings above.
    Every field cites an already-real function; nothing here is a
    second computation of another -- the real portfolio/scheduling scan
    is computed exactly ONCE and threaded into opportunity_cost() via
    its own injection point (see opportunity_cost()'s own docstring)."""
    import value_engine
    import scheduler
    import ceo_decision_center

    portfolio = value_engine.build_value_engine_report(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    scheduling = scheduler.decide_next_actions(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
        portfolio=portfolio,
    )
    opp_cost = opportunity_cost(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
        portfolio=portfolio, scheduling=scheduling,
    )
    stuck = stuck_without_production(
        decisions_path=decisions_path, timeline_path=timeline_path, outcomes_path=outcomes_path,
        stuck_after_days=stuck_after_days,
    )
    attention_snapshot = ceo_decision_center.capital_allocation_snapshot(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
    )

    profiles = portfolio["profiles"]

    top_roi_initiatives = [
        {
            "niche": p["niche"],
            "priority_score": p["board_summary"]["priority_score"].get("score")
                if isinstance(p["board_summary"]["priority_score"], dict) else None,
            "expected_roi": p["board_summary"]["expected_roi"],
            "recommendation": p["board_summary"]["recommendation"],
        }
        for p in profiles[:10]
    ]

    projects_losing_value = [
        {"niche": p["niche"], "reasons": p["at_risk"]["reasons"]}
        for p in profiles if p["at_risk"]["flagged"]
    ]

    real_roi_pcts = [
        p["board_summary"]["expected_roi"]["roi_pct"] for p in profiles
        if isinstance(p["board_summary"]["expected_roi"], dict) and isinstance(p["board_summary"]["expected_roi"].get("roi_pct"), (int, float))
    ]
    expected_portfolio_return = (
        {
            "average_roi_pct": round(sum(real_roi_pcts) / len(real_roi_pcts), 1),
            "based_on_n_real_opportunities": len(real_roi_pcts),
            "note": f"متوسط حقيقي عبر {len(real_roi_pcts)} من {len(profiles)} فرصة — البقية بلا عائد استثمار حقيقي محسوب بعد",
        }
        if real_roi_pcts else
        {"answer": "Unknown", "reason": "لا عائد استثمار حقيقي (ROI) محسوب بعد لأي فرصة في المحفظة"}
    )

    return {
        "top_roi_initiatives": top_roi_initiatives,
        "projects_losing_value": projects_losing_value,
        "projects_consuming_resources_without_results": stuck["stuck"],
        "resource_distribution": {
            "scheduling_buckets": scheduling["counts"],
            "attention_by_department": attention_snapshot,
        },
        "expected_portfolio_return": expected_portfolio_return,
        "opportunity_cost_summary": opp_cost["pairings"],
        "portfolio_size": len(profiles),
        "generated_at": _now_iso(),
    }
