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
        # Autonomous Evolution Protocol (ADR-187, 2026-08-07): 4 sections
        # the founder's directive named that build_galaxy_evolution_report()
        # didn't yet carry explicitly. Each is pure citation over an
        # already-real, already-cheap source -- no new judgment engine,
        # same discipline as every field above.
        "commercial_debt": _commercial_debt(),
        "strategic_debt": _strategic_debt(),
        "competitive_threats": _competitive_threats(),
        "never_build": _never_build_list(),
        # Autonomous Evolution Engine (ADR-193, 2026-08-07): closes the
        # one real gap MONTHLY_EVOLUTION_REPORT.md found -- "what became
        # obsolete / should be removed" had no real citation anywhere in
        # this report, even though a real, cheap, mechanical answer
        # already existed (enterprise_validation.py::detect_unused_services(),
        # ADR-166) and had simply never been threaded in.
        "obsolete_components": _obsolete_components(),
    }


def _obsolete_components():
    try:
        from enterprise_validation import detect_unused_services
        result = detect_unused_services()
        return {
            "value": result,
            "source": "enterprise_validation.py::detect_unused_services() (ADR-166) -- real, mechanical, re-runnable name-diff over server.js/factory_loop.js's real dispatch call sites.",
        }
    except Exception as e:
        return {"status": "unavailable", "reason": str(e)}


def _commercial_debt():
    try:
        from commercial_readiness import commercial_readiness_score
        result = commercial_readiness_score()
        return {
            "bottleneck_dimension": result.get("bottleneck"),
            "overall_score": result.get("overall"),
            "dimensions": result.get("dimensions"),
            "source": "commercial_readiness.py::commercial_readiness_score() (ADR-181)",
        }
    except Exception as e:
        return {"status": "unavailable", "reason": str(e)}


def _strategic_debt():
    try:
        from strategic_intelligence_core import evaluate_strategic_horizons
        horizons = evaluate_strategic_horizons()
        return {
            "value": horizons,
            "interpretation": "Every horizon reporting 'NOT ENOUGH EVIDENCE' (rather than a real projection) IS the real strategic debt -- no real multi-horizon planning signal exists yet, honestly disclosed rather than estimated.",
            "source": "strategic_intelligence_core.py::evaluate_strategic_horizons() (ADR-137)",
        }
    except Exception as e:
        return {"status": "unavailable", "reason": str(e)}


def _competitive_threats():
    """Deliberately does NOT trigger a fresh live competitor_discovery.py
    query (real network calls, per-niche, not cheap) just to render a
    report section -- cites the already-persisted real snapshot count
    instead, honestly labeled as passive/dated, not a live threat scan."""
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parent / "data" / "competitor_database.json"
    try:
        with open(path, encoding="utf-8") as f:
            db = json.load(f)
        return {
            "real_niches_with_tracked_competitor_data": len(db) if isinstance(db, dict) else None,
            "note": "Passive citation of already-persisted real snapshots (data/competitor_database.json) -- not a fresh live scan, which would mean real per-niche network calls on every report generation. See competitor_discovery.py for the real, on-demand per-niche researcher.",
            "source": "data/competitor_database.json",
        }
    except (OSError, json.JSONDecodeError) as e:
        return {"status": "unavailable", "reason": str(e)}


# Autonomous Evolution Protocol (ADR-187): a real, static, disclosed list
# of standing founder-confirmed deferrals already decided and recorded
# elsewhere in this factory's own governance history -- never a guess,
# never new judgment. Update this list only when a real new standing
# "not now" decision is made (an AskUserQuestion the founder actually
# answered), not speculatively.
_NEVER_BUILD_DECISIONS = [
    {"item": "Global Commerce Intelligence Division (GCID)", "decision": "Deferred (ADR-148, 2026-07-30)", "reason": "Zero real dollars at time of decision -- same Golden Rule that blocked earlier global expansion."},
    {"item": "Global Affiliate Commerce Engine (20-network connector architecture)", "decision": "Architecture documented, zero code authorized (ADR-152, 2026-07-30)", "reason": "Contradicted the founder's own immediately-preceding directive to pause Affiliate Commerce expansion until a real account is approved."},
    {"item": "Country-level market intelligence (per-country data connectors)", "decision": "Deferred (standing decision, 2026-07-23, re-confirmed ADR-175)", "reason": "Zero real local-market data connector exists for any market; re-triggers at the first real dollar or a real connector becoming available."},
    {"item": "Always-on autonomous daemon / global event bus / queue infrastructure", "decision": "Declined 6+ times (ADR-107, 110, 115, 142, 147, 157)", "reason": "New always-on execution infrastructure the founder has never approved; existing tick-based automation covers the real need."},
    {"item": "Automated execution of Evolution Queue proposals without founder approval", "decision": "Permanently human-gated by explicit founder decision (ADR-133, reconfirmed ADR-142/144/147/157)", "reason": "The one standing rule this factory has never revisited: 'Execute is, by explicit founder decision, human-gated always.'"},
]


def _never_build_list():
    return {
        "items": _NEVER_BUILD_DECISIONS,
        "note": "Real, already-decided standing deferrals cited from this factory's own governance history -- never invented, never re-litigated automatically. Only grows when the founder actually makes a new such decision.",
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
        ("Commercial Debt", "commercial_debt"),
        ("Strategic Debt", "strategic_debt"),
        ("Competitive Threats", "competitive_threats"),
        ("What Should Never Be Built", "never_build"),
        ("Obsolete Components", "obsolete_components"),
    ]
    for label, key in sections:
        lines.append(f"## {label}")
        lines.append(f"{report.get(key)}")
        lines.append("")
    return "\n".join(lines)
