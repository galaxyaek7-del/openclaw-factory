"""
Production Engine Health Gate -- Autonomous Digital Company v1 follow-up
(2026-07-19): a real, narrow production-readiness gate for
factory_loop.js's Golden Hunter Bridge, reusing
engine_health.compute_engine_health() (already real, tested, ADR-052) --
not a new health computation, and the same FAILURE_RATE_ALERT_BELOW
threshold (80%) executive_intelligence's own daily bottleneck report
already uses to flag a real bottleneck.

This is the "data flows, not isolated modules" connection the founder
asked for: executive_intelligence's real per-engine success-rate
detection now actually gates a real business decision (whether to
dispatch a new production run this cycle) instead of only ever
appearing in a standalone daily report nobody's code reads.

Fails OPEN on anything short of a real, confirmed low success rate --
same discipline as factory_loop.js's own opportunity-score gate ("a
scoring failure fails OPEN here on purpose... never block production
because a second, newer check happened to fail"). An engine with too
little real history (DISCOVERY maturity) or a healthy rate always
returns ok=True; this only ever blocks on a REAL, already-flagged
bottleneck, never a guess.
"""

from executive_intelligence import engine_health as engine_health_module
from executive_intelligence.bottlenecks import FAILURE_RATE_ALERT_BELOW

GATED_STAGE = "production"


def check_production_engine_health(timeline_path=None):
    health = engine_health_module.compute_engine_health(timeline_path=timeline_path)
    stage_health = health.get(GATED_STAGE, {})

    if stage_health.get("maturity") != "REAL":
        return {
            "ok": True,
            "reason": "لا سجل تنفيذ إنتاج حقيقي كافٍ بعد لتقييم الصحة -- لا حظر",
            "engine_health": stage_health,
        }

    rate = stage_health.get("success_rate")
    if rate is not None and rate < FAILURE_RATE_ALERT_BELOW:
        return {
            "ok": False,
            "reason": (
                f"محرّك الإنتاج يظهر معدّل نجاح حقيقي منخفض ({rate}% من "
                f"{stage_health['total_executions']} تنفيذ حقيقي مسجَّل) -- "
                f"تخطّي الإنتاج هذه الدورة (عتبة الإنذار: {FAILURE_RATE_ALERT_BELOW}%)"
            ),
            "engine_health": stage_health,
        }

    return {
        "ok": True,
        "reason": (
            f"محرّك الإنتاج سليم (نجاح {rate}% من {stage_health['total_executions']} تنفيذ)"
            if rate is not None else "لا بيانات كافية لحساب معدل نجاح حقيقي بعد"
        ),
        "engine_health": stage_health,
    }
