"""
Competition scorer (ADR-049) — thin adapter over
profit_oracle._score_competition() (ADR-041), enriched with the real
competitor counts market_intelligence_engine.analyze_opportunity()
already gathered via competitor_discovery.py (ADR-042). Read from
context.analysis (never re-fetched — that would be a second live
network call for data the pipeline already has).

This enrichment is additive only: profit_oracle.score_opportunity()'s
own `scores.competition` value (used today by book_generator.py,
inspectors.py, factory_loop.js) is completely unaffected — it keeps
calling _score_competition() directly, exactly as before. This module's
Score.confidence can be genuinely higher than _score_competition() alone
would justify, because it also knows whether competitor_discovery.py
actually found real competitors — that richer signal only reaches
callers of the new Core, never retroactively changes the old path
(partially closes BLOCKERS.md #4 for Core callers, without touching the
existing, tested, hot-path behavior at all).
"""

import profit_oracle

from market_intelligence_core.registry import register_scorer
from market_intelligence_core.types import CONFIDENCE_SCALE, Score


@register_scorer("competition")
def compute(context):
    competition_score, notes = profit_oracle._score_competition(context.niche, context.external_signal)

    competitors_summary = (context.analysis or {}).get("competitors") or {}
    real_competitors_found = competitors_summary.get("total_found")

    if real_competitors_found:
        confidence = CONFIDENCE_SCALE["high"]
    elif profit_oracle._find_niche_report(context.niche) or (context.external_signal or {}).get("competition"):
        confidence = CONFIDENCE_SCALE["medium"]
    else:
        confidence = CONFIDENCE_SCALE["low"]

    return Score(
        dimension="competition",
        raw_data={
            "notes": notes,
            "real_competitors_found": real_competitors_found,
            "by_category": competitors_summary.get("by_category"),
        },
        normalized_score=competition_score,
        confidence=confidence,
        explanation="؛ ".join(notes),
    )
