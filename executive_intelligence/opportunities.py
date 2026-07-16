"""
Opportunity tracking (ADR-052) — every accepted/rejected/deferred
decision, with its real, already-stored reasoning (decision_engine's
Decision.reasoning, ADR-050) — nothing re-derived, nothing summarized
away. The highest-value pending opportunity reuses decision_engine.
ranking.rank_queue() (the existing, tested global ranking) rather than
building a second one.
"""

from decision_engine import ranking, store


def track_opportunities(decisions_path=None):
    latest = store.latest_decision_per_niche(path=decisions_path)
    by_status = {"ACCEPTED": [], "REJECTED": [], "DEFERRED": []}

    for d in latest.values():
        by_status.setdefault(d.get("status", "UNKNOWN"), []).append({
            "niche": d.get("niche"),
            "opportunity_score": d.get("opportunity_score"),
            "ai_ceo_decision": d.get("ai_ceo_decision"),
            "reasoning": d.get("reasoning"),
            "decided_at": d.get("decided_at"),
        })

    return {
        "counts": {status: len(items) for status, items in by_status.items()},
        "by_status": by_status,
        "source": "data/decisions.jsonl",
    }


def highest_value_pending_opportunity(decisions_path=None, outcomes_path=None):
    queue = ranking.rank_queue(decisions_path=decisions_path, outcomes_path=outcomes_path)
    if not queue:
        return {
            "available": False,
            "reason": "لا فرصة ACCEPTED واحدة بانتظار تنفيذ حقيقي في طابور القرار حالياً",
        }
    top = queue[0]
    return {
        "available": True,
        "niche": top.get("niche"),
        "opportunity_score": top.get("opportunity_score"),
        "reasoning": top.get("reasoning"),
        "decided_at": top.get("decided_at"),
        "source": "decision_engine.ranking.rank_queue()",
    }
