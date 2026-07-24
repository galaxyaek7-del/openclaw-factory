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
from product_families.mapping import resolve_product_family


def _derive_status(ai_ceo_decision, opportunity_score_accepted):
    if ai_ceo_decision in ("REJECT", "PIVOT"):
        return "REJECTED"
    if ai_ceo_decision in ("WAIT", "IMPROVE"):
        return "DEFERRED"
    # ai_ceo_decision == "BUILD"
    return "ACCEPTED" if opportunity_score_accepted else "DEFERRED"


def evaluate_and_decide(niche, external_signal=None, tier="tier4", max_results=10,
                         analysis_db_file=None, decisions_path=None, precomputed_analysis=None,
                         ladder=None, product_family=None):
    """Runs the full Signal -> Evaluation -> Decision path for one niche and
    records the result permanently (append-only, never overwritten).

    product_family (Packaging Architecture Plan §1/§2, Phase A, 2026-07-18):
    an explicit family always wins; with none given, resolved from `ladder`
    via product_families.mapping.resolve_product_family()'s documented
    default table. Omitting it (every caller before this parameter existed)
    still resolves a family whenever `ladder` is known — this is additive
    to the Decision record only; orchestrator/engines/production.py falls
    back to its own unchanged behavior whenever the resolved family has no
    registered adapter yet, so no real behavior changes until a family
    module actually exists.

    precomputed_analysis (ADR-051): when the caller already has a fresh
    evaluate_opportunity() result (e.g. the Executive Orchestrator, which
    runs the market_intelligence stage immediately before the decision
    stage in the same cycle), pass it here to skip a second, redundant
    live network round-trip. Omitting it (every caller before this
    parameter existed) reproduces today's exact behavior unchanged.

    ladder (ADR-076, Decision Surface Reconciliation, 2026-07-18): when the
    niche carries a Strategic Production Priority Ladder rank
    (MASTER_CHARTER.md §2 — market_hunter.py tags every real candidate with
    one), the composite gate is profit_oracle.ladder_opportunity_score()
    (ADR-066) instead of the old tier-based opportunity_score() (ADR-026)
    — this is the fix for the divergence ENGINEERING_ASSESSMENT_20260718.md
    found: the automatic tick (factory_loop.js's huntGolden(), ADR-070) was
    already ladder-aware; this path was not. Omitting ladder (every caller
    before this parameter existed) reproduces the exact prior behavior —
    the old tier-based gate — unchanged."""
    resolved_family = resolve_product_family(ladder, product_family)
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
            ladder=ladder,
            product_family=resolved_family,
        )
        store.append_decision(decision, path=decisions_path)
        return decision

    if ladder:
        composite = profit_oracle.ladder_opportunity_score(niche, ladder=ladder, external_signal=external_signal)
        composite_score = composite["ladder_score"]
        composite_accepted = composite["accepted"]
        composite_reason = composite["reason"]
        score_label = "Ladder Opportunity Score (ADR-066)"
        # Opportunity Rejection Investigation (2026-07-22), mission point 7:
        # an accepted opportunity must include scalability + long-term
        # strategic value. ladder_opportunity_score() already computes
        # recurring_revenue_potential/reusability (the real per-ladder
        # proxies for those) but they were silently discarded before this
        # fix -- only composite_score/composite_accepted were kept, same
        # "computed then dropped" pattern found and fixed twice already
        # today (record_ladder_decision(), analyze_opportunity()).
        analysis["ladder_components"] = composite.get("components")
    else:
        composite = profit_oracle.opportunity_score(niche, tier=tier, external_signal=external_signal)
        composite_score = composite["opportunity_score"]
        composite_accepted = composite["accepted"]
        composite_reason = composite["reason"]
        score_label = "Opportunity Score (ADR-026)"

    ai_ceo = analysis["ai_ceo"]
    status = _derive_status(ai_ceo["decision"], composite_accepted)

    # Zero-assumption audit follow-up (High finding): this used to rebuild
    # its own string comparing composite['opportunity_score'] (tier-weighted)
    # against composite['min_required'] (the flat MIN_OPPORTUNITY_SCORE
    # constant) — the exact same bug already fixed in profit_oracle.py's own
    # `reason` field (which compares raw vs. tier-adjusted raw_floor, the
    # comparison `accepted` is actually decided by). For any tier where
    # tier_weight != tier4's 0.8, this produced a false inequality (e.g.
    # "88.6/100, < 65" for a value that is not, in fact, less than 65) — a
    # real bug already found live in this exact codebase's tier1 records
    # (data/decisions.jsonl). Reusing composite['reason'] directly instead
    # of re-deriving it here means this can never drift out of sync again.
    reasoning = list(ai_ceo["evidence"])
    reasoning.append(f"{score_label}: {composite_reason}")
    if ai_ceo["decision"] == "BUILD" and not composite_accepted:
        reasoning.append("تعارض بين بوابتين مستقلتين: AI CEO أوصى بالبناء لكن Opportunity Score لم يعبر الحد — تأجيل، لا قبول أحادي الجانب")

    decision = Decision(
        decision_id=make_decision_id(niche, tier, analysis["analyzed_at"]),
        niche=analysis["niche"],
        tier=tier,
        decided_at=analysis["analyzed_at"],
        status=status,
        ai_ceo_decision=ai_ceo["decision"],
        opportunity_score=composite_score,
        opportunity_score_accepted=composite_accepted,
        reasoning=reasoning,
        evaluation_snapshot=analysis,
        external_signal=external_signal,
        ladder=ladder,
        product_family=resolved_family,
    )
    store.append_decision(decision, path=decisions_path)
    return decision


