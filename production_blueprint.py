#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Global Product Factory (Production Blueprint,
2026-07-24).

The 15 named blueprint components and 6 named production statuses,
checked against this factory's real, already-built intelligence before
writing anything — maximum reuse, near-zero new computation:

  REAL, reused verbatim:
    product_architecture / customer_persona / pricing_strategy <-
      business_dossier.py's own _product_architecture()/
      _customer_profile()/_pricing_strategy(), already computed inside
      opportunity_pipeline.annotate_decision()'s business_dossier field.
    customer_pain_map <- annotate_decision's pain_level.
    competitive_analysis <- annotate_decision's competition field.
    unique_value_proposition <- value_engine.classify_value_proposition()
      (ADR-105, built earlier today).
    required_ai_models <- ai_capability.orchestrator.
      resource_allocation_status() (built earlier today, zero-cost).
    distribution_channels <- growth_engine.evaluate_channel_expansion()
      + revenue_pipeline.plan.build_production_plan()'s real
      recommended_platform.
    revenue_projection <- growth_engine.growth_forecast()'s own real,
      evidence-gated discipline, reused directly (never a second,
      competing forecast).
    production_pipeline <- portfolio_engine.classify_portfolio_class(),
      remapped onto this directive's 12 named pipeline names.
    production_status <- value_engine.classify_lifecycle_stage()'s
      already-real 10 stages, remapped onto the 6 named states.

  REAL, small new aggregation:
    product_specification <- factory_orchestrator.build_spec()
    production_checklist <- inspectors.py's real, named Dual Inspection
      stages (inspect_technical / audit_commercial), described not
      executed (they require a real generated file this report doesn't
      have).
    required_human_review_points <- CLAUDE.md's own documented real
      gap: this factory does not auto-process Human-in-the-Loop
      approvals (pending_review/queue/, scripts/process_approved_
      drafts.py) — a real, disclosed manual step, not fabricated.

  NO REAL SOURCE ANYWHERE IN THIS FACTORY TODAY:
    brand_position — no distinct real brand-positioning concept exists
      separate from competitive_moat/unique_value_proposition (both
      already surfaced elsewhere in this same blueprint).
    marketing_assets — thin but real (lib/publisher_seo.js, SEO
      metadata only), already disclosed in ADR-108.
    sales_funnel — no real conversion/traffic-funnel tracking exists
      anywhere in this factory (market_memory.py's own `conversion`
      field is always honestly None, ADR-106).
