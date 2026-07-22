"""
Business Dossier (Autonomous Digital Venture Studio, 2026-07-22).

For an opportunity already scored by profit_oracle.ladder_opportunity_score(),
synthesizes the 8 named sections the founder asked every accepted
opportunity to carry -- Business Thesis, Customer Profile, Product
Architecture, MVP Roadmap, Revenue Model, Pricing Strategy, Competitive
Moat, Long-Term Expansion Strategy -- as a PURE, DETERMINISTIC TEMPLATE
over already-real data (ladder_opportunity_score(), strategic_investment_
layer(), product_families.registry, revenue_pipeline.plan, and real
customer-pain evidence when available). Deliberately does NOT call an LLM
to compose narrative prose here -- every sentence traces back to one
specific real field, which an LLM-generated paragraph could not
guarantee, and this factory's own standing instruction is "no fabricated
numbers... evidence first."

Two sections are structurally, permanently incapable of a fully
confident answer without real data this factory doesn't have, and say so
honestly rather than inventing detail:
  - Customer Profile: this factory has no real demographic/persona data
    source anywhere (confirmed repeatedly). What IS real: aggregate
    counts of real GitHub Issues/HN/Stack Overflow evidence (when
    gathered) and the real ladder-based B2B/consumer proxy. Never a
    fabricated persona ("Sarah, 34, marketing manager...").
  - MVP Roadmap: no real dev-time-estimation model exists (confirmed
    repeatedly -- estimate_production_cost() measures real dollars, not
    calendar time). Reports a real, evidence-based sequence of
    buildable-today vs. blocked-on-infrastructure steps, never an
    invented timeline ("6 weeks", "Q3 2026").
"""

from product_families import registry as product_families_registry
from product_families.mapping import ALL_PRODUCT_FAMILIES, resolve_product_family

import profit_oracle
from revenue_pipeline.plan import estimate_pre_acceptance_roi

_LADDER_PRICE_BAND_TO_ECONOMICS_PLATFORM = {
    "book": "gumroad_digital", "premium": "gumroad_premium", "elite": "gumroad_elite",
}

_LADDER_DISPLAY_NAMES = {
    "ai_saas": "AI SaaS", "b2b_systems": "B2B Systems", "automation_tools": "Automation Tools",
    "reusable_assets": "Reusable Assets", "educational": "Educational", "kdp_books": "KDP Books",
}


def _business_thesis(ladder_result, si):
    niche = ladder_result.get("niche")
    ladder = ladder_result.get("ladder")
    ladder_name = _LADDER_DISPLAY_NAMES.get(ladder, ladder)
    price = ladder_result.get("price")
    score = ladder_result.get("ladder_score")
    market_signal = ladder_result.get("market_signal") or {}
    verdict_bits = []
    for key, label in (
        ("can_become_premium_digital_asset", "أصل رقمي مميز"),
        ("can_evolve_into_software_business", "عمل برمجي"),
        ("can_dominate_a_narrow_market", "سيطرة على سوق ضيق"),
    ):
        answer = si.get(key, {}).get("answer")
        if answer:
            verdict_bits.append(f"{label}: {answer}")
    return {
        "text": (
            f"\"{niche}\" -- مسار {ladder_name}، درجة حقيقية {score}/100، سعر مُوصى به ${price}. "
            f"حجم نقاش حقيقي: {market_signal.get('note', 'غير معروف')}. "
            f"{'؛ '.join(verdict_bits) if verdict_bits else 'لا أحكام استراتيجية كافية بعد'}."
        ),
        "grounded_in": "ladder_opportunity_score() + strategic_investment_layer() -- كل رقم هنا حقيقي، لا نص إنشائي جديد",
    }


