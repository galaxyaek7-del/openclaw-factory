"""
Decision Engine — global ranking + Decision Queue (ADR-050).

Ranks by opportunity_score (profit_oracle's tier-aware composite,
ADR-026) — the same real, tested number that gates ACCEPTED/DEFERRED in
engine.py, so ranking and decision-making use one consistent measure,
never two different ones that could disagree silently.
"""

from decision_engine import store


def rank_all(path=None):
    """Global ranking of every niche's LATEST decision, any status —
    'rank every opportunity globally'."""
    latest = store.latest_decision_per_niche(path=path)
    return sorted(
        latest.values(),
        key=lambda d: d.get("opportunity_score") if d.get("opportunity_score") is not None else -1,
        reverse=True,
    )


def rank_queue(decisions_path=None, outcomes_path=None):
    """The Decision Queue: every ACCEPTED decision not yet linked to a real
    sales outcome, ranked by opportunity_score descending — 'what's next
    in line,' not merely 'everything ever accepted.'"""
    matched_decision_ids = {
        o.get("decision_id") for o in store.read_outcomes(path=outcomes_path) if o.get("decision_id")
    }
    latest = store.latest_decision_per_niche(path=decisions_path)
    pending = [
        d for d in latest.values()
        if d.get("status") == "ACCEPTED" and d.get("decision_id") not in matched_decision_ids
    ]
    return sorted(pending, key=lambda d: d.get("opportunity_score") or 0, reverse=True)


def rank_queue_with_commercial_context(decisions_path=None, outcomes_path=None, evidence_path=None):
    """Global Market Learning Engine (2026-07-23): the Opportunity Queue,
    with each item additionally carrying its real market_memory.py
    commercial profile — informational only, never re-ranks anything
    (rank_queue()'s own opportunity_score order is untouched). Every item
    honestly reports zero real commercial evidence until a real sale for
    a RELATED, already-ACCEPTED niche exists (queue items are, by
    definition, not yet matched to any outcome themselves)."""
    import market_memory

    queue = rank_queue(decisions_path=decisions_path, outcomes_path=outcomes_path)
    return [
        {**d, "market_memory": market_memory.niche_commercial_profile(d.get("niche"), evidence_path=evidence_path)}
        for d in queue
    ]
