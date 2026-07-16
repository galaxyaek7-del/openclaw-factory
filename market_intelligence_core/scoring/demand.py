"""
Demand scorer (ADR-049) — thin adapter over profit_oracle._score_demand()
(ADR-038). The real implementation (seasonality date-check, real HN/
GitHub external_signal handling, keyword-count fallback) stays exactly
where it is, untouched and still independently tested by
tests/test_opportunity_score.py — this module only repackages its
already-correct output into the Score contract.
"""

import profit_oracle

from market_intelligence_core.registry import register_scorer
from market_intelligence_core.types import CONFIDENCE_SCALE, Score


@register_scorer("demand")
def compute(context):
    demand_score, notes = profit_oracle._score_demand(context.niche, context.now, context.external_signal)
    confidence = CONFIDENCE_SCALE["high"] if context.external_signal else CONFIDENCE_SCALE["low"]
    return Score(
        dimension="demand",
        raw_data={"notes": notes, "external_signal_used": bool(context.external_signal)},
        normalized_score=demand_score,
        confidence=confidence,
        explanation="؛ ".join(notes),
    )
