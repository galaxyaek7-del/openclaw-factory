"""
Rejection reason frequency (ADR-054) — "Which rejection reasons occur
most frequently?"

No existing report already tallies this, so it is computed here directly
from decision_engine.store's real, append-only decision history — but
deliberately at the coarsest HONEST granularity available: the real
categorical ai_ceo_decision field (REJECT vs PIVOT, decision_engine.
engine._derive_status()'s own two rejection categories) rather than
free-text clustering of the reasoning strings, which would require
guessing at similarity between sentences never validated against real
data. Counting a field that already exists, unambiguously, on every
Decision record is real; inventing a text-similarity "reason cluster"
would not be.
"""

from decision_engine import store


def most_frequent_rejection_reasons(decisions_path=None):
    latest = store.latest_decision_per_niche(path=decisions_path)
    rejected = [d for d in latest.values() if d.get("status") == "REJECTED"]

    if not rejected:
        return {
            "answer": "Unknown",
            "reason": "لا قرارات REJECTED مسجَّلة بعد في data/decisions.jsonl",
            "source": "decision_engine.store.latest_decision_per_niche()",
        }

    tally = {}
    for d in rejected:
        category = d.get("ai_ceo_decision", "UNKNOWN")
        tally[category] = tally.get(category, 0) + 1

    ranked = sorted(tally.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "answer": ranked[0][0],
        "counts": dict(ranked),
        "total_rejected": len(rejected),
        "source": "decision_engine.store.latest_decision_per_niche() — grouped by real ai_ceo_decision field",
    }
