"""
Confidence meta-scorer (ADR-049) — generalizes the confidence-averaging
fix from the 2026-07-15 self-audit (market_intelligence_engine.
ai_ceo_decision's PAIN_CONFIDENCE_SCALE bug) into one canonical place:
overall confidence is the average of every OTHER dimension's own
.confidence, computed automatically from whatever the pipeline actually
ran. Adding a new scorer changes this average automatically — zero
edits needed here, which is the entire point of a meta-scorer that runs
after the primary pass instead of a hardcoded list of dimensions (the
exact bug class that caused yesterday's confidence-gate failure: a
hand-maintained list silently drifting from what the pipeline actually
computes).
"""

from market_intelligence_core.registry import register_meta_scorer
from market_intelligence_core.types import Score


@register_meta_scorer("confidence")
def compute(context, scores):
    values = [s.confidence for s in scores.values() if s.confidence is not None]
    avg = round(sum(values) / len(values)) if values else 0
    return Score(
        dimension="confidence",
        raw_data={"per_dimension": {name: s.confidence for name, s in scores.items()}},
        normalized_score=avg,
        confidence=avg,  # a confidence score's own confidence in itself is just itself
        explanation=f"متوسط ثقة عام عبر {len(values)} بُعد حقيقي: {avg}/100",
    )