def _customer_profile(ladder_result, customer_pain=None):
    ladder = ladder_result.get("ladder")
    segment_proxy = {
        "ai_saas": "B2B/مؤسسات تقنية (proxy من مسار الإنتاج)", "b2b_systems": "B2B/مؤسسات (proxy من مسار الإنتاج)",
        "automation_tools": "أفراد/فرق صغيرة تقنية (proxy من مسار الإنتاج)",
        "reusable_assets": "مطوّرون/مصممون (proxy من مسار الإنتاج)",
        "educational": "متعلّمون أفراد (proxy من مسار الإنتاج)", "kdp_books": "قرّاء أفراد (proxy من مسار الإنتاج)",
    }.get(ladder, "غير معروف — لا ladder مُسجَّل")

    if not isinstance(customer_pain, dict) or customer_pain.get("pain_score") is None:
        return {
            "segment_proxy": segment_proxy,
            "real_evidence_count": None,
            "willingness_to_pay_signals": None,
            "note": "لا دليل عملاء حقيقي (نصوص GitHub Issues/HN/Stack Overflow) مُجمَّع لهذا القرار بعد -- شغّل إجراء go-deep-evidence للحصول على دليل حقيقي. لا شخصية عميل مُختلَقة.",
        }

    ev = customer_pain.get("real_evidence") or {}
    total_evidence = (ev.get("github_issues_found") or 0) + (ev.get("hn_discussions_found") or 0) + (ev.get("stack_overflow_found") or 0)
    return {
        "segment_proxy": segment_proxy,
        "real_evidence_count": total_evidence,
        "willingness_to_pay_signals": ev.get("willingness_to_pay_hits"),
        "query_used": customer_pain.get("query_used"),
        "note": f"مبني على {total_evidence} دليل حقيقي (GitHub Issues + HN + Stack Overflow) لاستعلام \"{customer_pain.get('query_used')}\" -- عدّ حقيقي، لا شخصية عميل مُختلَقة.",
    }


def _product_architecture(ladder, product_family=None):
    resolved = resolve_product_family(ladder, product_family)
    capability = {}
    for name in ALL_PRODUCT_FAMILIES:
        adapter = product_families_registry.get(name)
        capability[name] = "REAL" if adapter is not None else "NOT YET BUILT"

    if resolved is None:
        return {"resolved_family": None, "status": "Unknown", "note": "لا ladder معروف لتحديد عائلة المنتج"}

    status = capability.get(resolved, "NOT YET BUILT")
    return {
        "resolved_family": resolved,
        "status": status,
        "note": (
            f"عائلة المنتج الحقيقية المُقترَحة: {resolved} -- الحالة: {status}"
            + ("" if status == "REAL" else " (لا مولّد حقيقي مُسجَّل بعد -- ELITE_ASSET_DOCTRINE.md §6: يحتاج بنية استضافة/فوترة غير موجودة اليوم)")
        ),
    }


def _mvp_roadmap(ladder, product_family_status):
    steps = []
    if product_family_status.get("status") == "REAL":
        steps.append({
            "step": "توليد المحتوى/الحزمة", "status": "قابل للتنفيذ اليوم",
            "evidence": f"عائلة المنتج {product_family_status.get('resolved_family')} لها مولّد حقيقي مُسجَّل (product_families.registry)",
        })
        steps.append({
            "step": "الفحص المزدوج (Dual Inspection) + التوزيع", "status": "قابل للتنفيذ اليوم",
            "evidence": "خط الإنتاج الحقيقي الموجود (inspectors.py + commercial_execution) يغطي هذا تلقائياً",
        })
    else:
        steps.append({
            "step": "بناء بنية تحتية حقيقية (استضافة/قاعدة بيانات/فوترة اشتراك)", "status": "محظور -- غير موجود اليوم",
            "evidence": "ELITE_ASSET_DOCTRINE.md §6: لا استضافة، لا قاعدة بيانات مستخدمين، لا نظام اشتراك متكرر في هذا المصنع اليوم",
        })
    return {
        "steps": steps,
        "note": "لا نموذج تقدير وقت تطوير حقيقي في هذا المصنع (estimate_production_cost() يقيس التكلفة بالدولار، لا التقويم) -- تسلسل خطوات حقيقي (قابل للتنفيذ/محظور)، لا جدول زمني مُختلَق.",
    }


