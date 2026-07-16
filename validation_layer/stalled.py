"""
Accepted opportunities that never reached production (ADR-053) — a real
cross-reference between decision_engine's latest decisions and the
orchestrator timeline, reusing orchestrator.timeline.has_succeeded() and
orchestrator.orchestrator.make_idempotency_key() directly (the exact
functions the orchestrator itself uses for duplicate-prevention) rather
than re-deriving the key formula a second time.
"""

from decision_engine import store as decision_store
from orchestrator import timeline as orch_timeline
from orchestrator.orchestrator import make_idempotency_key


def detect_stalled_opportunities(decisions_path=None, timeline_path=None):
    latest = decision_store.latest_decision_per_niche(path=decisions_path)
    stalled = []

    for d in latest.values():
        if d.get("status") != "ACCEPTED":
            continue
        key = make_idempotency_key("production", d["niche"], d.get("tier", "tier4"))
        if not orch_timeline.has_succeeded(key, path=timeline_path):
            stalled.append({
                "niche": d["niche"],
                "decided_at": d.get("decided_at"),
                "opportunity_score": d.get("opportunity_score"),
                "evidence": "قرار ACCEPTED بلا تنفيذ إنتاج ناجح حقيقي واحد في data/orchestrator_timeline.jsonl",
            })

    if not stalled:
        return {"detected": False, "items": []}
    return {"detected": True, "items": stalled}