# ADR-076 (Decision Surface Reconciliation, 2026-07-18): the fast-path
# recorder — market_hunter.py's hunt_market() already computes a real
# profit_oracle.ladder_opportunity_score() result for every candidate it
# scans (accepted or not); this writes that already-computed result into
# the SAME single source of truth (data/decisions.jsonl) evaluate_and_decide()
# above writes to, via the same Decision type and store — so
# decision_engine/ranking.py and mission_control_api.py's Decision Queue
# (both read data/decisions.jsonl directly, unchanged by this ADR) reflect
# every real accept/reject decision, regardless of which of the two real
# decision paths produced it. Deliberately does NOT run live AI-CEO
# evidence gathering itself (that stays the separate, heavier
# evaluate_and_decide() path, still available for deliberate manual
# review) — ai_ceo_decision is honestly recorded as "N/A", never a
# fabricated verdict.
def record_ladder_decision(niche, ladder, ladder_result, decisions_path=None, product_family=None):
    """ladder_result: the exact dict profit_oracle.ladder_opportunity_score()
    already returned for this niche — never recomputed here, so this can
    never silently disagree with the score the caller actually acted on.

    product_family (Packaging Architecture Plan §1, Phase A, 2026-07-18):
    an explicit family always wins; with none given, resolved from
    `ladder` via the same product_families.mapping.resolve_product_family()
    evaluate_and_decide() uses — market_hunter.py's fast discovery path
    and the deliberate manual-review path never diverge on this either."""
    now = datetime.now(timezone.utc).isoformat()
    decision = Decision(
        decision_id=make_decision_id(niche, ladder or "kdp_books", now),
        niche=niche,
        tier="tier4",  # every real market_hunter.py candidate is sourced as tier4 today (ADR-026's meaning, unchanged) — a separate axis from ladder
        decided_at=now,
        status="ACCEPTED" if ladder_result.get("accepted") else "REJECTED",
        ai_ceo_decision="N/A",
        opportunity_score=ladder_result.get("ladder_score"),
        opportunity_score_accepted=ladder_result.get("accepted"),
        reasoning=[ladder_result.get("reason", "")],
        evaluation_snapshot={
            "ladder": ladder,
            "price": ladder_result.get("price"),
            "components": ladder_result.get("components"),
            # Opportunity Intelligence Round 2 (2026-07-22): ladder_result
            # (profit_oracle.ladder_opportunity_score()) already computes
            # these -- they were silently discarded before persisting here,
            # the same "real data computed then thrown away" pattern
            # ADR-041/043 found elsewhere. Purely additive: 3 new keys,
            # nothing existing changed. .get() so callers on an older
            # ladder_result shape (pre-defensibility) degrade to None,
            # never crash.
            "risk": ladder_result.get("risk"),
            "confidence": ladder_result.get("confidence"),
            "defensibility": ladder_result.get("defensibility"),
            # Strategic Opportunity Intelligence Engine (2026-07-22):
            # market_signal/ai_leverage; components (above) now also
            # carries automation_potential -- persisted proactively this
            # time, same "computed then dropped" pattern already fixed
            # reactively three times this week.
            "market_signal": ladder_result.get("market_signal"),
            "ai_leverage": ladder_result.get("ai_leverage"),
            # Proof of Payment doctrine (ADR-121, 2026-07-24): the real
            # cited evidence ladder_opportunity_score() already computed
            # -- persisted proactively this time rather than silently
            # discarded, same "computed then dropped" pattern this
            # function's own history above was fixed reactively for.
            "payment_evidence": ladder_result.get("payment_evidence"),
        },
        external_signal=None,
        ladder=ladder,
        decision_path="ladder_fast_gate",
        product_family=resolve_product_family(ladder, product_family),
    )
    store.append_decision(decision, path=decisions_path)
    return decision
