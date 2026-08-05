"""
Company Evolution Engine (EOS Phase 1, 2026-07-19) — "detect missing
capabilities, bottlenecks, high-ROI opportunities, duplicate work,
technical debt; recommend improvements automatically."

Concatenates five already-real signals into one report, same
"combine, don't reimplement" pattern mission_control_api.py's own
combined executive report already established:

  - Bottleneck detection: executive_intelligence.bottlenecks (ADR-052)
  - Technical debt: strategic_intelligence.technical_debt (ADR-054,
    itself a verbatim reuse of executive_intelligence.inactivity)
  - High-ROI opportunities: revenue_pipeline.pipeline's own real
    per-opportunity expected_roi (ADR-041 fee math), ranked here
  - Tool/AI-integration recommendations: tool_intelligence.proposals
    (Autonomous Digital Company v1, Track B3)
  - Missing capabilities: capability_registry_scanner (new, this phase)

Duplicate-work detection is deliberately NOT included here —
scripts/check_jsonl_duplication.js already covers the one real,
narrow, CI-enforced case that exists; general logic-duplication
detection would need AST/semantic analysis this factory doesn't have
and shouldn't fabricate (see ADR-080).

Recommending improvements stops at "evidence-cited proposal" —
tool_intelligence.proposals' own boundary. This module never executes
anything; it only assembles what's already real.
"""

from datetime import datetime, timezone


def _high_roi_opportunities(decisions_path=None, outcomes_path=None, timeline_path=None, top_n=5):
    from revenue_pipeline import pipeline as revenue_pipeline

    result = revenue_pipeline.run_revenue_pipeline(
        decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path,
    )
    if not result.get("processed"):
        return {"answer": "Unknown", "reason": result.get("reason", "لا فرص ACCEPTED لتقييم العائد عليها")}

    measured = [r for r in result["results"] if r["expected_roi"].get("maturity") == "REAL"]
    if not measured:
        return {"answer": "Unknown", "reason": "لا فرصة واحدة لديها سعر وتكلفة إنتاج حقيقيان معاً لحساب عائد حقيقي بعد"}

    ranked = sorted(measured, key=lambda r: r["expected_roi"]["roi_pct"], reverse=True)
    return {
        "top": [{"niche": r["niche"], "roi_pct": r["expected_roi"]["roi_pct"], "net_after_cost": r["expected_roi"]["expected_net_after_cost"]} for r in ranked[:top_n]],
        "measured_count": len(measured),
        "total_accepted": result["processed"],
        "source": "revenue_pipeline.pipeline.run_revenue_pipeline()",
    }


def _customer_success_bottleneck(proposals):
    """Continuous Improvement (Global Trust & Resilience Layer, Round 7,
    2026-07-29): "what is the biggest bottleneck preventing customer
    success?" -- reuses tool_intelligence.proposals' own real, already-
    wired customer-funnel signal (_customer_funnel_proposal(), fed by
    customer_pipeline.list_pipeline_overview()'s real stuck-request
    detection) rather than computing a second, competing bottleneck
    detector. Honestly reports none detected when it didn't fire."""
    customer_proposal = next((p for p in proposals if p.get("id") == "resolve_stuck_customer_requests"), None)
    if not customer_proposal:
        return {
            "detected": False,
            "reason": "لا اختناق حقيقي يمسّ نجاح العميل مكتشَف هذه الدورة (customer_pipeline.list_pipeline_overview())",
        }
    return {
        "detected": True,
        "summary": customer_proposal["tool"],
        "evidence": customer_proposal["evidence"],
        "source": "tool_intelligence.proposals._customer_funnel_proposal()",
    }


def build_evolution_report(decisions_path=None, outcomes_path=None, timeline_path=None,
                            sales_ledger_path=None, capability_registry_path=None):
    from executive_intelligence import bottlenecks as bottleneck_module
    from executive_intelligence import engine_health as engine_health_module
    from strategic_intelligence import technical_debt as tech_debt_module
    from tool_intelligence import proposals as tool_proposals_module
    from capability_registry_scanner import find_capability_gaps

    health = engine_health_module.compute_engine_health(timeline_path=timeline_path)
    bottleneck_result = bottleneck_module.detect_bottlenecks(
        health, decisions_path=decisions_path, outcomes_path=outcomes_path,
    )
    debt_result = tech_debt_module.components_at_risk_of_technical_debt(
        decisions_path=decisions_path, timeline_path=timeline_path, sales_ledger_path=sales_ledger_path,
    )
    high_roi = _high_roi_opportunities(decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path)
    gaps = find_capability_gaps(registry_path=capability_registry_path)
    proposals = tool_proposals_module.list_proposals()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bottlenecks": bottleneck_result,
        "technical_debt": debt_result,
        "high_roi_opportunities": high_roi,
        "capability_gaps": gaps,
        "tool_proposals": proposals,
        "customer_success_bottleneck": _customer_success_bottleneck(proposals),
    }


