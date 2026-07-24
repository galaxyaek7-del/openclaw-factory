#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Global CEO Decision Center (2026-07-24).

**Explicit directive: "Do NOT build another production engine... No
duplicated logic. Reuse every existing engine."** Like master_loop.py
(ADR-115) immediately before it, this module is orchestration over
already-real signals, not a new scoring system. Two of the 10 named
CEO questions (market saturation, niche strength) pointed to real
functions this session had not yet connected to anything:
`competitor_discovery.py`'s `_score_competitor_saturation()`/
`_score_market_concentration()`/`_score_new_entrant_trajectory()` —
real, already built, never wired into any of today's aggregation
layers. Wired here for the first time, using only the real, cached
competitor database (`load_database()`) — never a live network call
from a read-only report.

The 10 named questions, mapped to their real sources:
  1. Most profitable opportunity right now -> investment_pipeline.py
  2. Which opportunity should be abandoned  -> scheduler.py's cancel bucket
  3. Which product deserves more investment -> scheduler.py's accelerate bucket
  4. Which country should receive attention -> deferred (unchanged, 7th+ time today)
  5. Which market is becoming saturated     -> competitor_discovery.py (new wiring)
  6. Which niche is becoming stronger       -> competitor_discovery.py (new wiring)
  7. Best AI model per department           -> ai_capability.orchestrator.py
  8. Highest real ROI products              -> investment_pipeline.py
  9. Which pipelines waste resources        -> production_blueprint.py's QUALITY REVIEW bucket
  10. Next commercial experiment            -> scheduler.py / market_memory.py

"The CEO never sleeps" / "every hour" / "continuously reallocates":
the same live-process question already declined via AskUserQuestion in
ADR-107, reaffirmed ADR-110/115 — applied unchanged a fourth time. This
module builds the real, callable functions; it starts no process.

