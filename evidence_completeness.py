# Evidence Completeness Engine (ADR-127, 2026-07-25).
#
# Founder directive: "Unknown" must never automatically behave like
# "False". The 10-condition GALAXY FORGE PRODUCT STRATEGY gates
# (ADR-121/122/126) already refuse to treat absent evidence as a pass --
# but for the founder's OWN purpose (deciding whether to invest real
# research effort before finalizing a rejection), those gates collapse
# two genuinely different situations into the same boolean False:
# "we checked and it's bad" and "we haven't checked yet". This module
# adds a real, parallel 4-state view -- VERIFIED_TRUE / VERIFIED_FALSE /
# UNKNOWN / NOT_APPLICABLE -- over the exact same real fields
# profit_oracle.ladder_opportunity_score() already computes, never a
# second, recomputed, or fabricated scoring pass.
#
# "No live query inside scoring" (the same architectural principle
# _score_defensibility()/_score_market_signal()/_score_urgency() already
# established): this module never triggers a live external call from
# inside classify_criteria() or assess() -- those only read an
# ALREADY-COMPUTED ladder_opportunity_score() result. Live evidence
# acquisition is a separate, explicit, deliberate step
# (acquire_missing_evidence()) a caller invokes once per niche when they
# want the deeper research pass -- never an automatic side effect of
# scoring, matching ADR-122's own documented reasoning for declining to
# auto-wire pain-evidence gathering into every hunt_market() candidate
# (~30 real external API calls per hunt otherwise).
#
# Real, honest scope: only 2 of the 11 real criteria below have a
# genuine automated acquisition path today (difficult_to_copy via
# competitor_discovery.py's real, cached GitHub+HN search; pain_severity
# via market_intelligence_engine.py's real, UNCACHED GitHub+HN+Stack
# Overflow search, opt-in only because of its real per-call cost). Every
# other Unknown criterion gets an honest "no real automated method
# exists yet" research recommendation instead of a fabricated search --
# see RESEARCH_ACTIONS below.

import competitor_discovery
import market_intelligence_engine

VERIFIED_TRUE = "VERIFIED_TRUE"
VERIFIED_FALSE = "VERIFIED_FALSE"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"

STATES = (VERIFIED_TRUE, VERIFIED_FALSE, UNKNOWN, NOT_APPLICABLE)

# The 11 real criteria this factory can name today: the founder's own 10
# (GALAXY FORGE PRODUCT STRATEGY, ADR-126) plus Pain Severity (ADR-122's
# own gate -- not literally one of the founder's 10 numbered conditions,
# but part of the same real decision hierarchy and just as capable of
# being genuinely Unknown).
CRITERIA = (
    "proof_of_payment",
    "pain_severity",
    "low_or_moderate_competition",
    "difficult_to_copy",
    "premium_pricing_potential",
    "global_scalability",
    "long_term_strategic_value",
    "ai_significant_advantage",
    "high_profit_margin",
    "high_commercial_value",
    "continuous_improvement_potential",
)

# Real, concrete, honest recommendation per criterion -- "REAL ACQUIRABLE"
# ones have a real function this module can actually call
# (acquire_missing_evidence() below); every other one names the real
# manual research this factory has no automated substitute for yet,
# never a fabricated "search X" that doesn't exist.
RESEARCH_ACTIONS = {
    "proof_of_payment": (
        "لا بحث آلي حقيقي متاح بعد لدليل الدفع (صفحات تسعير، إعلانات وظائف، أسواق، تسعير وكالات) — "
        "يحتاج بحثاً يدوياً حقيقياً ثم تسجيلاً عبر market_evidence.record_evidence()"
    ),
    "pain_severity": (
        "REAL ACQUIRABLE — market_intelligence_engine.analyze_customer_pain(niche): بحث حي حقيقي عبر "
        "GitHub Issues + Hacker News + Stack Overflow، بلا تخزين مؤقت (تكلفة/حد معدل حقيقيان — استدعاء صريح فقط)"
    ),
    "low_or_moderate_competition": "مؤشر حتمي حقيقي دائماً متاح (تقرير محفوظ أو تقدير كلمات) — لا يكون Unknown فعلياً",
    "difficult_to_copy": (
        "REAL ACQUIRABLE — competitor_discovery.get_or_refresh_competitors(niche): بحث حي حقيقي مخزَّن "
        "عبر GitHub + Hacker News (يُعاد استخدام النسخة المخزَّنة حتى تُصبح قديمة فعلياً)"
    ),
    "premium_pricing_potential": "مؤشر حتمي حقيقي دائماً متاح (butter_price) — لا يكون Unknown فعلياً",
    "global_scalability": "مؤشر حتمي حقيقي دائماً متاح (ثوابت المسار الموثَّقة) — لا يكون Unknown فعلياً",
    "long_term_strategic_value": "مؤشر حتمي حقيقي دائماً متاح (ثوابت المسار الموثَّقة) — لا يكون Unknown فعلياً",
    "ai_significant_advantage": (
        "لا بيانات ناقصة هنا فعلياً — هذا تصنيف نصي حتمي لنص النيتش نفسه؛ Unknown تعني أن النص لا يحتوي أي "
        "كلمة مفتاحية واضحة بأي اتجاه — أعد صياغة وصف المنتج إن كانت الاستفادة من AI حقيقية فعلاً، لا يوجد بحث آلي بديل"
    ),
    "high_profit_margin": "مؤشر حتمي حقيقي دائماً متاح (تقدير هامش/تسعير) — لا يكون Unknown فعلياً",
    "high_commercial_value": "لا مؤشر حقيقي لهذا البُعد في هذا المصنع اليوم — فجوة حقيقية معروفة (ADR-126 audit)، لا اختلاق",
    "continuous_improvement_potential": "لا مؤشر حقيقي لهذا البُعد في هذا المصنع اليوم — فجوة حقيقية معروفة (ADR-126 audit)، لا اختلاق",
}