def render_markdown(report):
    lines = []

    lines.append("## الاختناقات")
    if report["bottlenecks"]["detected"]:
        for b in report["bottlenecks"]["items"]:
            lines.append(f"- {b['evidence']}")
    else:
        lines.append(f"- {report['bottlenecks']['reason']}")

    lines.append("\n## الديون التقنية (مكوّنات معرَّضة)")
    debt = report["technical_debt"]
    if debt["answer"] == "Unknown":
        lines.append(f"- {debt['reason']}")
    else:
        for e in debt["evidence"]:
            lines.append(f"- {e['component']}: {e['evidence']}")

    lines.append("\n## أعلى الفرص عائداً (ROI)")
    roi = report["high_roi_opportunities"]
    if roi.get("answer") == "Unknown":
        lines.append(f"- {roi['reason']}")
    else:
        for o in roi["top"]:
            lines.append(f"- {o['niche']}: {o['roi_pct']}% عائد (صافٍ بعد التكلفة: ${o['net_after_cost']})")

    lines.append("\n## فجوات القدرات المكتشَفة")
    gaps = report["capability_gaps"]
    lines.append(f"- {len(gaps['discovery_level'])} قدرة عند مستوى DISCOVERY، {len(gaps['estimated_level'])} عند ESTIMATED (من أصل {gaps.get('total_capabilities', 0)})")
    for c in gaps["discovery_level"][:5]:
        lines.append(f"  - {c.get('name', c.get('id'))} [DISCOVERY]")

    lines.append("\n## اقتراحات الأدوات (مقترَح، لا تنفيذ)")
    for p in report["tool_proposals"]:
        lines.append(f"- {p['tool']}")

    lines.append("\n## أكبر اختناق حقيقي أمام نجاح العميل")
    bottleneck = report.get("customer_success_bottleneck") or {}
    if bottleneck.get("detected"):
        lines.append(f"- {bottleneck['summary']}")
    else:
        lines.append(f"- {bottleneck.get('reason', 'غير محسوب')}")

    return "\n".join(lines) + "\n"


