"""
Risk scorer (ADR-049) — thin adapter over profit_oracle._score_risk()
(ADR-039): safety_filter.py's blocklist + REJECTED_NICHES.md's circuit
breaker, unchanged. Confidence reflects whether safety_filter.py
actually ran (a real, deterministic check), not the risk level itself —
a "low risk" verdict from a working filter deserves the same confidence
as a "blocked" one; only an unavailable/errored filter should lower it.
"""

import profit_oracle

from market_intelligence_core.registry import register_scorer
from market_intelligence_core.types import CONFIDENCE_SCALE, Score


@register_scorer("risk")
def compute(context):
    risk_score, risk_level, notes = profit_oracle._score_risk(context.niche)
    safety_filter_ran = not any(("غير متوفر" in n) or ("تعذّر" in n) for n in notes)
    confidence = CONFIDENCE_SCALE["high"] if safety_filter_ran else CONFIDENCE_SCALE["low"]
    return Score(
        dimension="risk",
        raw_data={"notes": notes, "level": risk_level},
        normalized_score=risk_score,
        confidence=confidence,
        explanation="؛ ".join(notes),
    )
