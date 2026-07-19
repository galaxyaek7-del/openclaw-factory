"""
Founder Console (EOS Phase 1, 2026-07-19) — "show only decisions that
require founder approval; everything else should operate autonomously."

Pure filter-and-merge of already-real signals, zero new judgment:

  - Which marketplace channels need founder action right now, and why
    (commercial_execution.approval_gates.check_approval_gates(), already
    real, ADR-adjacent to the Commercial Execution Layer).
  - DEFERRED decisions awaiting a founder call
    (decision_engine.store.latest_decision_per_niche(), filtered).

Attention/review flags (NEEDS_ATTENTION.md/NEEDS_REVIEW.md, written by
factory_loop.js) and BLOCKERS.md are JS-native reads (lib/dashboard_data.js
already has readAttentionFlag()/readReviewFlag(); reading BLOCKERS.md is
the exact same markdown-scrape technique server.js's own
readNextDollarActions() already uses on FACTORY_STATUS.md) — assembled
into the one Founder Console view in server.js, not duplicated here.
"""


def build_founder_queue_partial(decisions_path=None):
    """The Python-side half of the Founder Console: blocked channels +
    DEFERRED decisions. server.js merges this with the JS-native
    attention/review flags and BLOCKERS.md read to produce the full
    Founder Console view."""
    import distributor  # noqa: F401 -- self-registers every real channel arm
    from commercial_execution.approval_gates import check_approval_gates
    from decision_engine import store

    gates = check_approval_gates()

    latest = store.latest_decision_per_niche(path=decisions_path)
    deferred = [d for d in latest.values() if d.get("status") == "DEFERRED"]

    return {
        "blocked_channels": gates["gated"],
        "autonomous_channels": gates["autonomous"],
        "pending_decisions": deferred,
    }
