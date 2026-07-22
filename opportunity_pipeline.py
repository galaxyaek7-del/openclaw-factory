"""
Opportunity Pipeline (Opportunity Intelligence Round 2, 2026-07-22).

A real, ranked view over every already-scored opportunity in
data/decisions.jsonl -- ten named fields per opportunity, each either a
real value (reused verbatim from profit_oracle/decision_engine/market_
intelligence_engine, never recomputed) or honestly Unknown when this
factory has no real signal for it yet (Market Size and Time to MVP have
no real data source anywhere in this codebase -- reported as such, never
guessed).

Reads only already-computed real data (decision_engine.ranking.rank_all())
-- zero live network calls, safe to run over the full real history in
milliseconds, unlike golden_hunter/hunt.py's live re-scan. Never
recomputes accept/reject -- "Product Laboratory" is exactly the set of
decisions already ACCEPTED by the real, existing gate
(profit_oracle.ladder_opportunity_score()'s $97 floor + score floor, or
opportunity_score()'s tier floor) -- no new invented threshold.

Two real decision paths produce structurally different evaluation_
snapshot shapes (decision_engine/engine.py):
  - "ladder_fast_gate" (market_hunter.py, what nearly all real decisions
    use today): {ladder, price, components: {market_demand,
    competition_favorability, profit_potential, recurring_revenue_
    potential, reusability}, risk, confidence, defensibility}
  - "ai_ceo_full_evaluation" (the deliberate path): {scores: {demand,
    competition, margin, execution}, risk, confidence, defensibility,
    customer_pain, demand_pattern, competitors, opportunity_gap, pricing}
This module checks both shapes per field rather than assuming one.
"""

from datetime import datetime, timezone

from decision_engine import ranking


def _unknown(reason):
    return {"answer": "Unknown", "reason": reason}


def _first_not_none(*values):
    for v in values:
        if v is not None:
            return v
    return None


def _annotate(decision):
    snap = decision.get("evaluation_snapshot") or {}
    ladder_components = snap.get("components") or {}
    ai_ceo_scores = snap.get("scores") or {}
    ladder = decision.get("ladder")

    pain = snap.get("customer_pain")
    pain_level = (
        {"value": pain.get("pain_score"), "confidence": pain.get("confidence"), "reason": pain.get("reason")}
        if isinstance(pain, dict)
        else _unknown("لا دليل ألم عملاء حقيقي مسجَّل لهذا القرار (المسار السريع ladder_fast_gate لا يجمعه تلقائياً -- استخدم إجراء go-deep-evidence)")
    )

    competition_value = _first_not_none(ladder_components.get("competition_favorability"), ai_ceo_scores.get("competition"))
    competitors = snap.get("competitors")
    competition = (
        {"favorability_score": competition_value, "real_competitors": competitors}
        if competition_value is not None
        else _unknown("لا مكوّن منافسة محفوظ لهذا القرار")
    )

    price = _first_not_none(snap.get("price"), (snap.get("pricing") or {}).get("recommended_price"))

    recurring = ladder_components.get("recurring_revenue_potential")
    recurring_revenue_potential = (
        recurring if recurring is not None
        else _unknown("مكوّن الإيراد المتكرر يُحسَب فقط عبر مسار ladder_fast_gate -- غير متاح لهذا القرار")
    )

    technical_complexity = (
        ai_ceo_scores.get("execution") if ai_ceo_scores.get("execution") is not None
        else _unknown("مكوّن قابلية التنفيذ يُحسَب فقط عبر مسار ai_ceo_full_evaluation -- غير متاح لهذا القرار (المسار السريع لا يحسبه)")
    )

    defensibility = snap.get("defensibility")
    if not isinstance(defensibility, dict) or defensibility.get("level") is None:
        defensibility = _unknown("لم يُحسَب بعد لهذا القرار (رُصِد أول مرة اعتباراً من 2026-07-22 -- قرارات أقدم لا تحمله)")

    reusability = ladder_components.get("reusability")
    global_scalability = (
        reusability if reusability is not None
        else _unknown("مكوّن قابلية إعادة الاستخدام يُحسَب فقط عبر مسار ladder_fast_gate -- غير متاح لهذا القرار")
    )

    return {
        "niche": decision.get("niche"),
        "decision_id": decision.get("decision_id"),
        "decision_path": decision.get("decision_path"),
        "status": decision.get("status"),
        "opportunity_score": decision.get("opportunity_score"),

        # The 10 named fields (Opportunity Intelligence Round 2 ask):
        "market_size": _unknown("لا مصدر بيانات TAM حقيقي في هذا المصنع بعد"),
        "customer_type": (
            {"value": ladder, "note": "proxy من مسار الإنتاج (ladder rank) -- لا تصنيف عملاء حقيقي منفصل موجود بعد"}
            if ladder else _unknown("لا ladder مُسجَّل لهذا القرار")
        ),
        "pain_level": pain_level,
        "competition": competition,
        "estimated_selling_price": price if price is not None else _unknown("لا سعر مُوصى به محفوظ لهذا القرار"),
        "recurring_revenue_potential": recurring_revenue_potential,
        "technical_complexity": technical_complexity,
        "time_to_mvp": _unknown("لا نموذج تقدير وقت تطوير حقيقي في هذا المصنع بعد -- estimate_production_cost() يقيس التكلفة الحقيقية بالدولار، لا الوقت بالتقويم"),
        "defensibility": defensibility,
        "global_scalability": global_scalability,

        # Additional real, already-computed context (not part of the 10
        # named fields, kept for transparency):
        "risk": snap.get("risk"),
        "confidence": snap.get("confidence"),
        "reasoning": decision.get("reasoning"),
    }


def build_opportunity_pipeline(decisions_path=None, backlog_limit=100):
    """Product Laboratory = every real decision already ACCEPTED by the
    existing gate (never a new invented threshold). Backlog = everything
    else, capped at backlog_limit for a readable response -- the real
    total count is always reported honestly even when the list itself is
    truncated."""
    decisions = ranking.rank_all(path=decisions_path)
    annotated = [_annotate(d) for d in decisions]

    product_laboratory = [a for a in annotated if a["status"] == "ACCEPTED"]
    backlog_all = [a for a in annotated if a["status"] != "ACCEPTED"]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_opportunities": len(annotated),
        "product_laboratory": product_laboratory,
        "product_laboratory_count": len(product_laboratory),
        "backlog": backlog_all[:backlog_limit],
        "backlog_count": len(backlog_all),
        "backlog_truncated": len(backlog_all) > backlog_limit,
        "note": "معلوماتي فقط -- data/decisions.jsonl يبقى مصدر الحقيقة الوحيد، لا حساب جديد للقبول/الرفض. Product Laboratory = كل قرار مقبول فعلاً (status=ACCEPTED) عبر البوابة الحقيقية الموجودة (profit_oracle.ladder_opportunity_score()).",
    }


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Opportunity Pipeline (Opportunity Intelligence Round 2)")
    parser.add_argument('--backlog-limit', type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(build_opportunity_pipeline(backlog_limit=args.backlog_limit), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
