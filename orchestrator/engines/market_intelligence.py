"""
Market Intelligence engine adapter (ADR-051) — thin wrapper over
market_intelligence_core.core.evaluate_opportunity() (ADR-049,
untouched). Loose coupling: this file is the ONLY place in the
orchestrator that imports market_intelligence_core.
"""

from market_intelligence_core import core as mic_core

from orchestrator.registry import register_engine


@register_engine("market_intelligence")
def run(context):
    return mic_core.evaluate_opportunity(
        context["niche"],
        external_signal=context.get("external_signal"),
        tier=context.get("tier", "tier4"),
        max_results=context.get("max_results", 10),
        analysis_db_file=context.get("analysis_db_file"),
    )