def _revenue_model(ladder_result):
    components = ladder_result.get("components") or {}
    recurring = components.get("recurring_revenue_potential")
    return {
        "recurring_revenue_potential": recurring,
        "ladder": ladder_result.get("ladder"),
        "note": f"إيراد متكرر حقيقي (تقدير حسب المسار، RECURRING_REVENUE_BY_LADDER): {recurring}/100" if recurring is not None else "غير معروف",
    }


def _pricing_strategy(ladder_result, log_file=None):
    price = ladder_result.get("price")
    ladder = ladder_result.get("ladder")
    econ_platform = _LADDER_PRICE_BAND_TO_ECONOMICS_PLATFORM.get(profit_oracle.LADDER_PRICE_BAND.get(ladder), "gumroad_digital")
    roi = estimate_pre_acceptance_roi(price, platform=econ_platform, log_file=log_file) if price is not None else {"maturity": "DISCOVERY", "reason": "لا سعر محسوب"}
    return {
        "recommended_price_usd": price,
        "price_band": profit_oracle.LADDER_PRICE_BAND.get(ladder),
        "min_profit_floor_usd": profit_oracle.MIN_LADDER_PROFIT_FLOOR,
        "pre_acceptance_roi": roi,
        "note": f"السعر الحقيقي المُوصى به ${price} (نطاق {profit_oracle.LADDER_PRICE_BAND.get(ladder)}) -- من butter_price()، لا تخمين",
    }


def _competitive_moat(ladder_result):
    defensibility = ladder_result.get("defensibility") or {}
    return {
        "level": defensibility.get("level"),
        "note": defensibility.get("note") or "لا بيانات منافسين مخزَّنة",
    }


def _expansion_strategy(ladder_result, si):
    components = ladder_result.get("components") or {}
    reusability = components.get("reusability")
    ecosystem = si.get("can_create_a_product_ecosystem", {})
    return {
        "reusability_score": reusability,
        "can_create_ecosystem": ecosystem.get("answer"),
        "note": f"قابلية إعادة الاستخدام الحقيقية حسب المسار: {reusability}/100 -- {ecosystem.get('evidence', '')}",
    }


def build_business_dossier(ladder_result, customer_pain=None, product_family=None, log_file=None):
    """ladder_result: an already-computed profit_oracle.ladder_opportunity_score()
    dict -- never recomputed here. customer_pain: an already-computed
    market_intelligence_engine.analyze_customer_pain() dict, if one exists
    for this niche (optional -- most real decisions don't have one yet,
    see this module's own docstring on why Customer Profile degrades
    honestly without it)."""
    si = profit_oracle.strategic_investment_layer(ladder_result)
    architecture = _product_architecture(ladder_result.get("ladder"), product_family)

    return {
        "niche": ladder_result.get("niche"),
        "ladder": ladder_result.get("ladder"),
        "business_thesis": _business_thesis(ladder_result, si),
        "customer_profile": _customer_profile(ladder_result, customer_pain),
        "product_architecture": architecture,
        "mvp_roadmap": _mvp_roadmap(ladder_result.get("ladder"), architecture),
        "revenue_model": _revenue_model(ladder_result),
        "pricing_strategy": _pricing_strategy(ladder_result, log_file=log_file),
        "competitive_moat": _competitive_moat(ladder_result),
        "expansion_strategy": _expansion_strategy(ladder_result, si),
        "strategic_investment": si,
        "note": "توليف حتمي فوق بيانات حقيقية محسوبة مسبقاً -- لا استدعاء LLM لإنشاء نص جديد هنا، لا شخصية عميل مُختلَقة، لا جدول زمني مُختلَق. معلوماتي فقط -- لا يُغيّر بوابة القبول/الرفض.",
    }
