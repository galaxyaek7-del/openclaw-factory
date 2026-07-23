"""
Opportunity Pipeline (Opportunity Intelligence Round 2, 2026-07-22;
Strategic Opportunity Intelligence Engine, 2026-07-22).

A real, ranked view over every already-scored opportunity in
data/decisions.jsonl -- real fields per opportunity, each either a real
value (reused verbatim from profit_oracle/decision_engine/market_
intelligence_engine, never recomputed) or honestly Unknown when this
factory has no real signal for it yet (Time to MVP has no real data
source anywhere in this codebase -- reported as such, never guessed;
Market Size is a real discussion-volume proxy, explicitly never a dollar
TAM figure -- see profit_oracle._score_market_signal()'s own docstring).

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
    potential, reusability, automation_potential}, risk, confidence,
    defensibility, market_signal, ai_leverage}
  - "ai_ceo_full_evaluation" (the deliberate path): {scores: {demand,
    competition, margin, execution}, risk, confidence, defensibility,
    market_signal, ai_leverage, customer_pain, demand_pattern,
    competitors, opportunity_gap, pricing}
This module checks both shapes per field rather than assuming one.

Also synthesizes profit_oracle.strategic_investment_layer() per
opportunity -- "evaluate as if acquiring a company" -- whenever a real
ladder is on record; honestly omitted (never fabricated) for decisions
with no ladder.
"""

from datetime import datetime, timezone

from decision_engine import ranking
import profit_oracle
import business_dossier as bd
import executive_board as eb
import market_alerts
import decision_reopen


def _unknown(reason):
    return {"answer": "Unknown", "reason": reason}


def _first_not_none(*values):
    for v in values:
        if v is not None:
            return v
    return None