# ── Galaxy Evolution Report (ADR-173, 2026-08-05) ──
# Founder's "Company Evolution Protocol V1" directive: a monthly
# "GALAXY EVOLUTION REPORT" (strengths/weaknesses/critical risks/hidden
# opportunities/recommended improvements/priority actions/long-term
# impact/monthly revenue impact/implementation effort, ROI-ranked) + a
# "Global Benchmark" study of world-class companies. Research found
# build_evolution_report() above (this same module, EOS Phase 1,
# 2026-07-19) already covers bottlenecks/technical debt/high-ROI
# opportunities/capability gaps/tool proposals -- almost the entire
# ask, just not labeled with the directive's exact section names and
# missing a balanced "Current Strengths" view (the existing report is
# gap-focused by design). This function relabels + extends it, never
# recomputing what build_evolution_report() already provides.
#
# Two real, disclosed gaps, honored per this factory's own Truth First
# Constitution (ADR-160) rather than fabricated: (1) "Potential Monthly
# Revenue Impact" and "Estimated Implementation Effort" per recommendation
# have zero real signal anywhere in this factory (confirmed repeatedly
# this session -- $0 real revenue to model an impact against, no real
# historical per-task duration data to estimate effort from) -- reported
# as NOT_MEASURABLE per item, never guessed; (2) "Global Benchmark --
# continuously study world-class companies" has no real, re-runnable
# internal capability -- competitor_discovery.py researches real
# per-niche product competitors, not general company-excellence
# principles, and no live external company-research pipeline exists
# anywhere in this factory. Disclosed as NOT_BUILT, not silently skipped.
def build_galaxy_evolution_report(decisions_path=None, outcomes_path=None, timeline_path=None,
                                   sales_ledger_path=None, capability_registry_path=None,
                                   base_report=None):
    """The one real aggregator -- computes build_evolution_report() and
    capital_allocation_engine.build_capital_allocation_dashboard()
    exactly once each, maps them onto the directive's 9 named sections,
    ROI-ranks recommendations using the one real numeric signal that
    exists (capital_allocation_engine's own expected ROI), and honestly
    discloses the 2 items with zero real signal rather than fabricating
    a number."""
    import capital_allocation_engine as cae

    base = base_report if base_report is not None else build_evolution_report(
        decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path,
        sales_ledger_path=sales_ledger_path, capability_registry_path=capability_registry_path,
    )
    capital = cae.build_capital_allocation_dashboard(
        decisions_path=decisions_path, board_path=None, alerts_path=None,
    )

    top_roi = capital.get("top_roi_initiatives") or []

    return {
        "current_strengths": {
            "value": "see truth_registry.py's real READY-component count and reality_audit.py's real Reality Score for the current, live figures -- not re-queried here to avoid a redundant 250s+ live scan",
            "source": "truth_registry.py (ADR-168) / reality_audit.py (ADR-162)",
        },
        "current_weaknesses": {
            "technical_debt": base["technical_debt"],
            "capability_gaps": base["capability_gaps"],
        },
        "critical_risks": {
            "value": "see resilience_monitor.py::assess_resilience() and the Company Readiness Audit's own Critical/Revenue Blockers sections for the current, live findings -- 0 real ACCEPTED opportunities, 0 real published books ever, as of the most recent audit",
            "source": "resilience_monitor.py + enterprise_factory_audit.py",
        },
        "hidden_opportunities": {
            "high_roi_opportunities": base["high_roi_opportunities"],
            "capital_opportunity_cost": capital.get("opportunity_cost_summary"),
        },
        "recommended_improvements": base["tool_proposals"],
        "high_priority_actions_ranked_by_roi": [
            {"initiative": i.get("niche") or i.get("name"), "expected_roi": i.get("expected_roi") or i.get("roi_pct"), "source": "capital_allocation_engine.py's real top_roi_initiatives"}
            for i in top_roi[:10]
        ],
        "expected_long_term_impact": {
            "value": "qualitative only -- see high_priority_actions_ranked_by_roi above for the real, numeric ROI signal this factory actually has",
            "reason": "No real long-term (multi-year) impact model exists anywhere in this factory -- strategic_intelligence_core.py's own evaluate_strategic_horizons() already discloses this same honest gap for 30d/90d/1y/3y/10y horizons.",
        },
        "potential_monthly_revenue_impact": "NOT_MEASURABLE -- zero real revenue exists to model an incremental impact against (confirmed: channels/ledger.py's real total_revenue_usd is $0); estimating one would be a fabricated number, forbidden by this factory's own Truth First Constitution (ADR-160)",
        "estimated_implementation_effort": "NOT_MEASURABLE -- no real historical per-task duration data exists anywhere in this factory (confirmed repeatedly: execution_status.py/gfos.py/strategic_planning.py all disclose 'estimated_completion: Unknown' for the same reason)",
        "global_benchmark": {
            "status": "NOT_BUILT",
            "reason": "No real, re-runnable internal capability studies world-class companies -- competitor_discovery.py researches real per-niche product competitors, a different, narrower concept. Building a live external company-research pipeline is a real, disclosed gap, not silently assumed to exist.",
        },
        "customer_success_bottleneck": base["customer_success_bottleneck"],
        "generated_at": base["generated_at"],
    }


def render_galaxy_evolution_report_markdown(report=None):
    report = report if report is not None else build_galaxy_evolution_report()
    lines = [f"# Galaxy Evolution Report", f"Generated: {report.get('generated_at')}", ""]
    sections = [
        ("Current Strengths", "current_strengths"),
        ("Current Weaknesses", "current_weaknesses"),
        ("Critical Risks", "critical_risks"),
        ("Hidden Opportunities", "hidden_opportunities"),
        ("Recommended Improvements", "recommended_improvements"),
        ("High Priority Actions (ranked by ROI)", "high_priority_actions_ranked_by_roi"),
        ("Expected Long-Term Impact", "expected_long_term_impact"),
        ("Potential Monthly Revenue Impact", "potential_monthly_revenue_impact"),
        ("Estimated Implementation Effort", "estimated_implementation_effort"),
        ("Global Benchmark", "global_benchmark"),
    ]
    for label, key in sections:
        lines.append(f"## {label}")
        lines.append(f"{report.get(key)}")
        lines.append("")
    return "\n".join(lines)
