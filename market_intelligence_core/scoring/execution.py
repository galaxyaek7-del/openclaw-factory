"""
Execution scorer (ADR-049) — thin adapter over
profit_oracle._score_execution(): book_engine fit + real per-channel
automation status (config/channels.json). Not one of the 8 dimensions
explicitly requested (Demand/Competition/Profit Margin/Customer Pain/
Pricing Power/Trend Stability/Confidence/Risk), but a real,
already-existing signal profit_score's own composite depends on (10%
weight) — kept as a 9th scorer rather than silently dropped from the
new Core's view, and a live, non-contrived demonstration that the
pipeline accepts additional scoring dimensions without any other file
needing to change.
"""

import profit_oracle

from market_intelligence_core.registry import register_scorer
from market_intelligence_core.types import CONFIDENCE_SCALE, Score


@register_scorer("execution")
def compute(context):
    fit_score, notes, platform = profit_oracle._score_execution(context.niche)
    return Score(
        dimension="execution",
        raw_data={"notes": notes, "recommended_platform": platform},
        normalized_score=fit_score,
        confidence=CONFIDENCE_SCALE["high"],  # today's book_engine capability is a known fact, not an estimate
        explanation="؛ ".join(notes),
    )
