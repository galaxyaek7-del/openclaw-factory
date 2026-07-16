"""
Profit Margin scorer (ADR-049) — thin adapter over
profit_oracle._score_margin() (ADR-041): real platform fees
(config/economics.json) and real logged Groq cost
(data/ai_cost_log.jsonl) when any exists, keyword-tier price estimate
otherwise. Untouched, unchanged, still independently tested by
tests/test_opportunity_score.py.
"""

import profit_oracle

from market_intelligence_core.registry import register_scorer
from market_intelligence_core.types import CONFIDENCE_SCALE, Score


@register_scorer("profit_margin")
def compute(context):
    margin_score, notes, price = profit_oracle._score_margin(context.niche)
    has_real_ai_cost = any("متوسط تكلفة Groq حقيقية" in n for n in notes)
    confidence = CONFIDENCE_SCALE["medium"] if has_real_ai_cost else CONFIDENCE_SCALE["low"]
    return Score(
        dimension="profit_margin",
        raw_data={"notes": notes, "recommended_price": price},
        normalized_score=margin_score,
        confidence=confidence,
        explanation="؛ ".join(notes),
    )
