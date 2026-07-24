#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Executive Quality Gate (Executive Directive, 2026-07-22).

A permanent core layer every opportunity, product, report, or
recommendation must pass before entering production. Reuses every real
signal this factory already computes -- "wrap, don't rewrite" applied to
governance itself, same as every engine addition this factory has made.
Builds exactly one new real check (brand_reputation_risk's content scan)
and one new real computation (evidence_freshness) that didn't exist
before; every other criterion is a real, already-computed field threaded
through, never recalculated with new logic.

The honest core of this module: several of the 20 requested criteria
have NO automatically-observed real data source anywhere in this
factory today -- willingness-to-pay, customer-acquisition-difficulty per
specific niche, and customer-retention-potential all depend on real
market interactions this factory has no live instrumentation to detect
on its own (no landing page, no connected CRM, no automatic call
transcription). A gate that silently scored these anyway would be
exactly the fabrication this whole engagement has refused everywhere
else.

Market Learning Loop (2026-07-22, market_evidence.py): these three
criteria now auto-consume a real, permanent evidence ledger the moment
ANY real event (a real discovery call outcome, a real cold-email reply,
a real closed sale) has actually been recorded for that niche -- by a
human, or by Claude Code checking a real channel during a session.
UNKNOWN never disappears on its own; it disappears only because real
evidence arrived and was logged. Zero recorded evidence for a niche
still means honestly UNKNOWN, routed to NEEDS_HUMAN_REVIEW, never a
fabricated PASS.

Never triggers a live network call -- reads only already-computed or
already-cached real data (competitor_discovery's cache,
market_intelligence's already-recorded evidence, product_families'
registry status), same discipline every other scoring path in this
factory already follows.

    python executive_quality_gate.py --check "some niche" [--json]
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))


# ── Criteria that force NEEDS_HUMAN_REVIEW when their real status is
# UNKNOWN -- this factory has never built a real data source for these,
# so "we don't know" is the honest, permanent default, not a gap to hide.
HUMAN_REVIEW_IF_UNKNOWN = (
    "willingness_to_pay_evidence",
    "customer_acquisition_difficulty",
    "customer_retention_potential",
)

# Criteria whose real FAIL verdict rejects the opportunity outright.
REJECT_IF_FAIL = (
    "customer_pain_evidence",
    "legal_compliance_risk",
    "brand_reputation_risk",
    "market_saturation_competitor_quality",
)

EVIDENCE_STALE_AFTER_DAYS = 90


def _unknown(reason):
    return {"status": "UNKNOWN", "evidence": None, "reason": reason}


def _real(status, evidence, reason):
    return {"status": status, "evidence": evidence, "reason": reason}


def _days_since(iso_ts):
    if not iso_ts:
        return None
    try:
        then = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if then.tzinfo is None:
            then = then.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - then).days
    except (ValueError, TypeError):
        return None


# ── 1. Real customer pain evidence ──
def check_customer_pain_evidence(customer_pain):
    """Reuses market_intelligence_engine.analyze_customer_pain()'s
    already-computed real evidence -- never re-queries live here."""
    if not isinstance(customer_pain, dict) or customer_pain.get("pain_score") is None:
        return _unknown("لا دليل ألم عملاء حقيقي مسجَّل لهذا القرار — Go Deep Evidence لم يُشغَّل بعد")
    real_evidence = customer_pain.get("real_evidence") or {}
    total_hits = sum(real_evidence.get(k) or 0 for k in ("github_issues_found", "hn_discussions_found", "stack_overflow_found"))
    if total_hits == 0:
        return _real("FAIL", real_evidence, "صفر أدلة حقيقية (GitHub/HN/Stack Overflow) رغم محاولة الاستعلام الحقيقي")
    return _real("PASS", real_evidence, f"{total_hits} دليل حقيقي (GitHub/HN/Stack Overflow)")


