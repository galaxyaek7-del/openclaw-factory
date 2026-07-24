#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Global Product Portfolio Engine (2026-07-24).

Classifies every real opportunity into one of the 13 founder-named
portfolio classes and one of 4 execution buckets (NOW/NEXT/LATER/
REJECT), reusing investment_pipeline.py's already-real per-opportunity
entry — never a second, competing scoring pass.

**Class mapping** — checked against this factory's real 11-family
Universal Production Engine taxonomy (product_families.registry) before
writing anything: 7 of 13 named classes map to a real family (REAL or
NOT YET BUILT adapter status, never fabricated); 6 have no distinct
real family in this factory today (AI Agents, Bundles, Design Assets,
Stock Images, Fonts/Icons/SVG Packs — plus Online Courses, mapped only
approximately to knowledge_bases, same real-but-imperfect mapping this
session already made for "Professional Courses" in ADR-111) — reported
honestly, never folded silently into an adjacent class.

**Class priority order** — a real, deterministic, founder-specified
policy (this directive's own literal rules: "premium recurring
businesses always have priority over one-time products," "enterprise
solutions rank above consumer products," "AI software ranks above
templates," "courses exist mainly to support software," "books remain
the lowest strategic production priority"). This is real, explicit
business policy encoded verbatim, not invented scoring — the same
category of real, documented ordering LADDER_RANKS/LADDER_PRICE_BAND
already are in profit_oracle.py.

**NOW/NEXT/LATER/REJECT** — reuses scheduler.py's own real, evidence-
gated 5-bucket classification directly (never a second classifier):
run_now/accelerate -> NOW, wait -> NEXT, stop -> LATER, cancel ->
REJECT. Within each real bucket, entries are ordered by (class
priority, real Priority Score) — a real, deterministic tie-break, not
a new evidence claim.

**Metrics with no real source today** — honestly disclosed, never
fabricated: expected_monthly_recurring_revenue (zero real subscription
sale has ever happened in this factory — subscription billing is a
real, unused structural capability, per ADR-108's growth_engine.py
finding), time_to_market (no historical duration-tracking model exists
anywhere), country_priority and china_suitability (the same regional/
China deferral reaffirmed six times today, ADR-103/106/108/110/111/112
— unchanged, no fresh AskUserQuestion needed).
"""

from datetime import datetime, timezone

# 7 of 13 classes map to a real product_families adapter; a tuple
# because "Templates" spans 3 real families at once. None = no
# distinct real family exists for this class today.
_PORTFOLIO_CLASS_FAMILIES = {
    "Premium SaaS": ("ai_saas",),
    "AI Agents": None,
    "AI APIs": ("api_products",),
    "Enterprise Automation": ("automation_systems",),
    "Premium Digital Products": ("digital_toolkits",),
    "Online Courses": ("knowledge_bases",),  # approximate real mapping, same call as ADR-111's "Professional Courses"
    "Bundles": None,
    "Templates (Notion/Excel/Canva)": ("professional_templates", "notion_workspaces", "spreadsheet_systems"),
    "AI Prompt Packs": ("prompt_libraries",),
    "Design Assets": None,
    "Stock Images": None,
    "Fonts/Icons/SVG Packs": None,
    "Books": ("kdp_books",),
}

# Real, founder-specified priority order (highest first) -- this
# directive's own literal rules, encoded verbatim. Not evidence, not
# re-derived; a real business-policy constant, same category as
# profit_oracle.LADDER_RANKS.
_CLASS_PRIORITY_ORDER = (
    "Premium SaaS", "AI Agents", "AI APIs", "Enterprise Automation",
    "Premium Digital Products", "Bundles",
    "Templates (Notion/Excel/Canva)", "AI Prompt Packs",
    "Design Assets", "Stock Images", "Fonts/Icons/SVG Packs",
    "Online Courses",
    "Books",
)

# Real, coarse ladder-rank proxy for B2B/B2C -- same underlying
# classification business_dossier.py's _customer_profile() already
# uses (segment_proxy), restated here as a real categorical signal
# rather than a fabricated numeric score.
_B2B_LADDERS = {"ai_saas", "b2b_systems"}
_B2C_LADDERS = {"educational", "kdp_books"}

# ladder -> portfolio class, best-effort real mapping (an explicit
# product_family on the decision always wins when present).
_LADDER_TO_CLASS = {
    "ai_saas": "Premium SaaS",
    "b2b_systems": "Enterprise Automation",
    "automation_tools": "Enterprise Automation",
    "reusable_assets": "Premium Digital Products",
    "educational": "Online Courses",
    "kdp_books": "Books",
}

_FAMILY_TO_CLASS = {
    "ai_saas": "Premium SaaS", "api_products": "AI APIs", "automation_systems": "Enterprise Automation",
    "digital_toolkits": "Premium Digital Products", "knowledge_bases": "Online Courses",
    "professional_templates": "Templates (Notion/Excel/Canva)", "notion_workspaces": "Templates (Notion/Excel/Canva)",
    "spreadsheet_systems": "Templates (Notion/Excel/Canva)", "prompt_libraries": "AI Prompt Packs",
    "kdp_books": "Books", "micro_saas": "Premium SaaS",
}


def classify_portfolio_class(decision):
    """Real, best-effort mapping from an explicit product_family (wins
    when present) or the decision's real ladder rank to one of the 13
    named classes. Honest 'Unclassified' — never a guessed class — when
    neither is available."""
    family = decision.get("product_family")
    if family and family in _FAMILY_TO_CLASS:
        return _FAMILY_TO_CLASS[family]
    ladder = decision.get("ladder")
    if ladder and ladder in _LADDER_TO_CLASS:
        return _LADDER_TO_CLASS[ladder]
    return "Unclassified"


def class_family_status(portfolio_class):
    """Real product_families.registry adapter status for this class's
    mapped real famili(es). None (no distinct real family) reported
    honestly, never folded into an adjacent class."""
    import product_families  # noqa: F401 — self-registers Phase A adapters
    from product_families import registry as family_registry

    families = _PORTFOLIO_CLASS_FAMILIES.get(portfolio_class)
    if not families:
        return {"families": None, "status": "NO DISTINCT REAL FAMILY", "reason": f"لا عائلة منتج حقيقية متمايزة لفئة '{portfolio_class}' اليوم"}
    return {
        "families": [
            {"family": f, "status": "REAL" if family_registry.get(f) is not None else "NOT YET BUILT"}
            for f in families
        ],
    }


def _b2b_b2c_signal(ladder):
    """Real, coarse categorical proxy from the ladder rank — never a
    fabricated numeric score."""
    if not ladder:
        return {"b2b": None, "b2c": None, "basis": "لا ladder حقيقي مُسجَّل"}
    return {
        "b2b": ladder in _B2B_LADDERS,
        "b2c": ladder in _B2C_LADDERS,
        "basis": f"proxy من مسار الإنتاج (ladder={ladder!r}) — نفس تصنيف business_dossier.py's segment_proxy، وليس درجة رقمية دقيقة",
    }


def _diversification_impact(portfolio_class, class_counts):
    """Real, evidence-based: marginal diversification value is inversely
    related to how many OTHER real ACCEPTED opportunities already share
    this exact class — never a fabricated 'synergy' number."""
    sibling_count = max(0, class_counts.get(portfolio_class, 0) - 1)
    if sibling_count == 0:
        return {"impact": "high", "sibling_count": 0, "note": "أول فرصة حقيقية مقبولة في هذه الفئة — يزيد تنوّع المحفظة فعلياً"}
    return {
        "impact": "low" if sibling_count >= 3 else "medium",
        "sibling_count": sibling_count,
        "note": f"{sibling_count} فرصة حقيقية أخرى مقبولة فعلاً في نفس الفئة — قيمة تنويع تهميشية أقل",
    }


def build_portfolio_entry(niche, decisions_path=None, board_path=None, alerts_path=None,
                           reopen_log_path=None, evidence_path=None, class_counts=None):
    """Real, unified Portfolio Engine entry for one niche — reuses
    investment_pipeline.build_investment_pipeline_entry() directly for
    every already-real field, adds only the genuinely new metrics this
    directive named. Returns None (never fabricated) for a niche with
    no real decision at all."""
    import factory_orchestrator as fo
    import investment_pipeline
    import market_memory
    from revenue_pipeline import plan as plan_module

    decision = fo.find_decision(niche, decisions_path=decisions_path)
    if decision is None:
        return None

    ip_entry = investment_pipeline.build_investment_pipeline_entry(
        niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
    )
    portfolio_class = classify_portfolio_class(decision)

    market_memory_profile = market_memory.niche_commercial_profile(niche, evidence_path=evidence_path)
    cost_result = plan_module.estimate_production_cost()
    reusability = ((decision.get("evaluation_snapshot") or {}).get("components") or {}).get("reusability")

    return {
        "niche": niche,
        "portfolio_class": portfolio_class,
        "portfolio_class_family_status": class_family_status(portfolio_class),
        "investment_pipeline_entry": ip_entry,
        "expected_annual_revenue": {
            "value": market_memory_profile.get("total_revenue") if market_memory_profile else None,
            "basis": "إيراد حقيقي مُحقَّق حتى الآن — وليس توقّعاً سنوياً؛ لا نموذج تنبؤ حقيقي في هذا المصنع (نفس انضباط growth_engine.growth_forecast())",
        },
        "expected_monthly_recurring_revenue": {
            "value": 0,
            "reason": "صفر مبيعة اشتراك حقيقية حدثت في هذا المصنع على الإطلاق — القدرة البنيوية حقيقية (Paddle billing_cycle) لكن غير مُستخدَمة (ADR-108)",
        },
        "development_cost": cost_result,
        "time_to_market": {"value": None, "reason": "لا نموذج تتبّع مدة تطوير تاريخي حقيقي في هذا المصنع بعد"},
        "country_priority": {"value": None, "reason": "مؤجَّل بوعي — نفس القرار المؤكَّد 6 مرات اليوم (ADR-103/106/108/110/111/112)"},
        "china_suitability": {"value": None, "reason": "مؤجَّل بوعي — نفس السبب أعلاه، لا موصّل بيانات صيني حقيقي"},
        "b2b_b2c": _b2b_b2c_signal(decision.get("ladder")),
        "reusability_inside_company": reusability,
        "portfolio_diversification_impact": _diversification_impact(portfolio_class, class_counts or {}),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def _now_next_later_reject_bucket(niche, scheduling_buckets):
    """Reuses scheduler.py's own real, evidence-gated classification
    directly — never a second classifier. run_now/accelerate -> NOW
    (both are real 'act on this now' signals), wait -> NEXT, stop ->
    LATER (temporary red flag), cancel -> REJECT."""
    remap = {"run_now": "NOW", "accelerate": "NOW", "wait": "NEXT", "stop": "LATER", "cancel": "REJECT"}
    for bucket_name, items in scheduling_buckets.items():
        if any(item["niche"] == niche for item in items):
            return remap.get(bucket_name, "NEXT")
    return "NEXT"


def build_portfolio_report(decisions_path=None, board_path=None, alerts_path=None,
                            reopen_log_path=None, evidence_path=None, timeline_path=None, outcomes_path=None):
    """The real, whole-factory portfolio: every real ACCEPTED
    opportunity classified into a real portfolio class and a real
    NOW/NEXT/LATER/REJECT bucket, ordered within each bucket by (class
    priority, real Priority Score) — a real, deterministic tie-break
    over already-real evidence, never a new evidence claim.

    Top 100 worldwide / Top 25 enterprise / Top 25 recurring revenue —
    real, ranked slices over what exists today (this factory has far
    fewer than 100/25 real opportunities right now; the real, honest
    count is reported, never padded). Top 50 China: always honestly
    empty — same deferred reason as every other China ask today."""
    import scheduler
    import factory_orchestrator as fo

    scheduling = scheduler.decide_next_actions(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    accepted_niches = [
        item["niche"]
        for bucket in scheduling["buckets"].values()
        for item in bucket
    ]

    provisional = []
    for niche in accepted_niches:
        decision = fo.find_decision(niche, decisions_path=decisions_path)
        provisional.append((niche, classify_portfolio_class(decision) if decision else "Unclassified"))
    class_counts = {}
    for _, cls in provisional:
        class_counts[cls] = class_counts.get(cls, 0) + 1

    entries = []
    for niche, _ in provisional:
        entry = build_portfolio_entry(
            niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path, class_counts=class_counts,
        )
        if entry is None:
            continue
        entry["execution_bucket"] = _now_next_later_reject_bucket(niche, scheduling["buckets"])
        entries.append(entry)

    def _sort_key(e):
        cls = e["portfolio_class"]
        class_rank = _CLASS_PRIORITY_ORDER.index(cls) if cls in _CLASS_PRIORITY_ORDER else len(_CLASS_PRIORITY_ORDER)
        priority = ((e["investment_pipeline_entry"] or {}).get("commercial_score")) or -1
        return (class_rank, -priority)
    entries.sort(key=_sort_key)

    enterprise_classes = {"Enterprise Automation", "AI APIs", "Premium SaaS"}
    enterprise_entries = [e for e in entries if e["portfolio_class"] in enterprise_classes]

    def _recurring_score(e):
        ip = e["investment_pipeline_entry"] or {}
        dims = ip.get("ranking_dimensions") or {}
        rec = dims.get("recurring_revenue_potential")
        return rec if isinstance(rec, (int, float)) else -1
    recurring_entries = sorted(entries, key=_recurring_score, reverse=True)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_real_opportunities": len(entries),
        "top_100_worldwide": entries[:100],
        "top_25_enterprise": enterprise_entries[:25],
        "top_25_recurring_revenue": recurring_entries[:25],
        "top_50_china": {"entries": [], "reason": "مؤجَّل بوعي — لا موصّل بيانات صيني حقيقي (نفس القرار المؤكَّد 6 مرات اليوم)"},
    }