# Only these 2 have acquire_missing_evidence() actually do something real.
REAL_ACQUIRABLE_CRITERIA = ("pain_severity", "difficult_to_copy")


def _classify_bool_or_none(value_is_none, passes):
    if value_is_none:
        return UNKNOWN
    return VERIFIED_TRUE if passes else VERIFIED_FALSE


def classify_criteria(ladder_result):
    """Reads ONLY ladder_result's own already-computed real fields (the
    output of profit_oracle.ladder_opportunity_score()) -- never triggers
    a new computation or live query. Returns {criterion: {"state":...,
    "value":..., "note":...}} for all 11 real criteria."""
    components = ladder_result.get("components") or {}
    defensibility = ladder_result.get("defensibility") or {}
    ai_leverage = ladder_result.get("ai_leverage") or {}
    urgency = ladder_result.get("urgency") or {}
    payment_evidence = ladder_result.get("payment_evidence") or []

    urgency_score = urgency.get("score")
    ai_leverage_score = ai_leverage.get("score")
    defensibility_level = defensibility.get("level")
    competition_favorability = components.get("competition_favorability")
    profit_potential = components.get("profit_potential")
    recurring = components.get("recurring_revenue_potential")
    reusability = components.get("reusability")
    price = ladder_result.get("price")

    out = {}

    out["proof_of_payment"] = {
        "state": VERIFIED_TRUE if len(payment_evidence) > 0 else UNKNOWN,
        "value": len(payment_evidence),
        "note": (
            f"{len(payment_evidence)} حدث دليل دفع حقيقي مسجَّل" if payment_evidence
            else "صفر أحداث دليل دفع مسجَّلة — لم يُبحث بعد فعلياً، وليس تأكيداً أن لا سوق حقيقي موجود"
        ),
    }

    out["pain_severity"] = {
        "state": _classify_bool_or_none(urgency_score is None, (urgency_score or 0) >= 25),
        "value": urgency_score,
        "note": urgency.get("note"),
    }

    # Always real/deterministic (a saved report, a passed external
    # signal, or a keyword-count fallback -- never None) -- see
    # profit_oracle._score_competition()'s own docstring.
    out["low_or_moderate_competition"] = {
        "state": VERIFIED_TRUE if (competition_favorability or 0) >= 60 else VERIFIED_FALSE,
        "value": competition_favorability,
        "note": f"competition_favorability {competition_favorability}/100 (الحد: 60)",
    }

    out["difficult_to_copy"] = {
        "state": (
            UNKNOWN if defensibility_level in (None, "Unknown")
            else VERIFIED_FALSE if defensibility_level == "منخفضة"
            else VERIFIED_TRUE
        ),
        "value": defensibility_level,
        "note": defensibility.get("note"),
    }

    out["premium_pricing_potential"] = {
        "state": VERIFIED_TRUE if (price or 0) >= 97 else VERIFIED_FALSE,
        "value": price,
        "note": f"السعر الحقيقي ${price} (الحد الأدنى: $97)",
    }

    out["global_scalability"] = {
        "state": VERIFIED_TRUE if (reusability or 0) >= 55 else VERIFIED_FALSE,
        "value": reusability,
        "note": f"reusability {reusability}/100 (الحد: 55) — نفس مكوّن long_term_strategic_value، ليس حساباً ثانياً",
    }

    out["long_term_strategic_value"] = {
        "state": VERIFIED_TRUE if (recurring or 0) >= 55 and (reusability or 0) >= 55 else VERIFIED_FALSE,
        "value": {"recurring": recurring, "reusability": reusability},
        "note": f"recurring={recurring}/reusability={reusability} (الحد: 55/55)",
    }

    out["ai_significant_advantage"] = {
        "state": _classify_bool_or_none(ai_leverage_score is None, (ai_leverage_score or 0) >= 50),
        "value": ai_leverage_score,
        "note": ai_leverage.get("note"),
    }

    out["high_profit_margin"] = {
        "state": VERIFIED_TRUE if (profit_potential or 0) >= 50 else VERIFIED_FALSE,
        "value": profit_potential,
        "note": f"profit_potential {profit_potential}/100 (الحد: 50)",
    }

    # Genuine gaps (ADR-126 audit): no real per-opportunity signal exists
    # anywhere in this factory for these 2 -- always Unknown, never
    # fabricated, never gated.
    out["high_commercial_value"] = {"state": UNKNOWN, "value": None, "note": RESEARCH_ACTIONS["high_commercial_value"]}
    out["continuous_improvement_potential"] = {"state": UNKNOWN, "value": None, "note": RESEARCH_ACTIONS["continuous_improvement_potential"]}

    return out


