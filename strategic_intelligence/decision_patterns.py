"""
Decision success patterns + least-predictive dimensions (ADR-054).

Answers two of the six required questions:
  - "Which decision patterns repeatedly lead to successful outcomes?"
  - "Which scoring dimensions are least predictive?"

Both are read directly off decision_engine.learning.recalibration_report()
(ADR-050) — REUSED verbatim, never recomputed. That function already
measures, per scoring dimension, the real average normalized_score among
ACCEPTED-and-actually-sold niches versus ACCEPTED-and-not-yet-sold ones,
gated behind a minimum real sample size. This module only INTERPRETS
that existing output (which dimension has the largest/smallest real
difference) — it adds no new statistic of its own.
"""

from decision_engine import learning as decision_learning


def find_success_patterns(decisions_path=None, outcomes_path=None):
    """The scoring dimension(s) most associated with a real sale — the
    largest real (avg_score_when_sold - avg_score_when_not_yet_sold)."""
    recalibration = decision_learning.recalibration_report(decisions_path=decisions_path, outcomes_path=outcomes_path)
    if not recalibration.get("recalibrated"):
        return {
            "answer": "Unknown",
            "reason": recalibration.get("reason", "بيانات مبيعات حقيقية غير كافية بعد"),
            "source": "decision_engine.learning.recalibration_report()",
        }

    per_dim = recalibration["per_dimension"]
    if not per_dim:
        return {"answer": "Unknown", "reason": "لا أبعاد تسجيل ذات بيانات كافية للمقارنة", "source": "decision_engine.learning.recalibration_report()"}

    ranked = sorted(per_dim.items(), key=lambda kv: kv[1]["difference"], reverse=True)
    top_dimension, top_stats = ranked[0]
    return {
        "answer": top_dimension,
        "evidence": (
            f"متوسط {top_dimension} عند البيع الحقيقي: {top_stats['avg_score_when_sold']}، "
            f"عند عدم البيع بعد: {top_stats['avg_score_when_not_yet_sold']} "
            f"(فرق حقيقي: {top_stats['difference']})"
        ),
        "sample_size": recalibration["real_sold_samples"],
        "source": "decision_engine.learning.recalibration_report()",
    }


def find_least_predictive_dimensions(decisions_path=None, outcomes_path=None):
    """The scoring dimension(s) whose real score barely differs between
    sold and not-yet-sold niches — i.e. it doesn't distinguish winners."""
    recalibration = decision_learning.recalibration_report(decisions_path=decisions_path, outcomes_path=outcomes_path)
    if not recalibration.get("recalibrated"):
        return {
            "answer": "Unknown",
            "reason": recalibration.get("reason", "بيانات مبيعات حقيقية غير كافية بعد"),
            "source": "decision_engine.learning.recalibration_report()",
        }

    per_dim = recalibration["per_dimension"]
    if not per_dim:
        return {"answer": "Unknown", "reason": "لا أبعاد تسجيل ذات بيانات كافية للمقارنة", "source": "decision_engine.learning.recalibration_report()"}

    ranked = sorted(per_dim.items(), key=lambda kv: abs(kv[1]["difference"]))
    least_dimension, least_stats = ranked[0]
    return {
        "answer": least_dimension,
        "evidence": f"أصغر فرق حقيقي بين البيع وعدمه: {least_stats['difference']} نقطة فقط",
        "sample_size": recalibration["real_sold_samples"],
        "source": "decision_engine.learning.recalibration_report()",
    }
