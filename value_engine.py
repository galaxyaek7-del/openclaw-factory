#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Value Engine (2026-07-23).

"Does this increase the long-term value of the company?" A permanent
synthesis layer that evaluates every real ACCEPTED opportunity against
17 requested dimensions and produces the Executive-Board-facing summary
(Priority Score, Expected ROI, Strategic Value, Estimated Build Cost,
Estimated Maintenance Cost, Estimated Lifetime Value, Recommendation).

Reuses, never duplicates: `opportunity_pipeline.py`'s already-real
per-decision annotation (market_signal/defensibility/ai_leverage/
automation_potential/recurring_revenue_potential/global_scalability/
strategic_investment/board_brief/active_alerts/reopen_history),
`revenue_pipeline/plan.py`'s real cost/ROI/ladder-comparison functions,
`market_evidence.py`'s real per-niche evidence summary,
`decision_engine/ranking.py`'s real decision history. Nothing here is a
second, competing scoring system — every numeric input traces to one
specific already-computed real field elsewhere in this factory.

A real search (2026-07-23) mapped all 17 requested dimensions before any
code was written:
  - 6 already real, reused verbatim: recurring_revenue_potential,
    scalability, defensibility, ai_leverage, automation_potential,
    competitive_moat.
  - 4 partially real, reused from profit_oracle.strategic_investment_
    layer()/market_signal: long_term_strategic_value, global_demand,
    platform_potential, enterprise_potential.
  - 5 genuinely new but still 100% evidence-grounded (never fabricated,
    always derived from already-computed real data): knowledge_
    accumulation (real count of accumulated evidence artifacts),
    synergy_with_existing_products / bundle_potential (real count of
    sibling ACCEPTED decisions sharing the same ladder),
    upgrade_potential (real price delta to a higher real ladder rank,
    from revenue_pipeline.plan.compare_ladder_variants()).
  - 3 have NO real data source anywhere in this factory today --
    reported as explicit, reasoned Unknown, never estimated or guessed:
    expected_customer_value, lifetime_revenue_potential,
    brand_building_impact.