"""

from datetime import datetime, timezone

# portfolio_engine's 13 classes -> this directive's 12 named pipelines.
# Not a clean 1:1: 2 portfolio classes (Stock Images, Fonts/Icons/SVG
# Packs) have no target in this directive's own pipeline list at all,
# reported honestly as "outside the 12 named pipelines" rather than
# forced into a nearby one.
_CLASS_TO_PIPELINE = {
    "Premium SaaS": "SaaS",
    "AI Agents": "AI Agent",
    "AI APIs": "API",
    "Enterprise Automation": "Automation Package",
    "Premium Digital Products": "Digital Bundle",
    "Online Courses": "Online Course",
    "Bundles": "Digital Bundle",
    "AI Prompt Packs": "Prompt Pack",
    "Design Assets": "Design Assets",
    "Books": "Ebook",
}
# Templates splits by the real, specific product_family when set;
# a generic/unset family stays honestly ambiguous between Notion/Excel/Canva.
_TEMPLATE_FAMILY_TO_PIPELINE = {
    "notion_workspaces": "Notion",
    "spreadsheet_systems": "Excel",
    "professional_templates": None,  # no real Canva-specific family exists
}


def classify_production_pipeline(decision):
    """Real pipeline classification — reuses portfolio_engine.classify_
    portfolio_class() directly, never a second classifier."""
    import portfolio_engine

    portfolio_class = portfolio_engine.classify_portfolio_class(decision)
    if portfolio_class == "Templates (Notion/Excel/Canva)":
        family = decision.get("product_family")
        pipeline = _TEMPLATE_FAMILY_TO_PIPELINE.get(family)
        if pipeline:
            return pipeline
        return {"value": None, "reason": "فئة قوالب حقيقية لكن بلا عائلة منتج محدَّدة (Notion/Excel/Canva) — لا Canva-specific family حقيقية في هذا المصنع اليوم"}
    pipeline = _CLASS_TO_PIPELINE.get(portfolio_class)
    if pipeline:
        return pipeline
    return {"value": None, "reason": f"فئة محفظة حقيقية ('{portfolio_class}') لا مقابل حقيقي لها بين الـ12 مسار إنتاج المُسمّاة في هذه المهمة"}


# value_engine.classify_lifecycle_stage()'s 10 real stages, remapped
# onto the 6 named production statuses -- real, deterministic, no new
# evidence computed.
def classify_production_status(niche, decisions_path=None, timeline_path=None, outcomes_path=None):
    """Real production status -- reuses value_engine.classify_lifecycle_
    stage() directly. QUALITY REVIEW is distinguished from BUILDING via
    inspectors.py's own real quarantine record (a niche that failed
    Dual Inspection and was logged to QUARANTINE.md) -- the one real
    signal this factory has for "currently under quality review" as
    opposed to "not yet attempted.\""""
    import value_engine
    import inspectors

    lifecycle = value_engine.classify_lifecycle_stage(
        niche, decisions_path=decisions_path, timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    stages = lifecycle["stages"]
    quarantined = niche.strip().lower() in inspectors._read_quarantined_niches()

    if stages["commercial_launch"]["reached"]:
        status = "LEARNING" if stages["continuous_improvement"]["reached"] else "LIVE"
    elif stages["premium_production"]["reached"]:
        status = "READY TO SELL"
    elif stages["prototype"]["reached"]:
        status = "QUALITY REVIEW" if quarantined else "BUILDING"
    elif stages["evidence_based_validation"]["reached"]:
        status = "READY TO BUILD"
    else:
        status = {"value": None, "reason": "لا قرار حقيقي بعد لهذا النيتش"}

    return {"status": status, "lifecycle_stage": lifecycle}


_NO_SOURCE_BLUEPRINT_FIELDS = {
    "brand_position": "لا مفهوم تموضع علامة تجارية حقيقي متمايز عن unique_value_proposition/competitive_moat في هذا المصنع اليوم",
    "sales_funnel": "لا تتبّع قمع تحويل/زيارات حقيقي في هذا المصنع اليوم (نفس فجوة market_memory.py's conversion field، ADR-106)",
}


def build_production_blueprint(niche, decisions_path=None, board_path=None, alerts_path=None,
                                reopen_log_path=None, evidence_path=None, timeline_path=None, outcomes_path=None):
    """The real, unified 15-component Production Blueprint for one
    niche. Returns None (never fabricated) when this niche has no real
    decision on record at all."""
    import factory_orchestrator as fo
    import opportunity_pipeline as op
    import growth_engine
    import value_engine
    from ai_capability import orchestrator as ai_orchestrator
    from revenue_pipeline import plan as plan_module

    decision = fo.find_decision(niche, decisions_path=decisions_path)
    if decision is None:
        return None

    annotated = op.annotate_decision(decision, board_path=board_path, alerts_path=alerts_path, reopen_log_path=reopen_log_path)
    business_dossier = annotated.get("business_dossier") or {}
    spec = fo.build_spec(decision) if decision.get("status") == "ACCEPTED" else None

    profile = value_engine.compute_value_profile(
        niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    value_proposition = profile.get("value_proposition") if profile else {
        "value": None, "reason": "يتطلب قراراً مقبولاً فعلاً (ACCEPTED) لتقييم value_proposition حقيقي",
    }

    production_plan = plan_module.build_production_plan(decision)

    return {
        "niche": niche,
        "product_specification": spec,
        "product_architecture": business_dossier.get("product_architecture"),
        "customer_persona": business_dossier.get("customer_profile"),
        "customer_pain_map": annotated.get("pain_level"),
        "competitive_analysis": annotated.get("competition"),
        "unique_value_proposition": value_proposition,
        "pricing_strategy": business_dossier.get("pricing_strategy"),
        "brand_position": {"value": None, "reason": _NO_SOURCE_BLUEPRINT_FIELDS["brand_position"]},
        "production_checklist": {
            "stages": ["inspect_technical (inspectors.py)", "audit_commercial (inspectors.py)"],
            "note": "بوابة Dual Inspection الحقيقية الوحيدة في هذا المصنع — تُنفَّذ فعلياً أثناء الإنتاج، لا تُستدعى هنا (تحتاج ملفاً حقيقياً مُولَّداً)",
        },
        "required_ai_models": ai_orchestrator.resource_allocation_status(),
        "required_human_review_points": {
            "value": "pending_review/queue/ + scripts/process_approved_drafts.py",
            "note": "خطوة موافقة بشرية حقيقية موثَّقة — هذا المصنع لا يُعالج موافقات Human-in-the-Loop تلقائياً (CLAUDE.md)",
        },
        "distribution_channels": {
            "recommended_platform": production_plan.get("recommended_platform"),
            "channel_expansion": growth_engine.evaluate_channel_expansion(),
        },
        "marketing_assets": {
            "value": "SEO metadata only (lib/publisher_seo.js)",
            "reason": "لا قدرة أصول تسويقية حقيقية أبعد من ذلك في هذا المصنع اليوم (مُفصَح عنها سابقاً في ADR-108)",
        },
        "sales_funnel": {"value": None, "reason": _NO_SOURCE_BLUEPRINT_FIELDS["sales_funnel"]},
        "revenue_projection": growth_engine.growth_forecast(evidence_path=evidence_path),
        "production_pipeline": classify_production_pipeline(decision),
        "production_status": classify_production_status(
            niche, decisions_path=decisions_path, timeline_path=timeline_path, outcomes_path=outcomes_path,
        ),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_production_missions_board(decisions_path=None, board_path=None, alerts_path=None,
                                     reopen_log_path=None, evidence_path=None, timeline_path=None, outcomes_path=None):
    """Mission Control's real, continuous view: every real ACCEPTED
    opportunity's production_status, bucketed under the 6 named states.
    Reuses decision_engine.ranking.rank_all() for the real accepted set
    (cheap), classify_production_status() per niche (no full blueprint
    needed just to bucket by status)."""
    from decision_engine import ranking

    accepted = [
        d for d in ranking.rank_all(path=decisions_path)
        if d.get("status") == "ACCEPTED" and d.get("niche")
    ]

    buckets = {"READY TO BUILD": [], "BUILDING": [], "QUALITY REVIEW": [], "READY TO SELL": [], "LIVE": [], "LEARNING": []}
    for d in accepted:
        result = classify_production_status(
            d["niche"], decisions_path=decisions_path, timeline_path=timeline_path, outcomes_path=outcomes_path,
        )
        status = result["status"]
        if isinstance(status, str) and status in buckets:
            buckets[status].append(d["niche"])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_real_accepted_opportunities": len(accepted),
        "buckets": buckets,
        "counts": {k: len(v) for k, v in buckets.items()},
    }