def evidence_coverage_report(classification):
    """Real, computed-not-invented aggregate: coverage% = the share of
    the 11 real criteria that are actually VERIFIED (true or false) --
    NOT_APPLICABLE counts as covered (nothing more to know), UNKNOWN does
    not."""
    total = len(classification)
    verified = sum(1 for c in classification.values() if c["state"] in (VERIFIED_TRUE, VERIFIED_FALSE))
    not_applicable = sum(1 for c in classification.values() if c["state"] == NOT_APPLICABLE)
    unknown = sum(1 for c in classification.values() if c["state"] == UNKNOWN)
    covered = verified + not_applicable
    coverage_pct = round(100.0 * covered / total, 1) if total else 0.0
    missing_evidence = [k for k, v in classification.items() if v["state"] == UNKNOWN]
    return {
        "coverage_pct": coverage_pct,
        "verified_count": verified,
        "unknown_count": unknown,
        "not_applicable_count": not_applicable,
        "total_count": total,
        "missing_evidence": missing_evidence,
    }


def confidence_from_coverage(coverage_pct):
    """The real, disclosed, simplest honest mapping: confidence IS how
    much of the real evidence has actually been verified, not a second,
    separately-invented percentage. See ADR-127 for why a more elaborate
    curve was deliberately not built."""
    return coverage_pct


def recommended_research_actions(classification):
    """Real, concrete text per missing (UNKNOWN) criterion -- from
    RESEARCH_ACTIONS, never invented per-call."""
    return {
        k: RESEARCH_ACTIONS.get(k, "لا توصية بحث محدَّدة مسجَّلة لهذا المعيار")
        for k, v in classification.items() if v["state"] == UNKNOWN
    }


def estimate_value_if_verified(ladder_result, classification):
    """NOT a fabricated projection: ladder_score/price are already real,
    already-computed numbers that gates never change (only accept/reject
    do) -- so "what would this be worth if the Unknowns resolve
    favorably" is literally the SAME real ladder_score/price this niche
    already has, explicitly conditioned on which real criteria are still
    Unknown. Never a different, invented number."""
    unknown_criteria = [k for k, v in classification.items() if v["state"] == UNKNOWN]
    return {
        "ladder_score": ladder_result.get("ladder_score"),
        "price": ladder_result.get("price"),
        "condition": (
            f"لو تحوَّلت المعايير التالية إلى VERIFIED_TRUE: {', '.join(unknown_criteria)} — "
            f"يبقى ladder_score/price الحقيقيان الحاليان كما هما (البوابات لا تُغيّر القيمة، فقط قرار القبول/الرفض)"
            if unknown_criteria else "لا معايير Unknown متبقية — هذا التقدير غير مطلوب"
        ),
    }


# Below this real coverage floor, a real reject is not yet honest if
# there's still real, actionable research to do first -- RESEARCH_REQUIRED
# instead. Disclosed, not tuned/invented: roughly "more than 2 of the 11
# real criteria still Unknown" (9/11 ≈ 82%). See ADR-127 for the founder
# discussion this threshold should be revisited under.
DEFAULT_RESEARCH_THRESHOLD_PCT = 80.0


