"""
Bottleneck effort (ADR-054) — "Which bottlenecks consume the most
engineering effort?"

Reused verbatim from validation_layer.reliability.compute_reliability_
statistics()'s bottleneck_frequency tally (ADR-053) — no second
computation. "Effort" here is approximated honestly by real occurrence
count, the only real signal currently recorded; this factory has no
separate real time-tracking of engineering hours spent per bottleneck
type, so that stronger claim is never made.
"""

from validation_layer import reliability as reliability_module


def most_effort_consuming_bottleneck(decisions_path=None, outcomes_path=None, timeline_path=None):
    stats = reliability_module.compute_reliability_statistics(
        decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path,
    )
    frequency = stats["bottleneck_frequency"]

    if not frequency:
        return {
            "answer": "Unknown",
            "reason": "لا اختناقات حقيقية مكتشَفة بعد",
            "source": "validation_layer.reliability.compute_reliability_statistics()",
        }

    ranked = sorted(frequency.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "answer": ranked[0][0],
        "counts": dict(ranked),
        "note": "التكرار الحالي، لا وقت هندسي حقيقي مقاس — لا مصدر زمني حقيقي لهذا القياس بعد",
        "source": "validation_layer.reliability.compute_reliability_statistics()",
    }