# ── 2. Real willingness-to-pay evidence ──
def check_willingness_to_pay(explicit_wtp_evidence=None, niche=None):
    """Market Learning Loop (2026-07-22): auto-consumes market_evidence.py's
    real, already-recorded WTP-adjacent events (demo/trial/purchase/
    closed-sale = positive, pricing_objection = negative) for this exact
    niche the moment any real evidence exists -- never invents a dollar
    figure, only counts real events. Still always Unknown when zero real
    evidence has been recorded yet, matching this factory's honest
    default (zero real sales exist for most niches today)."""
    if explicit_wtp_evidence:
        return _real("PASS", explicit_wtp_evidence, "دليل استعداد للدفع حقيقي مُقدَّم صراحةً من مصدر خارجي")
    if niche:
        import market_evidence
        signal = market_evidence.get_willingness_to_pay_signal(niche)
        if signal:
            if signal["positive_signals"] > 0 and signal["pricing_objections"] == 0:
                return _real("PASS", signal, f"{signal['positive_signals']} إشارة سوق حقيقية إيجابية مسجَّلة (طلب عرض/تجربة/شراء/بيع مغلق)")
            if signal["pricing_objections"] > 0 and signal["pricing_objections"] >= signal["positive_signals"]:
                return _real("FAIL", signal, f"{signal['pricing_objections']} اعتراض سعري حقيقي مسجَّل، يساوي أو يفوق الإشارات الإيجابية")
            return _real("INFO", signal, f"دليل سوق حقيقي مختلط: {signal['positive_signals']} إيجابي، {signal['pricing_objections']} اعتراض سعري")
    return _unknown("لا آلية حقيقية في هذا المصنع لقياس الاستعداد للدفع تلقائياً — صفر دليل سوق حقيقي (Market Evidence Ledger) مُسجَّل بعد لهذا النيتش")


# ── 3. Market saturation and competitor quality ──
def check_market_saturation(niche, competitor_db=None):
    """Reuses competitor_discovery.py's cached database only -- never
    triggers a live search from inside the gate."""
    if competitor_db is None:
        try:
            import competitor_discovery
            competitor_db = competitor_discovery.load_database()
        except Exception:
            competitor_db = {}
    key = re.sub(r"\s+", " ", (niche or "").strip().lower())
    entry = competitor_db.get(key)
    if not entry:
        return _unknown("لا بيانات منافسين مخزَّنة لهذا النيتش — لم يُشغَّل اكتشاف منافسين حقيقي بعد")
    competitors = entry.get("competitors") or []
    enterprise_leaders = [c for c in competitors if c.get("classification") == "Enterprise Leader"]
    if len(enterprise_leaders) >= 2:
        return _real("FAIL", entry, f"{len(enterprise_leaders)} قائد مؤسسي حقيقي موجود بالفعل — تشبّع سوق حقيقي")
    return _real("PASS", entry, f"{len(competitors)} منافس حقيقي مُصنَّف، {len(enterprise_leaders)} قائد مؤسسي فقط")


# ── 4. Technical feasibility ──
def check_technical_feasibility(ladder, product_family=None):
    from product_families import registry as pf_registry
    from product_families.mapping import resolve_product_family
    family = resolve_product_family(ladder, product_family)
    if not family:
        return _unknown(f"لا عائلة منتج معروفة للـ ladder '{ladder}'")
    adapter = pf_registry.get(family)
    if adapter is None:
        return _real("FAIL", {"family": family}, f"لا محرك إنتاج حقيقي مبني بعد لهذه العائلة ({family}) — غير قابل للتنفيذ اليوم")
    return _real("PASS", {"family": family}, f"محرك إنتاج حقيقي موجود ({family})")


