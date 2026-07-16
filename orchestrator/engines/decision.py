"""
Decision engine adapter (ADR-051) — thin wrapper over
decision_engine.engine.evaluate_and_decide() (ADR-050, untouched except
for the new optional precomputed_analysis parameter added specifically
for this integration). Reuses the market_intelligence stage's own result
from the shared cycle context instead of re-evaluating live — avoiding a
real, redundant second network round-trip for the same niche in the same
cycle.
"""

from decision_engine import engine as decision_engine_module

from orchestrator.registry import register_engine


@register_engine("decision")
def run(context):
    decision = decision_engine_module.evaluate_and_decide(
        context["niche"],
        external_signal=context.get("external_signal"),
        tier=context.get("tier", "tier4"),
        max_results=context.get("max_results", 10),
        precomputed_analysis=context.get("market_intelligence_result"),
        decisions_path=context.get("decisions_path"),
    )
    return decision.to_dict()
