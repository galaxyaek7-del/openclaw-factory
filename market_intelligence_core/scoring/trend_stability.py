"""
Trend Stability scorer (ADR-049) — thin adapter over
market_intelligence_engine.classify_demand_pattern() (ADR-043).
Seasonal is real (date-based keyword match against
profit_oracle.SEASONAL_KEYWORDS) and read as high, predictable
stability. Evergreen-with-Exploding/Declining-Unknown is honestly not
computable — this factory has only ever taken single snapshots, so
normalized_score is None (DISCOVERY), never a guessed number, exactly
matching classify_demand_pattern()'s own documented honesty.
"""

import market_intelligence_engine

from market_intelligence_core.registry import register_scorer
from market_intelligence_core.types import CONFIDENCE_SCALE, Score


@register_scorer("trend_stability")
def compute(context):
    pattern = (context.analysis or {}).get("demand_pattern")
    if pattern is None:
        pattern = market_intelligence_engine.classify_demand_pattern(context.niche, context.now)

    if pattern["pattern"] == "Seasonal":
        in_season = "في موسمه الآن" in pattern["reason"]
        # Seasonal but currently out of window is still a real, predictable
        # cycle — not unstable, just not at its peak right now.
        normalized_score = 85 if in_season else 55
        confidence = CONFIDENCE_SCALE["high"]
    else:
        normalized_score = None
        confidence = CONFIDENCE_SCALE["low"]

    return Score(
        dimension="trend_stability",
        raw_data={"pattern": pattern["pattern"]},
        normalized_score=normalized_score,
        confidence=confidence,
        explanation=pattern["reason"],
    )