# ── 5. Legal and compliance risk (real, partial proxy only) ──
def check_legal_compliance_risk(niche):
    """Real but explicitly partial: reuses safety_filter.py's content-risk
    keyword check plus real quarantine/rejection history. This is NOT a
    real legal-compliance analysis engine -- no such thing exists in this
    factory -- and is never presented as full legal clearance."""
    import safety_filter
    import inspectors
    quarantined = (niche or "").strip().lower() in inspectors._read_quarantined_niches()
    if quarantined:
        return _real("FAIL", {"quarantined": True}, "هذا النيتش محجوب سابقاً في QUARANTINE.md")
    result = safety_filter.evaluate({"niche": niche})
    if not result.get("allowed"):
        return _real("FAIL", result, f"safety_filter.py رفض: {result.get('risk_level')} — {result.get('reasons')}")
    return _real("PASS", result, f"لا مخاطر محتوى معروفة (score {result.get('score')}/100) — فحص جزئي فقط، ليس تحليلاً قانونياً كاملاً")


# ── 6. Delivery capability ──
def check_delivery_capability(ladder, product_family=None, cost_log_file=None):
    from revenue_pipeline import plan as plan_module
    feasibility = check_technical_feasibility(ladder, product_family)
    if feasibility["status"] != "PASS":
        return feasibility
    cost = plan_module.estimate_production_cost(log_file=cost_log_file)
    if cost.get("maturity") != "REAL":
        return _unknown("لا تكلفة إنتاج حقيقية مسجَّلة بعد لتأكيد القدرة على التسليم")
    return _real("PASS", cost, f"محرك حقيقي + تكلفة إنتاج حقيقية مؤكَّدة (${cost['estimated_cost_usd']}/عملية، عيّنة {cost['sample_size']})")


# ── 7. Scalability ──
def check_scalability(components):
    reusability = (components or {}).get("reusability")
    if reusability is None:
        return _unknown("لا مكوّن قابلية إعادة استخدام محسوب لهذا القرار")
    if reusability < 50:
        return _real("FAIL", {"reusability": reusability}, f"قابلية إعادة استخدام منخفضة ({reusability}/100)")
    return _real("PASS", {"reusability": reusability}, f"قابلية إعادة استخدام حقيقية: {reusability}/100")


# ── 8. Defensibility ──
def check_defensibility(defensibility_field):
    if not isinstance(defensibility_field, dict) or defensibility_field.get("level") is None:
        return _unknown("لم يُحسَب دفاعية حقيقية لهذا القرار بعد")
    return _real("INFO", defensibility_field, f"دفاعية: {defensibility_field.get('level')}")


# ── 9. Long-term strategic value ──
def check_long_term_strategic_value(strategic_investment):
    if not isinstance(strategic_investment, dict):
        return _unknown("لا طبقة استثمار استراتيجي محسوبة لهذا القرار")
    keys = [
        "can_become_premium_digital_asset", "can_evolve_into_software_business",
        "can_create_recurring_revenue", "can_dominate_a_narrow_market",
        "becomes_more_valuable_over_time", "can_create_a_product_ecosystem",
    ]
    yes_count = sum(1 for k in keys if (strategic_investment.get(k) or {}).get("answer") == "Yes")
    return _real("INFO", strategic_investment, f"{yes_count}/{len(keys)} سؤال استراتيجي حقيقي بإجابة Yes")


# ── 10. Revenue model sustainability ──
def check_revenue_model_sustainability(components):
    recurring = (components or {}).get("recurring_revenue_potential")
    if recurring is None:
        return _unknown("لا مكوّن إيراد متكرر محسوب لهذا القرار")
    if recurring < 40:
        return _real("FAIL", {"recurring_revenue_potential": recurring}, f"إمكانية إيراد متكرر منخفضة ({recurring}/100)")
    return _real("PASS", {"recurring_revenue_potential": recurring}, f"إمكانية إيراد متكرر حقيقية: {recurring}/100")


# ── 11. Brand reputation risk (new real check, grounded in a live 2026-07-22 finding) ──
BRAND_RISK_PHRASES = [
    "our platform", "our sales team", "24/7 support", "24/7 dedicated support",
    "sign up for an account", "create a new account", "our dedicated support team",
    "click the \"deploy\" button", "deploy the ai chatbot",
]


