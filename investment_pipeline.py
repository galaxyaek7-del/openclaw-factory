#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Investment Pipeline (Global Revenue Discovery Engine,
2026-07-24).

The founder-named 10 ranking dimensions and 12 per-opportunity fields,
checked field-by-field against this factory's real, already-built
intelligence before writing anything — pure aggregation, never a new
scoring pass:

  9 of 10 ranking dimensions already real, reused verbatim from
  opportunity_pipeline.annotate_decision(): market_size, competition,
  willingness_to_pay (market_evidence.py), production_difficulty
  (technical_complexity), long_term_strategic_value (strategic_
  investment's real becomes_more_valuable_over_time), defensibility,
  recurring_revenue_potential, global_scalability, ai_leverage.

  1 genuinely new: urgency — no dedicated real signal exists anywhere
  in this factory. Built as a disclosed, evidence-grounded PROXY (real
  active market_alerts.py severity/count — an active Critical alert IS
  a genuine time-sensitivity signal), never a fabricated general
  urgency score — same "real proxy, not a guessed absolute" discipline
  market_size's own docstring already uses for discussion volume.

  11 of 12 per-opportunity fields already real, reused from already-
  built modules: commercial_score (opportunity_score), business_model
  (customer_type ladder proxy), estimated_revenue/estimated_profit
  (revenue_pipeline.plan.estimate_roi()), risk_analysis (annotate_
  decision's risk field), customer_profile (business_dossier's already-
  computed real evidence-count profile), recommended_product (growth_
  engine.evaluate_product_multiplication()), recommended_price/
  recommended_distribution (revenue_pipeline.plan.build_production_
  plan()), recommended_marketing (thin but real — SEO metadata only,
  already disclosed in ADR-108).

  1 deferred, same real reason as this directive's own Country/China
  sections (ADR-111, itself the reaffirmation of ADR-103/106/108/110):
  country_priority — zero real local market-data connector exists for
  any country in this factory today.
"""

from datetime import datetime, timezone


def _urgency_signal(active_alerts):
    """Real, disclosed proxy — an active real market_alerts.py Critical/
    High severity event IS a genuine time-sensitivity signal (a real
    competitor just moved). Never a fabricated general urgency score."""
    if not active_alerts or not active_alerts.get("total"):
        return {"value": "none", "reason": "لا تنبيهات سوق حقيقية نشطة لهذا النيتش لاستخدامها كمؤشر إلحاح", "by_severity_counts": {}}
    counts = active_alerts.get("by_severity_counts") or {}
    critical, high = counts.get("Critical", 0), counts.get("High", 0)
    if critical:
        level = "high"
    elif high:
        level = "medium"
    else:
        level = "low"
    return {
        "value": level,
        "reason": f"{critical} تنبيه Critical + {high} تنبيه High نشط حقيقي (proxy إلحاح، وليس مقياساً عاماً مُختلَقاً)",
        "by_severity_counts": counts,
    }


def build_investment_pipeline_entry(niche, decisions_path=None, board_path=None, alerts_path=None,
                                     reopen_log_path=None, evidence_path=None):
    """Real, unified Investment Pipeline entry for one niche. Returns
    None (never fabricated) when this niche has no real decision on
    record at all — same wider-than-ACCEPTED scope as commercial_
    intelligence.py, since discovery-stage intelligence is real and
    useful pre-decision too."""
    import factory_orchestrator as fo
    import opportunity_pipeline as op
    import market_evidence
    import growth_engine
    from revenue_pipeline import plan as plan_module

    decision = fo.find_decision(niche, decisions_path=decisions_path)
    if decision is None:
        return None

    annotated = op.annotate_decision(decision, board_path=board_path, alerts_path=alerts_path, reopen_log_path=reopen_log_path)
    willingness_to_pay = market_evidence.get_willingness_to_pay_signal(niche, evidence_path=evidence_path)
    production_plan = plan_module.build_production_plan(decision)
    strategic_investment = annotated.get("strategic_investment") or {}

    cost_result = plan_module.estimate_production_cost()
    roi_result = plan_module.estimate_roi(
        production_plan.get("recommended_price"),
        cost_result.get("estimated_cost_usd") if cost_result.get("maturity") == "REAL" else None,
        platform=production_plan.get("economics_platform", "gumroad_digital"),
    )

    product_opportunities = (
        growth_engine.evaluate_product_multiplication(
            niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        )
        if decision.get("status") == "ACCEPTED" else
        {"value": None, "reason": "يتطلب قراراً مقبولاً فعلاً (ACCEPTED) — هذا القرار حالياً: " + str(decision.get("status"))}
    )

    business_dossier = annotated.get("business_dossier") or {}

    return {
        "niche": niche,
        "ranking_dimensions": {
            "market_size": annotated.get("market_size"),
            "competition": annotated.get("competition"),
            "urgency": _urgency_signal(annotated.get("active_alerts")),
            "willingness_to_pay": willingness_to_pay,
            "production_difficulty": annotated.get("technical_complexity"),
            "long_term_strategic_value": strategic_investment.get("becomes_more_valuable_over_time"),
            "defensibility": annotated.get("defensibility"),
            "recurring_revenue_potential": annotated.get("recurring_revenue_potential"),
            "global_scalability": annotated.get("global_scalability"),
            "ai_leverage": annotated.get("ai_leverage"),
        },
        "commercial_score": decision.get("opportunity_score"),
        "business_model": annotated.get("customer_type"),
        "estimated_revenue": roi_result,
        "estimated_profit": roi_result,
        "risk_analysis": annotated.get("risk"),
        "country_priority": {
            "value": None,
            "reason": "مؤجَّل بوعي — لا موصّل بيانات سوق محلي حقيقي لأي دولة في هذا المصنع اليوم (ADR-103، مؤكَّد مجدداً في ADR-111)",
        },
        "customer_profile": business_dossier.get("customer_profile"),
        "recommended_product": product_opportunities,
        "recommended_price": production_plan.get("recommended_price"),
        "recommended_distribution": production_plan.get("recommended_platform"),
        "recommended_marketing": {
            "value": "SEO metadata only (lib/publisher_seo.js)",
            "reason": "لا قدرة حملات تسويقية حقيقية أبعد من ذلك في هذا المصنع اليوم (مُفصَح عنها سابقاً في ADR-108)",
        },
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_investment_pipeline(decisions_path=None, board_path=None, alerts_path=None,
                               reopen_log_path=None, evidence_path=None, limit=None):
    """The real, whole-factory Investment Pipeline — every real decision
    (any status, not just ACCEPTED — discovery-stage opportunities are
    real investment candidates too), ranked by real opportunity_score
    descending, reusing decision_engine.ranking.rank_all()'s own real
    order (cheap — no per-niche profile computation needed to sort).

    `limit` (same real, disclosed scale-valve pattern as value_engine.
    build_value_engine_report(), Autonomous Global Commercial Company
    Layer, 2026-07-23): only the top-N by real opportunity_score get a
    full entry built. Default None preserves exact prior behavior."""
    from decision_engine import ranking

    ranked = ranking.rank_all(path=decisions_path)
    if limit is not None:
        ranked = ranked[:limit]

    entries = [
        build_investment_pipeline_entry(
            d["niche"], decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        )
        for d in ranked if d.get("niche")
    ]
    entries = [e for e in entries if e is not None]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_real_decisions": len(ranking.rank_all(path=decisions_path)),
        "count": len(entries),
        "limited_to": limit,
        "entries": entries,
    }
