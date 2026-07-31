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
