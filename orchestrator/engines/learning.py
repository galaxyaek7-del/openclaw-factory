"""
Learning engine adapter (ADR-051) — thin wrapper over decision_engine.
feedback.sync_outcomes() and decision_engine.learning's real accuracy/
recalibration functions (ADR-050, untouched). Factory-wide, not
niche-specific — running it is always safe (no network, no spend), so
it runs every cycle regardless of that cycle's own decision outcome.
"""

from decision_engine import feedback, learning as decision_learning

from orchestrator.registry import register_engine


@register_engine("learning")
def run(context):
    decisions_path = context.get("decisions_path")
    outcomes_path = context.get("outcomes_path")
    return {
        "sync": feedback.sync_outcomes(decisions_path=decisions_path, outcomes_path=outcomes_path),
        "accuracy": decision_learning.compute_prediction_accuracy(decisions_path=decisions_path, outcomes_path=outcomes_path),
        "recalibration": decision_learning.recalibration_report(decisions_path=decisions_path, outcomes_path=outcomes_path),
    }
