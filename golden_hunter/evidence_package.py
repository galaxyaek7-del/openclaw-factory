"""
Evidence package builder (ADR-060) — the 9 required fields, built
entirely from a Decision record already produced by the existing
pipeline (decision_engine.store / orchestrator.run_cycle()). Zero new
scoring: demand/competition/profit/confidence/risk are read straight off
Decision.evaluation_snapshot (market_intelligence_core, ADR-049).

Only two fields are genuinely new interpretation, both derived from
data that already exists in the snapshot:
  - implementation difficulty: relabels the existing "execution"
    dimension score (ADR-049's execution scorer — book_engine fit,
    already computed) rather than inventing a second difficulty metric.
  - "why this opportunity exists now": a short, evidence-cited sentence
    built only from fields already in the snapshot (demand_pattern,
    whether a real external_signal was supplied, real customer-pain
    evidence counts) — never an invented narrative.
"""


def _implementation_difficulty(evaluation_snapshot):
    execution = (evaluation_snapshot.get("dimension_scores") or {}).get("execution")
    if not execution or execution.get("normalized_score") is None:
        return {"level": "Unknown", "evidence": "لا بُعد تنفيذ محسوب لهذا التقييم"}

    score = execution["normalized_score"]
    if score >= 80:
        level = "منخفضة — يناسب قدرة book_engine الحالية مباشرة"
    elif score >= 50:
        level = "متوسطة"
    else:
        level = "عالية — يتجاوز قدرة المصنع الحالية"

    return {"level": level, "evidence": execution.get("explanation", ""), "execution_score": score}


def _why_now(evaluation_snapshot, external_signal):
    reasons = []

    demand_pattern = evaluation_snapshot.get("demand_pattern") or {}
    if demand_pattern.get("pattern") == "Seasonal":
        reasons.append(f"نمط طلب موسمي حقيقي: {demand_pattern.get('reason')}")

    if external_signal:
        source = external_signal.get("source")
        if source == "github":
            reasons.append(f"إشارة حقيقية: {external_signal.get('stars')} نجمة GitHub")
        elif source == "hacker_news":
            reasons.append(f"إشارة حقيقية: {external_signal.get('points')} نقطة Hacker News")

    pain = evaluation_snapshot.get("customer_pain") or {}
    real_evidence = pain.get("real_evidence") or {}
    total_pain_signals = (real_evidence.get("github_issues_found") or 0) + (real_evidence.get("hn_discussions_found") or 0)
    if total_pain_signals:
        reasons.append(f"{total_pain_signals} دليل ألم عملاء حقيقي (GitHub Issues/HN)")

    if not reasons:
        return "لا دليل حقيقي واحد يبرِّر توقيتاً معيَّناً الآن — الفرصة تُقيَّم بلا إشارة زمنية خاصة"
    return "؛ ".join(reasons)


def _recommended_action(status, ai_ceo_decision):
    """A descriptive label reflecting a decision the pipeline ALREADY
    made (decision_engine, ADR-050) — never a new decision, never an
    auto-trigger of anything."""
    if status == "ACCEPTED":
        return "أُضيفت لطابور القرار — بانتظار تنفيذ صريح (execute_production=True) بإذن منفصل"
    if status == "REJECTED":
        return "لا تُتابَع — رفض حقيقي من AI CEO أو عتبة Opportunity Score"
    if ai_ceo_decision == "IMPROVE":
        return "راقب — فجوة فرصة متوسطة، تحتاج تمييزاً أوضح قبل البناء"
    return "راقب — أدلة حقيقية غير كافية بعد لقرار واثق"


def build_evidence_package(decision):
    """decision: a Decision.to_dict()-shaped record (from decision_engine.store)."""
    snapshot = decision.get("evaluation_snapshot") or {}

    return {
        "niche": decision.get("niche"),
        "status": decision.get("status"),
        "opportunity_score": decision.get("opportunity_score"),
        "evidence_package": snapshot,
        "demand_evidence": {
            "score": (snapshot.get("scores") or {}).get("market_demand"),
            "pattern": snapshot.get("demand_pattern"),
        },
        "competition_evidence": {
            "score": (snapshot.get("scores") or {}).get("competition_favorability"),
            "competitors": snapshot.get("competitors"),
        },
        "profit_evidence": {
            "score": (snapshot.get("scores") or {}).get("profit_potential"),
            "pricing": snapshot.get("pricing"),
        },
        "confidence": snapshot.get("confidence"),
        "risk": snapshot.get("risk"),
        "estimated_implementation_difficulty": _implementation_difficulty(snapshot),
        "why_this_opportunity_exists_now": _why_now(snapshot, decision.get("external_signal")),
        "recommended_action": _recommended_action(decision.get("status"), decision.get("ai_ceo_decision")),
    }