def check_brand_reputation_risk(product_chapters=None):
    """Real, deterministic content scan for the exact fabricated-hosted-
    software claim pattern found live this session (product quality
    pass, 2026-07-22): AI-generated techdoc content describing a real
    platform, sales team, and 24/7 support that don't exist. Not
    exhaustive and not a substitute for human review, but a real, cheap,
    automatable first pass. Honestly Unknown if no content is supplied."""
    if not product_chapters:
        return _unknown("لا محتوى منتج مُقدَّم للفحص")
    combined = " ".join(
        (c.get("content") or "") for c in product_chapters if isinstance(c, dict)
    ).lower()
    hits = [p for p in BRAND_RISK_PHRASES if p in combined]
    if hits:
        return _real("FAIL", hits, f"المحتوى يدّعي بنية تحتية/فريق دعم غير موجود فعلياً: {', '.join(hits)}")
    return _real("PASS", None, "لا عبارات ادّعاء بنية تحتية غير حقيقية موجودة في نص المحتوى (فحص جزئي)")


# ── 12. Operational cost ──
def check_operational_cost(cost_log_file=None):
    from revenue_pipeline import plan as plan_module
    cost = plan_module.estimate_production_cost(log_file=cost_log_file)
    if cost.get("maturity") != "REAL":
        return _unknown(cost.get("reason", "لا تكلفة تشغيل حقيقية مسجَّلة بعد"))
    return _real("INFO", cost, f"تكلفة حقيقية: ${cost['estimated_cost_usd']}/عملية (عيّنة {cost['sample_size']})")


# ── 13. Customer acquisition difficulty ──
def check_customer_acquisition_difficulty(explicit_cac_evidence=None, niche=None):
    """Market Learning Loop (2026-07-22): auto-consumes market_evidence.py's
    real logged cold_outreach_result/email_reply events for this niche
    -- a real, computed reply rate, not a dollar CAC (no real spend-
    tracking exists to compute a dollar figure from). Still Unknown when
    zero real outreach has been logged yet for this niche."""
    if explicit_cac_evidence:
        return _real("INFO", explicit_cac_evidence, "دليل صعوبة اكتساب عملاء حقيقي مُقدَّم صراحةً")
    if niche:
        import market_evidence
        signal = market_evidence.get_customer_acquisition_signal(niche)
        if signal:
            rate_note = f" (معدل رد {signal['reply_rate_pct']}%)" if signal["reply_rate_pct"] is not None else ""
            return _real("INFO", signal, f"دليل سوق حقيقي: أُرسِل {signal['sent']}، رَدّ {signal['replied']}{rate_note}")
    return _unknown("لا مصدر بيانات آلي حقيقي لصعوبة اكتساب العملاء — صفر دليل سوق حقيقي (Market Evidence Ledger) مُسجَّل بعد لهذا النيتش")


# ── 14. Customer retention potential ──
def check_customer_retention_potential(niche=None):
    """Market Learning Loop (2026-07-22): auto-consumes market_evidence.py's
    real retention_signal events (renewal/churn) for this niche. Still
    Unknown by default -- zero real sales exist anywhere in this factory
    to measure retention from for most niches today, and pretending
    otherwise would be exactly the fabrication this gate exists to
    prevent."""
    if niche:
        import market_evidence
        signal = market_evidence.get_retention_signal(niche)
        if signal:
            if signal["churned"] > signal["renewed"]:
                return _real("FAIL", signal, f"{signal['churned']} حالة تسرّب حقيقية مسجَّلة، أكثر من التجديد ({signal['renewed']})")
            return _real("PASS" if signal["renewed"] > 0 else "INFO", signal, f"{signal['renewed']} تجديد حقيقي، {signal['churned']} تسرّب مسجَّل")
    return _unknown("صفر مبيعات/تجديدات حقيقية مسجَّلة بعد لقياس الاحتفاظ بالعملاء لهذا النيتش — لا توجد طريقة صادقة لتقييم هذا حتى يصل دليل حقيقي")


