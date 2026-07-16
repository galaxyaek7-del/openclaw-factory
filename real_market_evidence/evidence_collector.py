"""
Real Market Evidence collection (ADR-058) — see package docstring for the
full boundary statement (no live Amazon scraping, ever). Sources
exclusively from profit_oracle._find_niche_report() — the exact same
real saved-report lookup profit_oracle.py's scoring already uses.
"""

import profit_oracle
from market_intelligence_core.types import CONFIDENCE_SCALE

from real_market_evidence.types import METRICS, Evidence

MAX_COMPETITION = profit_oracle.MAX_COMPETITION

_STRUCTURALLY_UNKNOWN_REASONS = {
    "best_seller_rank": "niche_validator_v2.py لا يستخرج BSR اليوم — يظهر فقط في صفحات تفاصيل المنتج الفردية، لا صفحات نتائج البحث المحفوظة",
    "marketplace_age": "يحتاج تاريخ إدراج فعلي لكل قائمة — غير مُستخرَج من لقطة صفحة نتائج بحث واحدة",
    "update_frequency": "يحتاج مراقبة متكررة عبر الزمن لنفس القوائم — لا لقطات متعددة محفوظة بعد لهذا النيتش",
    "seller_concentration": "يحتاج نسبة بائع لكل قائمة — غير مُستخرَج من صفحة نتائج البحث",
    "revenue_indicators": "أمازون لا يُظهر أرقام مبيعات/إيراد علنية أبداً — لا مصدر حقيقي ممكن بأي حال",
}


def _unknown(metric, reason):
    return Evidence(metric=metric, source="unavailable", timestamp=None, confidence=0,
                     raw_value=None, normalized_value=None, explanation=reason)


def _real(metric, timestamp, raw_value, normalized_value, explanation):
    return Evidence(metric=metric, source="niche_validator_v2 saved report", timestamp=timestamp,
                     confidence=CONFIDENCE_SCALE["high"], raw_value=raw_value,
                     normalized_value=normalized_value, explanation=explanation)


def collect_evidence(niche):
    """Returns {metric_name: Evidence} for all 10 requested metrics. Never
    raises, never guesses — a missing/malformed saved report degrades to
    all-Unknown, exactly like every other honest-degradation function in
    this factory."""
    report = profit_oracle._find_niche_report(niche)

    if not report or report.get("status") != "success":
        reason = "لا تقرير Amazon محفوظ يدوياً لهذا النيتش (niche_validator_v2.py) — لا مصدر بيانات سوق حقيقي بعد"
        return {m: _unknown(m, reason) for m in METRICS}

    timestamp = report.get("analyzed_at")
    metrics_data = report.get("metrics", {}) or {}
    total_results = metrics_data.get("total_results")
    price = metrics_data.get("price", {}) or {}
    reviews = metrics_data.get("reviews", {}) or {}
    books_analyzed = metrics_data.get("books_analyzed")

    evidence = {}

    if total_results is not None:
        evidence["amazon_search_result_count"] = _real(
            "amazon_search_result_count", timestamp, total_results, None,
            f"عدد نتائج بحث Amazon الحقيقي: {total_results:,}",
        )
    else:
        evidence["amazon_search_result_count"] = _unknown("amazon_search_result_count", "لا حقل total_results في التقرير المحفوظ")

    if books_analyzed is not None:
        evidence["competing_listings_count"] = _real(
            "competing_listings_count", timestamp, books_analyzed, None,
            f"عدد قوائم منافسة حقيقية مُحلَّلة من الصفحة المحفوظة: {books_analyzed}",
        )
    else:
        evidence["competing_listings_count"] = _unknown("competing_listings_count", "لا حقل books_analyzed في التقرير المحفوظ")

    if price.get("avg"):
        evidence["pricing_distribution"] = _real(
            "pricing_distribution", timestamp, dict(price), price.get("avg"),
            f"توزيع أسعار حقيقي: أدنى ${price.get('min')}، متوسط ${price.get('avg')}، أعلى ${price.get('max')}",
        )
    else:
        evidence["pricing_distribution"] = _unknown("pricing_distribution", "لا بيانات سعر صالحة في التقرير المحفوظ")

    if reviews.get("avg") is not None:
        evidence["review_count_distribution"] = _real(
            "review_count_distribution", timestamp, dict(reviews), reviews.get("avg"),
            f"توزيع مراجعات حقيقي: متوسط {reviews.get('avg')}، أعلى {reviews.get('max')}",
        )
    else:
        evidence["review_count_distribution"] = _unknown("review_count_distribution", "لا بيانات مراجعات صالحة في التقرير المحفوظ")

    if total_results is not None:
        saturation_pct = round(min(100, 100 * total_results / MAX_COMPETITION), 1)
        evidence["category_saturation"] = _real(
            "category_saturation", timestamp, total_results, saturation_pct,
            f"تشبُّع الفئة الحقيقي: {total_results:,} نتيجة من حد {MAX_COMPETITION:,} (profit_oracle.MAX_COMPETITION) = {saturation_pct}%",
        )
    else:
        evidence["category_saturation"] = _unknown("category_saturation", "يحتاج total_results حقيقياً لحسابه")

    for metric, reason in _STRUCTURALLY_UNKNOWN_REASONS.items():
        evidence[metric] = _unknown(metric, reason)

    return evidence


def evidence_quality_summary(niches):
    """Real tally only: across the given niches, how many of the 10
    metrics are real (confidence > 0) versus Unknown — the ONLY success
    measure this engine reports, per the explicit instruction that
    success is measured by evidence quality, never by acceptance count."""
    per_niche = {}
    total_metrics = 0
    real_metrics = 0

    for niche in niches:
        evidence = collect_evidence(niche)
        real_count = sum(1 for e in evidence.values() if e.confidence > 0)
        per_niche[niche] = {"real": real_count, "total": len(evidence)}
        total_metrics += len(evidence)
        real_metrics += real_count

    return {
        "per_niche": per_niche,
        "aggregate_real_metrics": real_metrics,
        "aggregate_total_metrics": total_metrics,
        "evidence_quality_pct": round(100 * real_metrics / total_metrics, 1) if total_metrics else 0.0,
    }
