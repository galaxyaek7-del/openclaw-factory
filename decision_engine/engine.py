"""
Decision Engine — the orchestrator (ADR-050).

evaluate_and_decide() is Signal -> Evaluation -> Decision:
  1. market_intelligence_core.evaluate_opportunity() — real evaluation,
     unchanged (dimension_scores, ai_ceo verdict, real customer-pain/
     competitor evidence).
  2. profit_oracle.opportunity_score() — the existing, tested, tier-aware
     composite ranking score (ADR-026) and its MIN_OPPORTUNITY_SCORE gate.
     evaluate_opportunity()'s own analysis dict computes this internally
     but does not expose it (it only keeps the components) — called again
     here rather than re-deriving its formula. Cheap and synchronous, so
     calling it twice costs nothing real.

A decision requires BOTH real gates to agree before ACCEPTED: the AI CEO's
evidence-based verdict AND the tier-aware composite floor. When they
disagree, the decision is DEFERRED, never silently resolved one way.
"""

from datetime import datetime, timezone

import profit_oracle
from market_intelligence_core import core as market_intelligence_core

from decision_engine import store
from decision_engine.types import Decision, make_decision_id


def _derive_status(ai_ceo_decision, opportunity_score_accepted):
    if ai_ceo_decision in ("REJECT", "PIVOT"):
        return "REJECTED"
    if ai_ceo_decision in ("WAIT", "IMPROVE"):
        return "DEFERRED"
    # ai_ceo_decision == "BUILD"
    return "ACCEPTED" if opportunity_score_accepted else "DEFERRED"


def evaluate_and_decide(niche, external_signal=None, tier="tier4", max_results=10,
                         analysis_db_file=None, decisions_path=None, precomputed_analysis=None):
    """Runs the full Signal -> Evaluation -> Decision path for one niche and
    records the result permanently (append-only, never overwritten).

    precomputed_analysis (ADR-051): when the caller already has a fresh
    evaluate_opportunity() result (e.g. the Executive Orchestrator, which
    runs the market_intelligence stage immediately before the decision
    stage in the same cycle), pass it here to skip a second, redundant
    live network round-trip. Omitting it (every caller before this
    parameter existed) reproduces today's exact behavior unchanged."""
    analysis = precomputed_analysis if precomputed_analysis is not None else market_intelligence_core.evaluate_opportunity(
        niche, external_signal=external_signal, tier=tier, max_results=max_results,
        analysis_db_file=analysis_db_file,
    )

    if "error" in analysis:
        decision = Decision(
            decision_id=make_decision_id(analysis.get("niche", ""), tier, analysis["analyzed_at"]),
            niche=analysis.get("niche", ""),
            tier=tier,
            decided_at=analysis["analyzed_at"],
            status="REJECTED",
            ai_ceo_decision=analysis["ai_ceo"]["decision"],
            opportunity_score=None,
            opportunity_score_accepted=None,
            reasoning=[analysis["error"]],
            evaluation_snapshot=analysis,
            external_signal=external_signal,
        )
        store.append_decision(decision, path=decisions_path)
        return decision

    composite = profit_oracle.opportunity_score(niche, tier=tier, external_signal=external_signal)
    ai_ceo = analysis["ai_ceo"]
    status = _derive_status(ai_ceo["decision"], composite["accepted"])

    reasoning = list(ai_ceo["evidence"])
    reasoning.append(
        f"Opportunity Score (ADR-026): {composite['opportunity_score']}/100, "
        f"{'>= ' if composite['accepted'] else '< '}{composite['min_required']} المطلوب (tier={tier})"
    )
    if ai_ceo["decision"] == "BUILD" and not composite["accepted"]:
        reasoning.append("تعارض بين بوابتين مستقلتين: AI CEO أوصى بالبناء لكن Opportunity Score لم يعبر الحد — تأجيل، لا قبول أحادي الجانب")

    decision = Decision(
        decision_id=make_decision_id(niche, tier, analysis["analyzed_at"]),
        niche=analysis["niche"],
        tier=tier,
        decided_at=analysis["analyzed_at"],
        status=status,
        ai_ceo_decision=ai_ceo["decision"],
        opportunity_score=composite["opportunity_score"],
        opportunity_score_accepted=composite["accepted"],
        reasoning=reasoning,
        evaluation_snapshot=analysis,
        external_signal=external_signal,
    )
    store.append_decision(decision, path=decisions_path)
    return decision
