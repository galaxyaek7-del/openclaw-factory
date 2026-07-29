"""
Founder Console (EOS Phase 1, 2026-07-19) — "show only decisions that
require founder approval; everything else should operate autonomously."

Pure filter-and-merge of already-real signals, zero new judgment:

  - Which marketplace channels need founder action right now, and why
    (commercial_execution.approval_gates.check_approval_gates(), already
    real, ADR-adjacent to the Commercial Execution Layer).
  - DEFERRED decisions awaiting a founder call
    (decision_engine.store.latest_decision_per_niche(), filtered).
  - Real Evolution Queue proposals awaiting a founder call (Autonomous
    Company Evolution Engine, Round 6, 2026-07-29) — evolution_queue.py's
    own AWAITING_FOUNDER_APPROVAL bucket, the same integration style as
    the DEFERRED-decisions count just above.
  - A real active marketplace publish emergency stop (Global Commercial
    Hardening, Phase 1, 2026-07-29) — channels/publish_protection.py's
    own global.emergency_stopped flag, surfaced the moment it's real
    (this halts real revenue, so it belongs alongside the other
    founder-must-decide signals, not buried in a read-only panel alone).

Attention/review flags (NEEDS_ATTENTION.md/NEEDS_REVIEW.md, written by
factory_loop.js) and BLOCKERS.md are JS-native reads (lib/dashboard_data.js
already has readAttentionFlag()/readReviewFlag(); reading BLOCKERS.md is
the exact same markdown-scrape technique server.js's own
readNextDollarActions() already uses on FACTORY_STATUS.md) — assembled
into the one Founder Console view in server.js, not duplicated here.
"""


def build_founder_queue_partial(decisions_path=None, evolution_queue_state_path=None, publish_protection_state_path=None):
    """The Python-side half of the Founder Console: blocked channels +
    DEFERRED decisions + pending Evolution Queue proposals + an active
    publish emergency stop. server.js merges this with the JS-native
    attention/review flags and BLOCKERS.md read to produce the full
    Founder Console view."""
    import distributor  # noqa: F401 -- self-registers every real channel arm
    from commercial_execution.approval_gates import check_approval_gates
    from decision_engine import store
    import evolution_queue
    from channels import publish_protection

    gates = check_approval_gates()

    latest = store.latest_decision_per_niche(path=decisions_path)
    deferred = [d for d in latest.values() if d.get("status") == "DEFERRED"]

    queue = evolution_queue.list_evolution_queue(state_path=evolution_queue_state_path)
    protection_status = publish_protection.list_publish_protection_status(state_path=publish_protection_state_path)

    return {
        "blocked_channels": gates["gated"],
        "autonomous_channels": gates["autonomous"],
        "pending_decisions": deferred,
        "pending_evolution_proposals": queue["awaiting_approval"],
        "publish_emergency_stop": protection_status["global"] if protection_status["global"]["emergency_stopped"] else None,
    }