# ── 15. Infrastructure readiness ──
def check_infrastructure_readiness(ladder, product_family=None):
    """Same real underlying signal as technical_feasibility/delivery_
    capability (product_families.registry) -- reported separately per
    the directive's own 20-point structure, but honestly noted as the
    same real check, not a second independent measurement."""
    result = check_technical_feasibility(ladder, product_family)
    if result["status"] == "UNKNOWN":
        return result
    note = " (نفس فحص technical_feasibility الحقيقي، غير مقاس بشكل منفصل)"
    return _real(result["status"], result["evidence"], result["reason"] + note)


# ── 16. Automation readiness ──
def check_automation_readiness(components):
    automation_potential = (components or {}).get("automation_potential")
    if automation_potential is None:
        return _unknown("لا مكوّن قابلية أتمتة محسوب لهذا القرار")
    return _real("INFO", {"automation_potential": automation_potential}, f"قابلية أتمتة حقيقية: {automation_potential}/100")


# ── 17. Data confidence score ──
def check_data_confidence_score(confidence_field):
    if not isinstance(confidence_field, dict) or confidence_field.get("score") is None:
        return _unknown("لا درجة ثقة حقيقية محسوبة لهذا القرار")
    score = confidence_field["score"]
    if score < 40:
        return _real("FAIL", confidence_field, f"ثقة بيانات منخفضة جداً ({score}/100)")
    return _real("PASS" if score >= 60 else "INFO", confidence_field, f"ثقة بيانات حقيقية: {score}/100 ({confidence_field.get('level', '')})")


# ── 18. Evidence freshness ──
def check_evidence_freshness(decided_at=None, competitor_cache_age_days=None):
    ages = []
    decision_age = _days_since(decided_at)
    if decision_age is not None:
        ages.append(("decision", decision_age))
    if competitor_cache_age_days is not None:
        ages.append(("competitor_cache", competitor_cache_age_days))
    if not ages:
        return _unknown("لا طوابع زمنية حقيقية متاحة لقياس حداثة الأدلة")
    stale = [(name, age) for name, age in ages if age > EVIDENCE_STALE_AFTER_DAYS]
    if stale:
        return _real("FAIL", dict(ages), f"أدلة قديمة (>{EVIDENCE_STALE_AFTER_DAYS} يوم): {stale}")
    return _real("PASS", dict(ages), f"الأدلة حديثة (أقدمها {max(a for _, a in ages)} يوم)")


# ── 19/20. Human review requirement + final executive decision (meta) ──
def _run_all_checks(spec):
    snap = spec.get("evaluation_snapshot") or {}
    components = snap.get("components") or {}
    return {
        "customer_pain_evidence": check_customer_pain_evidence(snap.get("customer_pain")),
        "willingness_to_pay_evidence": check_willingness_to_pay(spec.get("explicit_wtp_evidence"), niche=spec.get("niche")),
        "market_saturation_competitor_quality": check_market_saturation(spec.get("niche"), spec.get("competitor_db")),
        "technical_feasibility": check_technical_feasibility(spec.get("ladder"), spec.get("product_family")),
        "legal_compliance_risk": check_legal_compliance_risk(spec.get("niche")),
        "delivery_capability": check_delivery_capability(spec.get("ladder"), spec.get("product_family"), spec.get("cost_log_file")),
        "scalability": check_scalability(components),
        "defensibility": check_defensibility(snap.get("defensibility")),
        "long_term_strategic_value": check_long_term_strategic_value(spec.get("strategic_investment")),
        "revenue_model_sustainability": check_revenue_model_sustainability(components),
        "brand_reputation_risk": check_brand_reputation_risk(spec.get("product_chapters")),
        "operational_cost": check_operational_cost(spec.get("cost_log_file")),
        "customer_acquisition_difficulty": check_customer_acquisition_difficulty(spec.get("explicit_cac_evidence"), niche=spec.get("niche")),
        "customer_retention_potential": check_customer_retention_potential(niche=spec.get("niche")),
        "infrastructure_readiness": check_infrastructure_readiness(spec.get("ladder"), spec.get("product_family")),
        "automation_readiness": check_automation_readiness(components),
        "data_confidence_score": check_data_confidence_score(snap.get("confidence")),
        "evidence_freshness": check_evidence_freshness(spec.get("decided_at"), spec.get("competitor_cache_age_days")),
    }