"Automatically allocate resources between" 10 named functions: built as
a real, DESCRIPTIVE snapshot of where real opportunities/evidence
currently concentrate (real counts) — never a fabricated dollar budget.
This factory has no live worker pool or department payroll to actually
reallocate; the honest analog is reporting where real attention already
is, which the founder can act on.
"""

from datetime import datetime, timezone

# Country/China Division stays deferred, unchanged — same reason as
# every prior occurrence today (ADR-103, reaffirmed ADR-106/108/110/
# 111/112/113/114/115).
_COUNTRY_DEFERRAL_REASON = "مؤجَّل بوعي — لا موصّل بيانات سوق محلي حقيقي لأي دولة في هذا المصنع اليوم (نفس القرار المؤكَّد مراراً اليوم)"


def _market_saturation_and_strength(niche, db_file=None):
    """Real saturation/concentration/trajectory scores for one niche —
    reuses competitor_discovery.py's own real, already-built scoring
    functions directly over the real, CACHED competitor database (never
    a live network call). Honest Unknown when no real competitor scan
    has ever run for this niche."""
    import competitor_discovery as cd

    db = cd.load_database(db_file=db_file)
    snapshot = db.get(cd._normalize_key(niche))
    if not snapshot:
        return {
            "niche": niche, "has_real_data": False,
            "reason": "لا مسح منافسين حقيقي (competitor_discovery.py) شُغِّل لهذا النيتش بعد",
        }
    return {
        "niche": niche, "has_real_data": True,
        "saturation": cd._score_competitor_saturation(snapshot),
        "concentration": cd._score_market_concentration(snapshot),
        "trajectory": cd._score_new_entrant_trajectory(snapshot),
    }


def answer_ceo_questions(decisions_path=None, board_path=None, alerts_path=None,
                          reopen_log_path=None, evidence_path=None, timeline_path=None,
                          outcomes_path=None, db_file=None):
    """Real, evidence-based answers to the 10 named questions — every
    answer reused directly from an already-real function, never a new
    evidence claim."""
    import investment_pipeline
    import scheduler
    import production_blueprint
    import market_memory
    from ai_capability import orchestrator as ai_orchestrator
    from decision_engine import ranking

    pipeline = investment_pipeline.build_investment_pipeline(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
    )
    scheduling = scheduler.decide_next_actions(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    missions_board = production_blueprint.build_production_missions_board(
        decisions_path=decisions_path, timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    recommendations = market_memory.recommend_actions(evidence_path=evidence_path)

    accepted_niches = [d["niche"] for d in ranking.rank_all(path=decisions_path) if d.get("status") == "ACCEPTED" and d.get("niche")]
    market_signals = [_market_saturation_and_strength(n, db_file=db_file) for n in accepted_niches]
    with_real_data = [s for s in market_signals if s["has_real_data"]]

    def _top_saturation():
        scored = [s for s in with_real_data if isinstance(s["saturation"], dict) and isinstance(s["saturation"].get("score"), (int, float))]
        return max(scored, key=lambda s: s["saturation"]["score"]) if scored else None

    def _top_trajectory():
        scored = [s for s in with_real_data if isinstance(s["trajectory"], dict) and isinstance(s["trajectory"].get("score"), (int, float))]
        return max(scored, key=lambda s: s["trajectory"]["score"]) if scored else None

    top_saturated = _top_saturation()
    top_strengthening = _top_trajectory()

    return {
        "1_most_profitable_opportunity_now": pipeline["entries"][0] if pipeline["entries"] else None,
        "2_opportunity_to_abandon": scheduling["buckets"]["cancel"][0] if scheduling["buckets"]["cancel"] else None,
        "3_deserves_more_investment": scheduling["buckets"]["accelerate"][0] if scheduling["buckets"]["accelerate"] else None,
        "4_country_to_prioritize": {"value": None, "reason": _COUNTRY_DEFERRAL_REASON},
        "5_market_becoming_saturated": top_saturated,
        "6_niche_becoming_stronger": top_strengthening,
        "7_best_ai_model_per_department": ai_orchestrator.resource_allocation_status(),
        "8_highest_real_roi_products": sorted(
            [e for e in pipeline["entries"] if isinstance(e.get("estimated_profit"), dict) and e["estimated_profit"].get("maturity") == "REAL"],
            key=lambda e: e["estimated_profit"].get("net_profit_after_fees") or 0, reverse=True,
        )[:10],
        "9_pipelines_wasting_resources": {
            "quality_review": missions_board["buckets"]["QUALITY REVIEW"],
            "note": "فرص حقيقية فشلت Dual Inspection وسُجِّلت في QUARANTINE.md — استهلكت تكلفة إنتاج حقيقية بلا مبيعة",
        },
        "10_next_commercial_experiment": {
            "scheduler_run_now": scheduling["buckets"]["run_now"],
            "evidence_gated_recommendations": recommendations.get("recommendations", []),
        },
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def capital_allocation_snapshot(decisions_path=None, board_path=None, alerts_path=None,
                                 reopen_log_path=None, evidence_path=None):
    """Real, DESCRIPTIVE snapshot of where real opportunities/evidence
    currently concentrate across the 10 named functions — never a
    fabricated dollar budget. This factory has no live worker pool or
    payroll to actually reallocate; the honest analog is reporting
    where real attention already is."""
    import portfolio_engine
    import factory_orchestrator as fo
    import market_evidence
    from decision_engine import ranking

    all_decisions = ranking.rank_all(path=decisions_path)
    accepted = [d for d in all_decisions if d.get("status") == "ACCEPTED" and d.get("niche")]
    not_yet_decided = [d for d in all_decisions if d.get("status") not in ("ACCEPTED", "REJECTED") and d.get("niche")]

    class_counts = {}
    for d in accepted:
        decision = fo.find_decision(d["niche"], decisions_path=decisions_path)
        cls = portfolio_engine.classify_portfolio_class(decision) if decision else "Unclassified"
        class_counts[cls] = class_counts.get(cls, 0) + 1

    real_evidence_niches = sum(
        1 for d in accepted if list(market_evidence.read_evidence(niche=d["niche"], evidence_path=evidence_path))
    )

    return {
        "Research": {"count": len(not_yet_decided), "basis": "قرارات حقيقية قيد التقييم، لم تُقبل أو تُرفض بعد"},
        "Production": {"count": class_counts.get("Enterprise Automation", 0) + class_counts.get("Premium SaaS", 0), "basis": "فرص مقبولة فعلاً في فئات إنتاج نشطة"},
        "Automation": {"count": class_counts.get("Enterprise Automation", 0), "basis": "فئة Enterprise Automation الحقيقية"},
        "Marketing": {"value": "SEO metadata only", "reason": "لا قدرة تسويقية حقيقية أبعد من ذلك اليوم (ADR-108)"},
        "Publishing": {"count": sum(1 for d in accepted), "basis": "كل فرصة مقبولة فعلاً مؤهَّلة للنشر عبر distributor.py"},
        "Sales": {"count": real_evidence_niches, "basis": "فرص مقبولة فعلاً بدليل سوق حقيقي مسجَّل"},
        "Commercial Intelligence": {"count": real_evidence_niches, "basis": "نفس عدد الأدلة الحقيقية أعلاه"},
        "China Division": {"count": 0, "reason": _COUNTRY_DEFERRAL_REASON},
        "Enterprise Division": {"count": class_counts.get("Enterprise Automation", 0) + class_counts.get("AI APIs", 0), "basis": "فئتا Enterprise Automation + AI APIs الحقيقيتان"},
        "Premium Products": {"count": class_counts.get("Premium SaaS", 0) + class_counts.get("Premium Digital Products", 0), "basis": "فئتا Premium SaaS + Premium Digital Products الحقيقيتان"},
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def ceo_dashboard(decisions_path=None, board_path=None, alerts_path=None,
                   reopen_log_path=None, evidence_path=None, timeline_path=None,
                   outcomes_path=None, db_file=None):
    """The 8 real, named Mission Control fields — thin reuse only.
    Company Health is deliberately NOT re-derived here (GET /health is
    already the real, live view); referenced, not duplicated."""
    import investment_pipeline
    import scheduler
    import growth_engine
    from channels import ledger

    pipeline = investment_pipeline.build_investment_pipeline(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path, limit=10,
    )
    scheduling = scheduler.decide_next_actions(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )

    return {
        "company_health": {"value": None, "reason": "GET /health (lib/health_checks.js) هو المصدر الحقيقي الحي — غير مُعاد اشتقاقه هنا"},
        "capital_allocation": capital_allocation_snapshot(
            decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        ),
        "growth_rate": growth_engine.growth_forecast(evidence_path=evidence_path),
        "revenue_trend": ledger.revenue_trend(),
        "top_opportunities": pipeline["entries"],
        "top_risks": {"stop": scheduling["buckets"]["stop"], "cancel": scheduling["buckets"]["cancel"]},
        "current_strategic_priority": scheduling["buckets"]["run_now"][0] if scheduling["buckets"]["run_now"] else None,
        "next_executive_decision": scheduling["buckets"]["accelerate"][0] if scheduling["buckets"]["accelerate"] else (
            scheduling["buckets"]["run_now"][0] if scheduling["buckets"]["run_now"] else None
        ),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
