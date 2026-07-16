"""
Bottleneck detection (ADR-052) — two real, computable signals, nothing
inferred beyond what the data actually shows:

  1. An orchestrator engine with a real, recorded failure rate below 80%
     (needs at least one real success+failure pair to compute at all —
     see engine_health.py's own DISCOVERY/REAL split).
  2. An ACCEPTED opportunity sitting in the Decision Queue for 3+ real
     days without production/publishing having run — reusing
     decision_engine.ranking.rank_queue()'s own decided_at timestamps,
     not a new aging model.

Reports "no bottleneck detected" honestly when neither signal fires —
never invents one to make the report look more insightful than the data
supports.
"""

from datetime import datetime, timezone

from decision_engine import ranking

QUEUE_AGING_THRESHOLD_DAYS = 3
FAILURE_RATE_ALERT_BELOW = 80


def detect_bottlenecks(engine_health, decisions_path=None, outcomes_path=None, now=None):
    now = now or datetime.now(timezone.utc)
    items = []

    for stage, health in engine_health.items():
        if health.get("maturity") != "REAL":
            continue
        rate = health.get("success_rate")
        if rate is not None and rate < FAILURE_RATE_ALERT_BELOW:
            items.append({
                "type": "engine_failure_rate",
                "engine": stage,
                "evidence": (
                    f"{health['failures']} فشل من أصل {health['total_executions']} تنفيذ حقيقي "
                    f"(نسبة نجاح {rate}%) — data/orchestrator_timeline.jsonl"
                ),
            })

    queue = ranking.rank_queue(decisions_path=decisions_path, outcomes_path=outcomes_path)
    for item in queue:
        decided_at = item.get("decided_at")
        try:
            decided = datetime.fromisoformat(str(decided_at).replace("Z", "+00:00"))
            if decided.tzinfo is None:
                decided = decided.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        age_days = (now - decided).days
        if age_days >= QUEUE_AGING_THRESHOLD_DAYS:
            items.append({
                "type": "queue_aging",
                "niche": item.get("niche"),
                "age_days": age_days,
                "evidence": f"مقبول منذ {age_days} يوماً بلا تنفيذ إنتاج/نشر حقيقي بعد — decision_engine.ranking.rank_queue()",
            })

    if not items:
        return {"detected": False, "items": [], "reason": "لا اختناقات حقيقية مكتشَفة من البيانات المتاحة اليوم"}
    return {"detected": True, "items": items}
