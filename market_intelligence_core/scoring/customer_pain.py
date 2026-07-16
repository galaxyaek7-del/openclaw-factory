"""
Customer Pain scorer (ADR-049) — thin adapter over
market_intelligence_engine.analyze_customer_pain() (ADR-043): real
GitHub Issues Search + HN Algolia search, unchanged. Reuses
context.analysis's already-fetched pain dict (the pipeline runs after
market_intelligence_engine.analyze_opportunity() already made this real
network call once) instead of fetching a second time; falls back to a
fresh call only when no analysis context is available (e.g. a scorer
exercised standalone in a test).
"""

import market_intelligence_engine

from market_intelligence_core.registry import register_scorer
from market_intelligence_core.types import CONFIDENCE_SCALE, Score

_PAIN_CONFIDENCE = {"medium": CONFIDENCE_SCALE["medium"], "low": CONFIDENCE_SCALE["low"]}


@register_scorer("customer_pain")
def compute(context):
    pain = (context.analysis or {}).get("customer_pain")
    if pain is None:
        pain = market_intelligence_engine.analyze_customer_pain(context.niche, context.max_results)

    confidence = _PAIN_CONFIDENCE.get(pain.get("confidence"), CONFIDENCE_SCALE["low"])

    return Score(
        dimension="customer_pain",
        raw_data=pain.get("real_evidence", {}),
        normalized_score=pain.get("pain_score"),  # None when genuinely no evidence — never guessed
        confidence=confidence,
        explanation=pain.get("reason", ""),
    )