def _annotate(decision, board_path=None, alerts_path=None, reopen_log_path=None):
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

    # Strategic Opportunity Intelligence Engine (2026-07-22): the 3
    # dimensions that previously had zero real signal -- now real.
    market_signal = snap.get("market_signal")
    if not isinstance(market_signal, dict) or market_signal.get("level") is None:
        market_signal = _unknown("لم يُحسَب بعد لهذا القرار (رُصِد أول مرة اعتباراً من 2026-07-22 -- قرارات أقدم لا تحمله)")

    ai_leverage = snap.get("ai_leverage")
    if not isinstance(ai_leverage, dict) or ai_leverage.get("level") is None:
        ai_leverage = _unknown("لم يُحسَب بعد لهذا القرار (رُصِد أول مرة اعتباراً من 2026-07-22 -- قرارات أقدم لا تحمله)")

    automation_potential = ladder_components.get("automation_potential")
    if automation_potential is None:
        automation_potential = _unknown("مكوّن قابلية الأتمتة (حسب المسار) يُحسَب فقط عبر مسار ladder_fast_gate -- غير متاح لهذا القرار")

    # Strategic Investment Layer -- only when a real ladder is on record
    # (the synthesis needs ladder-specific components); honestly omitted,
    # never fabricated, otherwise.
    strategic_investment = None
    reconstructed_ladder_result = None
    if ladder and ladder_components:
        reconstructed_ladder_result = {
            "niche": decision.get("niche"), "ladder": ladder, "price": price,
            "components": ladder_components,
            "defensibility": snap.get("defensibility"),
            "market_signal": snap.get("market_signal"),
            "ai_leverage": snap.get("ai_leverage"),
        }
        strategic_investment = profit_oracle.strategic_investment_layer(reconstructed_ladder_result)

    # Autonomous Digital Venture Studio (2026-07-22): every ACCEPTED
    # opportunity automatically gets a full Business Dossier (thesis,
    # customer profile, product architecture, MVP roadmap, revenue model,
    # pricing strategy, competitive moat, expansion strategy) -- pure
    # synthesis over the same real reconstructed_ladder_result, no new
    # data gathering, never fabricated. Not built for backlog items --
    # only requested for opportunities already accepted by the real gate.
    business_dossier = None
    if decision.get("status") == "ACCEPTED" and reconstructed_ladder_result is not None:
        business_dossier = bd.build_business_dossier(
            reconstructed_ladder_result, customer_pain=snap.get("customer_pain"),
        )

    # Executive Board Integration (2026-07-23): read-only lookup of
    # whatever the board already decided for this niche -- never
    # convenes a new meeting from a backlog listing (that would mean a
    # new "decision" on every page load, and a full Enterprise Readiness
    # Gate run per row would be far too expensive for this bulk view).
    # Honestly None when this niche never went before the board.
    board_brief = eb.get_latest_board_brief(decision.get("niche"), board_path=board_path) if decision.get("niche") else None

    # Market Evidence & Alerting layer (2026-07-23): same real, read-only
    # connection as board_brief above -- never triggers a new alert scan
    # from a backlog listing.
    active_alerts = market_alerts.get_active_alerts(decision.get("niche"), alerts_path=alerts_path) if decision.get("niche") else None

    # Decision Re-open Trigger (2026-07-23): the full real audit trail of
    # every reopen event for this niche, if any -- same real, read-only
    # connection as board_brief/active_alerts above.
    reopen_history = decision_reopen.get_reopen_history(decision.get("niche"), reopen_log_path=reopen_log_path) if decision.get("niche") else None

    return {
        "niche": decision.get("niche"),
        "decision_id": decision.get("decision_id"),
        "decision_path": decision.get("decision_path"),
        "status": decision.get("status"),
        "opportunity_score": decision.get("opportunity_score"),

        # The 10 originally-named fields (Opportunity Intelligence Round 2):
        "market_size": market_signal,  # real discussion-volume proxy -- see profit_oracle._score_market_signal(), never a dollar TAM
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

        # The 3 dimensions added by the Strategic Opportunity Intelligence
        # Engine (2026-07-22):
        "ai_leverage": ai_leverage,
        "automation_potential": automation_potential,

        # The Strategic Investment Layer -- 7 acquisition-style questions,
        # synthesized from the real fields above. None (not fabricated)
        # when no real ladder exists to synthesize from.
        "strategic_investment": strategic_investment,

        # Autonomous Digital Venture Studio (2026-07-22): only present for
        # ACCEPTED opportunities, per the founder's own scoping ("every
        # accepted opportunity must automatically generate..."). None
        # (never fabricated) for backlog items.
        "business_dossier": business_dossier,

        # Executive Board Integration (2026-07-23): the latest real board
        # decision for this niche, if one has ever been convened. None
        # (never fabricated) when it hasn't.
        "board_brief": board_brief,

        # Market Evidence & Alerting layer (2026-07-23): active competitor
        # alerts for this niche (Critical/High/Medium/Low), if any real
        # scan has ever run. None (never fabricated) otherwise.
        "active_alerts": active_alerts,

        # Decision Re-open Trigger (2026-07-23): [] when this niche has
        # never been reopened (never fabricated as None-vs-empty-list
        # confusion -- get_reopen_history() always returns a real list).
        "reopen_history": reopen_history,

        # Additional real, already-computed context (not part of the
        # named fields, kept for transparency):
        "risk": snap.get("risk"),
        "confidence": snap.get("confidence"),
        "reasoning": decision.get("reasoning"),
    }


def build_opportunity_pipeline(decisions_path=None, backlog_limit=100, board_path=None, alerts_path=None, reopen_log_path=None):
    """Product Laboratory = every real decision already ACCEPTED by the
    existing gate (never a new invented threshold). Backlog = everything
    else, capped at backlog_limit for a readable response -- the real
    total count is always reported honestly even when the list itself is
    truncated.

    board_path: test-isolation override for the board_brief lookup
    (Executive Board Integration, 2026-07-23), same convention as
    decisions_path -- omitting it reads the real default board_meetings.jsonl.
    alerts_path: same isolation convention for the active_alerts lookup
    (Market Evidence & Alerting layer, 2026-07-23). reopen_log_path: same
    isolation convention for the reopen_history lookup (Decision Re-open
    Trigger, 2026-07-23)."""
    decisions = ranking.rank_all(path=decisions_path)
    annotated = [_annotate(d, board_path=board_path, alerts_path=alerts_path, reopen_log_path=reopen_log_path) for d in decisions]

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