def assess(niche, ladder_result, research_threshold=DEFAULT_RESEARCH_THRESHOLD_PCT):
    """Top-level real orchestration -- classify, compute coverage, decide
    the real lifecycle stage. Never recomputes ladder_opportunity_score()
    itself (FINAL_SCORING has already happened by the time this is
    called); this only decides whether that real verdict is honest to
    finalize yet, or whether real, actionable research should happen
    first."""
    classification = classify_criteria(ladder_result)
    coverage = evidence_coverage_report(classification)
    confidence = confidence_from_coverage(coverage["coverage_pct"])
    actions = recommended_research_actions(classification)
    value_if_verified = estimate_value_if_verified(ladder_result, classification)

    accepted = bool(ladder_result.get("accepted"))
    has_real_acquirable_unknown = any(k in REAL_ACQUIRABLE_CRITERIA for k in coverage["missing_evidence"])

    if accepted:
        lifecycle_status = "ACCEPTED"
    elif coverage["coverage_pct"] < research_threshold and has_real_acquirable_unknown:
        lifecycle_status = "RESEARCH_REQUIRED"
    else:
        lifecycle_status = "REJECTED"

    return {
        "niche": niche,
        "ladder": ladder_result.get("ladder"),
        "lifecycle_status": lifecycle_status,
        "score": ladder_result.get("ladder_score"),
        "confidence_pct": confidence,
        "confidence_reason": (
            f"تم التحقق من {coverage['coverage_pct']}% فقط من الأدلة المطلوبة"
            if coverage["coverage_pct"] < 100 else "تم التحقق من كل الأدلة المطلوبة الحقيقية"
        ),
        "coverage": coverage,
        "classification": classification,
        "recommended_research_actions": actions,
        "estimated_value_if_verified": value_if_verified,
        "ladder_reason": ladder_result.get("reason"),
    }


def acquire_missing_evidence(niche, classification, db_file=None, gather_pain=False, evidence_path=None):
    """Real, deliberate acquisition -- a caller invokes this ONCE per
    niche, never automatically per hunt-tick. Only touches the 2 real
    criteria with a genuine automated path (REAL_ACQUIRABLE_CRITERIA);
    every other Unknown criterion is reported honestly as not having one.
    gather_pain defaults to False: unlike competitor_discovery's cached
    search, analyze_customer_pain() is a real, UNCACHED live call every
    time -- opt-in only, same cost-consciousness ADR-122 already
    established."""
    missing = [k for k, v in classification.items() if v["state"] == UNKNOWN]
    results = {}

    for criterion in missing:
        if criterion == "difficult_to_copy" and criterion in missing:
            try:
                refreshed = competitor_discovery.get_or_refresh_competitors(niche, db_file=db_file)
                results[criterion] = {"attempted": True, "acquired": True, "result": refreshed}
            except Exception as e:
                results[criterion] = {"attempted": True, "acquired": False, "error": str(e)}
        elif criterion == "pain_severity" and gather_pain:
            try:
                pain = market_intelligence_engine.analyze_customer_pain(niche)
                results[criterion] = {"attempted": True, "acquired": True, "result": pain}
            except Exception as e:
                results[criterion] = {"attempted": True, "acquired": False, "error": str(e)}
        else:
            results[criterion] = {
                "attempted": False, "acquired": False,
                "note": RESEARCH_ACTIONS.get(criterion, "لا إجراء بحث آلي مسجَّل لهذا المعيار"),
            }

    return results


if __name__ == "__main__":
    import argparse
    import json
    import sys

    import profit_oracle

    parser = argparse.ArgumentParser(description="Evidence Completeness Engine — manual/CLI invocation")
    parser.add_argument("niche")
    parser.add_argument("--ladder", default="kdp_books")
    parser.add_argument("--acquire", action="store_true", help="run real evidence acquisition for acquirable Unknown criteria")
    parser.add_argument("--gather-pain", action="store_true", help="also run the real, uncached market_intelligence_engine.analyze_customer_pain() call")
    args = parser.parse_args()

    scored = profit_oracle.ladder_opportunity_score(args.niche, ladder=args.ladder)
    report = assess(args.niche, scored)

    if args.acquire:
        report["acquisition"] = acquire_missing_evidence(
            args.niche, report["classification"], gather_pain=args.gather_pain,
        )

    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    sys.exit(0)