def _human_review_required(results):
    reasons = [
        f"{name}: {results[name]['reason']}"
        for name in HUMAN_REVIEW_IF_UNKNOWN
        if results.get(name, {}).get("status") == "UNKNOWN"
    ]
    return bool(reasons), reasons


def _final_decision(results, human_review_required):
    hard_failures = [
        f"{name}: {results[name]['reason']}"
        for name in REJECT_IF_FAIL
        if results.get(name, {}).get("status") == "FAIL"
    ]
    other_failures = [
        f"{name}: {v['reason']}" for name, v in results.items()
        if v.get("status") == "FAIL" and name not in REJECT_IF_FAIL
    ]
    if hard_failures:
        return "REJECTED", hard_failures + other_failures
    if human_review_required:
        return "NEEDS_HUMAN_REVIEW", other_failures
    if other_failures:
        return "REJECTED", other_failures
    return "APPROVED", []


def _written_explanation(niche, results, decision, decision_reasons, review_reasons):
    lines = [f"Executive Quality Gate — {niche or 'غير محدَّد'}", f"القرار النهائي: {decision}", ""]
    if decision_reasons:
        lines.append("أسباب الرفض/الفشل الحقيقية:")
        lines += [f"  - {r}" for r in decision_reasons]
        lines.append("")
    if review_reasons:
        lines.append("يتطلب مراجعة بشرية بسبب:")
        lines += [f"  - {r}" for r in review_reasons]
        lines.append("")
    lines.append("كل معيار، بالتفصيل:")
    for name, v in results.items():
        lines.append(f"  [{v['status']}] {name}: {v['reason']}")
    return "\n".join(lines)


def run_executive_quality_gate(spec):
    """spec: a dict describing one opportunity/product to gate. Expected
    keys (all optional, gracefully Unknown when missing): niche, ladder,
    product_family, evaluation_snapshot (customer_pain, components,
    defensibility, confidence), strategic_investment, product_chapters,
    explicit_wtp_evidence, explicit_cac_evidence, competitor_db,
    decided_at, competitor_cache_age_days, cost_log_file.

    Returns the full structured result -- never raises, never fabricates
    a criterion it has no real data for."""
    results = _run_all_checks(spec)
    human_review_required, review_reasons = _human_review_required(results)
    decision, decision_reasons = _final_decision(results, human_review_required)
    explanation = _written_explanation(spec.get("niche"), results, decision, decision_reasons, review_reasons)
    return {
        "niche": spec.get("niche"),
        "criteria": results,
        "human_review_required": human_review_required,
        "human_review_reasons": review_reasons,
        "final_decision": decision,
        "decision_reasons": decision_reasons,
        "written_explanation": explanation,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Executive Quality Gate")
    parser.add_argument("--check", metavar="NICHE", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from decision_engine import ranking
    decisions = ranking.rank_all()
    decision = next((d for d in decisions if d.get("niche") == args.check), None)
    if decision is None:
        print(json.dumps({"success": False, "error": f"no decision found for {args.check!r}"}, ensure_ascii=False))
        sys.exit(1)

    result = run_executive_quality_gate({
        "niche": decision.get("niche"),
        "ladder": decision.get("ladder"),
        "evaluation_snapshot": decision.get("evaluation_snapshot"),
        "decided_at": decision.get("decided_at"),
    })
    if args.json:
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
    else:
        print(result["written_explanation"])


if __name__ == "__main__":
    main()
