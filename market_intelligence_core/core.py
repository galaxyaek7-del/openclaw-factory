"""
Market Intelligence Core — the canonical entrypoint (ADR-049).

evaluate_opportunity() is the permanent, single source of truth for
opportunity evaluation this factory's future capabilities should
integrate through. It does not reimplement orchestration that already
exists and is already tested: it calls
market_intelligence_engine.analyze_opportunity() (ADR-043, unchanged)
to get the full real analysis exactly as every existing caller already
receives it, then runs the plugin scoring pipeline on top and attaches
the result as an additive `dimension_scores` key — every dimension's
full Score (raw_data/normalized_score/confidence/explanation) alongside
the legacy shape, never replacing any of its existing keys.

Deliberately does NOT get called from profit_oracle.py's synchronous
scoring path, book_generator.py, inspectors.py, or factory_loop.js's
hot path — same standalone-orchestrator rule already established for
market_intelligence_engine.py/competitor_discovery.py/market_hunter.py
(ADR-041/042/043): live network calls stay out of the fast,
production-gating code. This is the deliberately-run, richer analysis
path.
"""

from datetime import datetime, timezone

import market_intelligence_engine

from market_intelligence_core import pipeline
from market_intelligence_core.types import EvaluationContext


def evaluate_opportunity(niche, external_signal=None, tier="tier4", max_results=10, analysis_db_file=None):
    analysis = market_intelligence_engine.analyze_opportunity(
        niche, external_signal=external_signal, tier=tier, max_results=max_results, analysis_db_file=analysis_db_file
    )

    if "error" in analysis:
        analysis["dimension_scores"] = {}
        return analysis

    context = EvaluationContext(
        niche=analysis["niche"],
        tier=tier,
        external_signal=external_signal,
        max_results=max_results,
        now=datetime.now(timezone.utc),
        analysis=analysis,
    )
    scores = pipeline.run(context)
    analysis["dimension_scores"] = {name: s.to_dict() for name, s in scores.items()}
    return analysis