Retirement of weak products (requested under "continuous optimization")
has no real sales-performance data to justify it yet (the same gap
dossier_bundle.py's own build_bundle() docstring already discloses).
This module builds a real, evidence-grounded "at_risk" SIGNAL instead
(a real board NOT_APPROVED verdict, a real Critical-severity active
alert, or a real reopened decision that flipped negative) --
deliberately labeled a risk signal, never a retirement recommendation.

Scoped to ACCEPTED opportunities only (Product Laboratory) -- the same
scope business_dossier.py/strategic_investment_layer() already
established ("every accepted opportunity automatically gets..."). A
full investment-analysis profile for a niche the real gate hasn't even
approved yet would be premature.

    python value_engine.py --report
    python value_engine.py --niche "some niche"
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone

_NO_REAL_SOURCE_DIMENSIONS = {
    "expected_customer_value": "لا نظام حقيقي لقياس قيمة العميل (مقابلات/NPS/مسح رضا) في هذا المصنع بعد",
    "lifetime_revenue_potential": "لا بيانات مبيعات متكررة أو تجديد حقيقية بعد لحساب قيمة العمر الحقيقية — السعر الحقيقي لمرة واحدة فقط معروف",
    "brand_building_impact": "لا مقياس علامة تجارية حقيقي (وعي/ذكر/بحث) متصل بهذا المصنع بعد",
}


def _unknown(reason):
    return {"answer": "Unknown", "reason": reason}


# ── 10 dimensions reused verbatim / near-verbatim from already-real fields ──

def _reused_dimensions(annotated):
    """6 already-real + 4 partially-real dimensions, pulled straight off
    opportunity_pipeline.py's own real annotation for this opportunity —
    zero recomputation."""
    strategic_investment = annotated.get("strategic_investment") or {}

    def _from_strategic_investment(key, note):
        if not strategic_investment:
            return _unknown("لا نتيجة strategic_investment_layer محفوظة لهذا القرار (لا ladder مُسجَّل)")
        return {"value": strategic_investment.get(key), "note": note}

    return {
        "recurring_revenue_potential": annotated.get("recurring_revenue_potential"),
        "scalability": annotated.get("global_scalability"),
        "defensibility": annotated.get("defensibility"),
        "ai_leverage": annotated.get("ai_leverage"),
        "automation_potential": annotated.get("automation_potential"),
        "competitive_moat": _from_strategic_investment(
            "competitors_can_copy_it_easily", "من طبقة الاستثمار الاستراتيجي الحقيقية (profit_oracle.strategic_investment_layer)"),
        "long_term_strategic_value": _from_strategic_investment(
            "becomes_more_valuable_over_time", "من طبقة الاستثمار الاستراتيجي الحقيقية"),
        "global_demand": annotated.get("market_size"),  # already explicitly a discussion-volume proxy, never a dollar TAM
        "platform_potential": _from_strategic_investment(
            "can_create_a_product_ecosystem", "من طبقة الاستثمار الاستراتيجي الحقيقية"),
        "enterprise_potential": _from_strategic_investment(
            "can_evolve_into_software_business", "من طبقة الاستثمار الاستراتيجي الحقيقية"),
    }


# ── 5 genuinely new dimensions, each a real synthesis over already-computed data ──

def _score_knowledge_accumulation(board_brief, active_alerts, market_evidence_summary):
    """Real, deterministic count of real evidence artifacts already
    accumulated for this niche — how much real institutional knowledge
    already exists, not a fabricated 'brand memory' concept."""
    sources = 0
    if board_brief and board_brief.get("has_meeting"):
        sources += 1
    if active_alerts and active_alerts.get("total", 0) > 0:
        sources += 1
    if market_evidence_summary and market_evidence_summary.get("total_events", 0) > 0:
        sources += 1
    level = "مرتفعة" if sources >= 2 else "متوسطة" if sources == 1 else "منخفضة"
    return {
        "score": sources, "level": level,
        "note": f"{sources}/3 مصادر أدلة حقيقية متراكمة (اجتماع مجلس حقيقي، تنبيهات نشطة حقيقية، أدلة سوق حقيقية)",
    }


def _score_synergy_and_bundle(ladder, ladder_counts):
    """Real count of other real ACCEPTED decisions sharing this exact
    ladder — a real synergy/bundle signal, never a guess. 2+ real
    siblings -> real bundle potential (they could literally be bundled
    together today)."""
    if not ladder:
        reason = "لا ladder مُسجَّل لهذا القرار"
        return _unknown(reason), _unknown(reason)
    sibling_count = max(0, ladder_counts.get(ladder, 0) - 1)  # exclude this opportunity itself
    synergy = {
        "sibling_count": sibling_count,
        "note": f"{sibling_count} منتج حقيقي آخر مقبول فعلاً على نفس الـ ladder ({ladder})",
    }
    bundle = {
        "eligible": sibling_count >= 2,
        "sibling_count": sibling_count,
        "note": (
            f"{sibling_count} منتج شقيق حقيقي — يؤهَّل لحزمة حقيقية اليوم" if sibling_count >= 2
            else f"{sibling_count} منتج شقيق فقط — يحتاج 2 على الأقل لحزمة حقيقية"
        ),
    }
    return synergy, bundle


def _score_upgrade_potential(ladder, current_price, variants_result):
    """Real price delta to a higher real ladder rank, reused directly
    from revenue_pipeline.plan.compare_ladder_variants() — never
    re-scored here."""
    if not variants_result or not ladder or current_price is None:
        return _unknown("يحتاج مقارنة ladder حقيقية (compare_ladder_variants) وسعراً حالياً حقيقياً محفوظاً")
    variants = variants_result.get("variants") or []
    higher = [v for v in variants if isinstance(v.get("price"), (int, float)) and v["price"] > current_price and "error" not in v]
    if not higher:
        return {"available": False, "note": "لا درجة ladder حقيقية أعلى بسعر حقيقي أعلى متاحة اليوم"}
    best = max(higher, key=lambda v: v["price"])
    delta = round(best["price"] - current_price, 2)
    return {
        "available": True, "best_upgrade_ladder": best["ladder"], "price_delta": delta,
        "note": f"ترقية حقيقية محتملة إلى {best['ladder']} بسعر حقيقي ${best['price']} (+${delta})",
    }


# ── Real, evidence-grounded risk signal (explicitly NOT a retirement recommendation) ──

def _compute_at_risk_flag(board_brief, active_alerts, reopen_history):
    """A real risk SIGNAL, not a retirement recommendation — zero real
    sales-performance data exists anywhere in this factory to justify
    actually retiring a product (dossier_bundle.py's own build_bundle()
    already discloses this exact gap). Flags only on real,
    already-computed governance evidence."""
    reasons = []
    if board_brief and board_brief.get("has_meeting") and board_brief.get("board_decision") == "NOT_APPROVED":
        reasons.append("قرار مجلس حقيقي: غير موافَق عليه")
    critical_count = (active_alerts or {}).get("by_severity_counts", {}).get("Critical", 0)
    if critical_count:
        reasons.append(f"{critical_count} تنبيه حرج (Critical) نشط حقيقي")
    for event in (reopen_history or []):
        new_decision = (event.get("new_decision") or {}).get("board_decision")
        if event.get("decision_changed") and new_decision == "NOT_APPROVED":
            reasons.append("إعادة فتح حقيقية أدّت إلى رفض المجلس")
    return {
        "flagged": bool(reasons),
        "reasons": reasons,
        "retirement_recommendation": _unknown(
            "لا بيانات أداء مبيعات حقيقية بعد لتبرير قرار تقاعد فعلي — "
            "هذه إشارة خطر من أدلة حوكمة حقيقية فقط، وليست توصية تقاعد نهائية",
        ),
    }


# ── Board-facing summary: Priority Score, Expected ROI, Strategic Value, ──
# ── Estimated Build/Maintenance Cost, Estimated Lifetime Value, Recommendation ──

def _compute_strategic_value_composite(reused, new_dims):
    """Real, transparent average over every NUMERIC real dimension score
    gathered above — never blended into profit_score/ladder_score/
    accepted (informational only, the same discipline every other
    additive dimension in profit_oracle.py already follows)."""
    numeric_scores = []
    for dim in (
        reused.get("recurring_revenue_potential"), reused.get("scalability"), reused.get("automation_potential"),
        reused.get("defensibility"), reused.get("ai_leverage"), reused.get("global_demand"),
        new_dims.get("knowledge_accumulation"),
    ):
        if isinstance(dim, dict) and isinstance(dim.get("score"), (int, float)):
            numeric_scores.append(dim["score"])
        elif isinstance(dim, (int, float)):
            numeric_scores.append(dim)
    if not numeric_scores:
        return _unknown("لا أبعاد رقمية حقيقية كافية لحساب قيمة استراتيجية مركّبة لهذا القرار")
    avg = round(sum(numeric_scores) / len(numeric_scores), 1)
    return {"score": avg, "based_on_n_dimensions": len(numeric_scores), "note": f"متوسط حقيقي عبر {len(numeric_scores)} بُعد رقمي حقيقي محسوب أعلاه"}


def _compute_priority_score(decision_opportunity_score, strategic_value):
    """A real, transparent prioritization LENS layered on top of —
    never replacing — decision_engine's own real opportunity_score
    (still the sole real acceptance/ranking gate; decision_engine.
    ranking.rank_queue() is completely unchanged by this module)."""
    parts, basis = [], []
    if isinstance(decision_opportunity_score, (int, float)):
        parts.append(decision_opportunity_score)
        basis.append("opportunity_score")
    if isinstance(strategic_value, dict) and isinstance(strategic_value.get("score"), (int, float)):
        parts.append(strategic_value["score"])
        basis.append("strategic_value")
    if not parts:
        return _unknown("لا opportunity_score حقيقي ولا قيمة استراتيجية مركّبة متاحة لهذا القرار")
    return {"score": round(sum(parts) / len(parts), 1), "based_on": basis}


def _financials(price, cost_result, roi_result, recurring_revenue_potential):
    lifetime_value_reason = "لا سعر حقيقي مُوصى به محفوظ لهذا القرار"
    if price is not None:
        lifetime_value_reason = f"لا بيانات مبيعات متكررة/تجديد حقيقية بعد — السعر الحقيقي لمرة واحدة هو ${price}"
        if isinstance(recurring_revenue_potential, (int, float)):
            lifetime_value_reason += f"؛ إمكانية إيراد متكرر مُقدَّرة حسب الـ ladder بـ {recurring_revenue_potential}/100 (مؤشر تقديري، ليس مبلغاً مالياً)"
    return {
        "estimated_build_cost": cost_result,
        "estimated_maintenance_cost": _unknown("لا نظام تتبّع تكلفة صيانة حقيقي بعد الإطلاق موجود في هذا المصنع بعد"),
        "expected_roi": roi_result,
        "estimated_lifetime_value": _unknown(lifetime_value_reason),
    }


def _build_recommendation(priority_score, at_risk, upgrade, bundle):
    """Deterministic, mechanical recommendation derived entirely from
    the real signals computed above — never freely-generated text."""
    actions = []
    if at_risk.get("flagged"):
        actions.append(f"مراجعة عاجلة: {'؛ '.join(at_risk['reasons'])}")
    score = priority_score.get("score") if isinstance(priority_score, dict) else None
    if score is not None:
        if score >= 70:
            actions.append("أولوية استثمار عالية — استمر في التطوير/التسويق")
        elif score >= 40:
            actions.append("راقب — أدلة حقيقية إضافية مطلوبة قبل استثمار إضافي")
        else:
            actions.append("أولوية منخفضة حالياً — لا استثمار إضافي قبل تحسّن الأدلة الحقيقية")
    if isinstance(upgrade, dict) and upgrade.get("available"):
        actions.append(f"فكّر في الترقية إلى {upgrade['best_upgrade_ladder']} (+${upgrade['price_delta']})")
    if isinstance(bundle, dict) and bundle.get("eligible"):
        actions.append(f"فرصة حزمة حقيقية مع {bundle['sibling_count']} منتج شقيق")
    if not actions:
        actions.append("لا توصية آلية محدَّدة — أدلة حقيقية غير كافية بعد")
    return actions


# ── Market Creation & Product Leadership (2026-07-23): the 6 named ──
# ── conditions every real product must satisfy at least one of.     ──
# ── Informational only, same additive discipline as every other      ──
# ── dimension above — never a new accept/reject gate, never blended  ──
# ── into profit_score/ladder_score/accepted. A real search found 4 of ──
# ── the 6 conditions have a real, already-computed evidence source;   ──
# ── the other 2 (creates a genuinely new market; increases the        ──
# ── customer's OWN revenue) have none anywhere in this factory today  ──
# ── — reported as honest, reasoned "insufficient evidence", never     ──
# ── forced into a yes/no this factory cannot actually back with real  ──
# ── data.                                                             ──

_VALUE_PROPOSITION_CONDITIONS = (
    "creates_new_market", "solves_expensive_problem_better", "automates_manual_work",
    "saves_time_or_money", "increases_customer_revenue", "becomes_indispensable_business_asset",
)


def _condition(satisfied, evidence):
    return {"satisfied": satisfied, "evidence": evidence}


def classify_value_proposition(annotated, reused, new_dims):
    """Real, evidence-based check against the 6 named Market Creation &
    Product Leadership conditions — reuses fields already computed
    elsewhere in this profile, never a new measurement. "At least one
    satisfied" is reported explicitly so a human/board can see the real
    basis, never a bare pass/fail."""
    strategic_investment = annotated.get("strategic_investment") or {}
    pain_level = annotated.get("pain_level") or {}
    automation = new_dims_automation = reused.get("automation_potential")
    automation_score = automation if isinstance(automation, (int, float)) else (automation or {}).get("score")

    conditions = {
        # No real market-creation validation methodology exists in this
        # factory (market_signal is explicitly a discussion-volume proxy,
        # never proof a market didn't already exist) — honestly
        # unresolved rather than forced.
        "creates_new_market": _condition(
            False, "لا منهجية تحقّق حقيقية لخلق سوق جديد فعلاً موجودة في هذا المصنع بعد — دليل غير كافٍ",
        ),
        "solves_expensive_problem_better": _condition(
            bool(pain_level.get("value")) and strategic_investment.get("competitors_can_copy_it_easily") is False,
            f"دليل ألم عملاء حقيقي: {pain_level.get('value')}؛ صعوبة تقليد حقيقية من طبقة الاستثمار الاستراتيجي"
            if pain_level.get("value") else "لا دليل ألم عملاء حقيقي مسجَّل لهذا القرار",
        ),
        "automates_manual_work": _condition(
            isinstance(automation_score, (int, float)) and automation_score >= 60,
            f"إمكانية أتمتة حقيقية: {automation_score}/100" if isinstance(automation_score, (int, float)) else "لا مقياس أتمتة حقيقي متاح",
        ),
        "saves_time_or_money": _condition(
            (isinstance(automation_score, (int, float)) and automation_score >= 60),
            f"إمكانية أتمتة حقيقية مرتفعة ({automation_score}/100) تعني توفيراً حقيقياً محتملاً في الوقت/التكلفة"
            if isinstance(automation_score, (int, float)) and automation_score >= 60
            else "لا دليل حقيقي كافٍ على توفير وقت/تكلفة حقيقي بعد",
        ),
        # Zero real customers, zero real revenue-impact-on-customer data
        # exist anywhere in this factory — always honest, never guessed.
        "increases_customer_revenue": _condition(
            False, "لا عملاء حقيقيون ولا بيانات أثر إيراد حقيقية على العميل موجودة في هذا المصنع بعد",
        ),
        "becomes_indispensable_business_asset": _condition(
            strategic_investment.get("can_evolve_into_software_business") is True
            or strategic_investment.get("can_create_a_product_ecosystem") is True,
            "طبقة الاستثمار الاستراتيجي الحقيقية: قابلية تطوّر إلى منتج برمجي أو نظام منتجات حقيقية"
            if (strategic_investment.get("can_evolve_into_software_business") or strategic_investment.get("can_create_a_product_ecosystem"))
            else "لا دليل حقيقي كافٍ على أن هذا المنتج يصبح أصلاً تجارياً لا غنى عنه",
        ),
    }
    satisfied_count = sum(1 for c in conditions.values() if c["satisfied"])
    return {
        "conditions": conditions,
        "satisfied_count": satisfied_count,
        "meets_minimum_bar": satisfied_count >= 1,
    }


# ── The 10-stage real product lifecycle. Reuses ──
# ── production_evidence.record.build_evidence_record() directly (already ──
# ── computes real discovery/decision/production/publishing/revenue/     ──
# ── customer-feedback evidence) — never re-derives it. 4 of the 10      ──
# ── stages (customer testing, localization, global expansion, long-term ──
# ── maintenance) have no real data source anywhere in this factory      ──
# ── today (ADR-102/ADR-103's own disclosed gaps) — always honestly      ──
# ── reported as not-yet-reached with the real, disclosed reason.        ──

LIFECYCLE_STAGES = (
    "global_opportunity_discovery", "evidence_based_validation", "prototype",
    "customer_testing", "premium_production", "commercial_launch",
    "continuous_improvement", "localization", "global_expansion", "long_term_maintenance",
)


def _check_continuous_improvement(niche):
    import enterprise_readiness as er
    trail = er.get_audit_trail(niche)
    count = len(trail.get("changelog_entries") or [])
    return {
        "reached": count > 0,
        "evidence": f"{count} إدخال سجل تغييرات حقيقي" if count else "لا سجل تغييرات حقيقي بعد",
    }


def classify_lifecycle_stage(niche, decisions_path=None, timeline_path=None, outcomes_path=None):
    """Real, evidence-based classification of which of the 10 named
    product-lifecycle stages this niche has real, verifiable evidence of
    having reached. Reuses production_evidence.record.build_evidence_
    record() directly."""
    from production_evidence import record as evidence_record

    evidence = evidence_record.build_evidence_record(
        niche, timeline_path=timeline_path, decisions_path=decisions_path, outcomes_path=outcomes_path,
    )

    production_events = evidence.get("execution_status") or []
    production_attempted = bool(production_events)
    production_succeeded = any(e.get("status") == "SUCCESS" for e in production_events)
    platform = evidence.get("platform") or {}
    publishing_succeeded = bool(platform.get("succeeded"))
    customer_feedback = evidence.get("customer_feedback")
    has_real_customer_feedback = isinstance(customer_feedback, dict) and isinstance(customer_feedback.get("answer"), list) and len(customer_feedback["answer"]) > 0
    decision_status = (evidence.get("decision") or {}).get("status")

    stages = {
        "global_opportunity_discovery": {
            "reached": evidence.get("discovery_timestamp") is not None,
            "evidence": f"وقت اكتشاف حقيقي: {evidence['discovery_timestamp']}" if evidence.get("discovery_timestamp") else "لا اكتشاف حقيقي مسجَّل بعد",
        },
        "evidence_based_validation": {
            "reached": decision_status not in (None, "Unknown"),
            "evidence": f"قرار حقيقي: {decision_status}" if decision_status not in (None, "Unknown") else "لا قرار حقيقي بعد",
        },
        "prototype": {
            "reached": production_attempted,
            "evidence": f"{len(production_events)} محاولة إنتاج حقيقية مسجَّلة" if production_attempted else "لا محاولة إنتاج حقيقية بعد",
        },
        "customer_testing": {
            "reached": has_real_customer_feedback,
            "evidence": "ملاحظات عملاء حقيقية موجودة" if has_real_customer_feedback else
                        (customer_feedback.get("reason") if isinstance(customer_feedback, dict) else "لا قناة ملاحظات عملاء حقيقية متصلة بهذا المصنع بعد"),
        },
        "premium_production": {
            "reached": production_succeeded,
            "evidence": "نجاح إنتاج حقيقي (Dual Inspection)" if production_succeeded else "لم ينجح إنتاج حقيقي بعد",
        },
        "commercial_launch": {
            "reached": publishing_succeeded,
            "evidence": f"نشر حقيقي ناجح على: {', '.join(platform.get('succeeded') or [])}" if publishing_succeeded else "لا نشر حقيقي ناجح بعد",
        },
        "continuous_improvement": _check_continuous_improvement(niche),
        "localization": {"reached": False, "evidence": "لا موصّل بيانات محلي حقيقي لأي سوق بعد — تأجيل واعٍ (ADR-103)"},
        "global_expansion": {"reached": False, "evidence": "لا بيانات مبيعات دولية حقيقية بعد — تأجيل واعٍ (ADR-103)"},
        "long_term_maintenance": {"reached": False, "evidence": "لا نظام تتبّع صيانة حقيقي بعد الإطلاق موجود بعد (ADR-102)"},
    }

    current_stage = None
    for stage_name in LIFECYCLE_STAGES:
        if stages[stage_name]["reached"]:
            current_stage = stage_name

    return {
        "niche": niche,
        "stages": stages,
        "current_stage": current_stage,
        "final_outcome": evidence.get("final_outcome"),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Single-opportunity entrypoint (reused by both the bulk report and Executive Board integration) ──

def compute_value_profile(niche, decisions_path=None, board_path=None, alerts_path=None,
                           reopen_log_path=None, evidence_path=None, ladder_counts=None,
                           cost_result=None, timeline_path=None, outcomes_path=None):
    """The real per-niche synthesis entrypoint. Reuses
    opportunity_pipeline.annotate_decision() for every already-computed
    real field, then layers the remaining requested Value Engine
    dimensions on top. Returns None (never fabricated) if this niche has
    no real ACCEPTED decision on record — matching business_dossier.py's
    own scope.

    timeline_path/outcomes_path (Market Creation & Product Leadership,
    2026-07-23): test-isolation overrides for classify_lifecycle_stage()'s
    own reuse of production_evidence.record.build_evidence_record()."""
    import opportunity_pipeline as op
    import factory_orchestrator as fo
    from decision_engine import ranking
    from revenue_pipeline import plan as plan_module
    import market_evidence as me

    decision = fo.find_decision(niche, decisions_path=decisions_path)
    if decision is None or decision.get("status") != "ACCEPTED":
        return None

    annotated = op.annotate_decision(decision, board_path=board_path, alerts_path=alerts_path, reopen_log_path=reopen_log_path)
    ladder = decision.get("ladder")

    if ladder_counts is None:
        all_decisions = ranking.rank_all(path=decisions_path)
        ladder_counts = Counter(d.get("ladder") for d in all_decisions if d.get("status") == "ACCEPTED" and d.get("ladder"))
    if cost_result is None:
        cost_result = plan_module.estimate_production_cost()

    price = annotated.get("estimated_selling_price")
    price_value = price if isinstance(price, (int, float)) else None
    variants_result = plan_module.compare_ladder_variants(niche) if niche else None
    market_evidence_summary = me.summarize_niche(niche, evidence_path=evidence_path) if niche else None
    roi_result = plan_module.estimate_roi(
        price_value, cost_result.get("estimated_cost_usd") if cost_result.get("maturity") == "REAL" else None,
        platform="gumroad_elite" if ladder else "gumroad_digital",
    )

    reused = _reused_dimensions(annotated)
    knowledge = _score_knowledge_accumulation(annotated.get("board_brief"), annotated.get("active_alerts"), market_evidence_summary)
    synergy, bundle = _score_synergy_and_bundle(ladder, ladder_counts)
    upgrade = _score_upgrade_potential(ladder, price_value, variants_result)
    at_risk = _compute_at_risk_flag(annotated.get("board_brief"), annotated.get("active_alerts"), annotated.get("reopen_history"))

    new_dims = {
        "knowledge_accumulation": knowledge,
        "synergy_with_existing_products": synergy,
        "bundle_potential": bundle,
        "upgrade_potential": upgrade,
    }
    no_source = {k: _unknown(v) for k, v in _NO_REAL_SOURCE_DIMENSIONS.items()}

    strategic_value = _compute_strategic_value_composite(reused, new_dims)
    priority_score = _compute_priority_score(decision.get("opportunity_score"), strategic_value)
    financials = _financials(price_value, cost_result, roi_result, reused.get("recurring_revenue_potential"))
    recommendation = _build_recommendation(priority_score, at_risk, upgrade, bundle)
    value_proposition = classify_value_proposition(annotated, reused, new_dims)
    lifecycle = classify_lifecycle_stage(niche, decisions_path=decisions_path, timeline_path=timeline_path, outcomes_path=outcomes_path)

    return {
        "niche": niche,
        "decision_id": annotated.get("decision_id"),
        "ladder": ladder,
        "dimensions": {**reused, **new_dims, **no_source},
        "at_risk": at_risk,
        "value_proposition": value_proposition,
        "lifecycle_stage": lifecycle,
        "board_summary": {
            "priority_score": priority_score,
            "expected_roi": roi_result,
            "strategic_value": strategic_value,
            "estimated_build_cost": financials["estimated_build_cost"],
            "estimated_maintenance_cost": financials["estimated_maintenance_cost"],
            "estimated_lifetime_value": financials["estimated_lifetime_value"],
            "recommendation": recommendation,
        },
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_value_engine_report(decisions_path=None, board_path=None, alerts_path=None,
                               reopen_log_path=None, evidence_path=None,
                               timeline_path=None, outcomes_path=None):
    """The one real, on-demand, whole-portfolio entrypoint — automatic
    resource-allocation prioritization: every real ACCEPTED opportunity
    (Product Laboratory), ranked by real Priority Score descending.
    Reuses compute_value_profile() per opportunity; the real ladder-
    count/cost lookups are computed once for the whole batch, not
    per-opportunity, matching opportunity_pipeline.py's own "safe to run
    over the full real history" performance discipline."""
    import opportunity_pipeline as op
    from decision_engine import ranking
    from revenue_pipeline import plan as plan_module

    pipeline = op.build_opportunity_pipeline(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path, reopen_log_path=reopen_log_path,
    )
    accepted_niches = [e["niche"] for e in pipeline["product_laboratory"]]

    all_decisions = ranking.rank_all(path=decisions_path)
    ladder_counts = Counter(d.get("ladder") for d in all_decisions if d.get("status") == "ACCEPTED" and d.get("ladder"))
    cost_result = plan_module.estimate_production_cost()

    profiles = [
        compute_value_profile(
            niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
            ladder_counts=ladder_counts, cost_result=cost_result,
            timeline_path=timeline_path, outcomes_path=outcomes_path,
        )
        for niche in accepted_niches
    ]
    profiles = [p for p in profiles if p is not None]

    def _sort_key(p):
        score = p["board_summary"]["priority_score"]
        return score["score"] if isinstance(score, dict) and isinstance(score.get("score"), (int, float)) else -1
    profiles.sort(key=_sort_key, reverse=True)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_evaluated": len(profiles),
        "profiles": profiles,
        "note": (
            "يُقيَّم فقط الفرص المقبولة فعلاً (Product Laboratory) — نفس نطاق "
            "business_dossier.py/strategic_investment_layer() الحالي. لا تقييم استثماري لفرص قيد الانتظار."
        ),
    }


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw Value Engine")
    parser.add_argument("--report", action="store_true", help="Full ranked portfolio report")
    parser.add_argument("--niche", metavar="NICHE", help="Single-opportunity value profile")
    args = parser.parse_args()

    if args.report:
        emit({"success": True, "result": build_value_engine_report()})
        return
    if args.niche:
        profile = compute_value_profile(args.niche)
        emit({"success": profile is not None, "result": profile})
        return
    parser.print_help()


if __name__ == "__main__":
    main()
