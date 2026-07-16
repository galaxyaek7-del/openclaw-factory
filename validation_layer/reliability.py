"""
Reliability statistics (ADR-053) — assembles the numbers requirement 7
asks for by REUSING already-built real computations rather than
re-deriving any of them:

  success rate / failure rate    executive_intelligence.engine_health
                                  (ADR-052, reused verbatim)
  average processing time        validation_layer.durations (new here —
                                  the one genuinely new statistic this
                                  layer computes)
  bottleneck frequency            a real tally of the CURRENT bottleneck
                                  snapshot from executive_intelligence.
                                  bottlenecks (ADR-052, reused), broken
                                  down by type — a real count of what's
                                  detected right now, never a fabricated
                                  historical trend (no periodic snapshot
                                  history exists yet to trend against;
                                  see ADR-053 for why that's honest, not
                                  a shortcut).
  decision accuracy               decision_engine.learning (ADR-050,
                                  reused verbatim)
"""

from decision_engine import learning as decision_learning
from executive_intelligence import bottlenecks as bottleneck_module
from executive_intelligence import engine_health as engine_health_module

from validation_layer import durations as duration_module


def compute_reliability_statistics(decisions_path=None, outcomes_path=None, timeline_path=None):
    health = engine_health_module.compute_engine_health(timeline_path=timeline_path)
    stage_durations = duration_module.compute_stage_durations(timeline_path=timeline_path)
    bottleneck_snapshot = bottleneck_module.detect_bottlenecks(
        health, decisions_path=decisions_path, outcomes_path=outcomes_path
    )
    accuracy = decision_learning.compute_prediction_accuracy(decisions_path=decisions_path, outcomes_path=outcomes_path)

    bottleneck_frequency = {}
    for item in bottleneck_snapshot.get("items", []):
        bottleneck_frequency[item["type"]] = bottleneck_frequency.get(item["type"], 0) + 1

    return {
        "engine_reliability": {
            stage: {
                "maturity": h["maturity"],
                "success_rate": h.get("success_rate"),
                "failures": h.get("failures"),
                "total_executions": h.get("total_executions", 0),
            }
            for stage, h in health.items()
        },
        "average_processing_time": stage_durations,
        "bottleneck_frequency": bottleneck_frequency,
        "decision_accuracy": accuracy,
    }
