"""
Pricing Power scorer (ADR-049) — genuinely new: "can this niche
defensibly command a higher price", never built before this Core.

Real signal only when a saved niche_validator_v2.py Amazon report
exists for this niche (real average competitor price, via
profit_oracle._find_niche_report() — the exact same lookup
score_opportunity() already uses for competition). Otherwise honestly
DISCOVERY (normalized_score=None) — live competitor-pricing-page
scraping was evaluated and rejected as unreliable (ADR-046: 25%
extraction reliability measured against real data), so this never
attempts it and never presents a guessed price as real.
"""

import profit_oracle

from market_intelligence_core.registry import register_scorer
from market_intelligence_core.types import CONFIDENCE_SCALE, Score


@register_scorer("pricing_power")
def compute(context):
    report = profit_oracle._find_niche_report(context.niche)
    if report and report.get("status") == "success":
        avg_price = report.get("metrics", {}).get("price", {}).get("avg", 0)
        if avg_price:
            normalized_score = max(0, min(100, round(avg_price / profit_oracle.MAX_BUTTER_PRICE * 100)))
            return Score(
                dimension="pricing_power",
                raw_data={"real_avg_competitor_price": avg_price, "source": "niche_validator_v2 saved report"},
                normalized_score=normalized_score,
                confidence=CONFIDENCE_SCALE["medium"],
                explanation=(
                    f"متوسط سعر منافسين حقيقي من تقرير Amazon محفوظ: ${avg_price} — "
                    f"مقاس نسبةً لسقف ${profit_oracle.MAX_BUTTER_PRICE}"
                ),
            )

    return Score(
        dimension="pricing_power",
        raw_data={"reason": "لا تقرير Amazon محفوظ لهذا النيتش"},
        normalized_score=None,
        confidence=CONFIDENCE_SCALE["low"],
        explanation=(
            "Unknown — يحتاج بيانات أسعار منافسين حقيقية. جلب الأسعار من صفحات المنافسين حياً "
            "غير موثوق (25% نسبة استخلاص صحيحة فقط، ADR-046) فلم يُحاوَل هنا"
        ),
    )
