"""
OpenClaw Factory — Validation Layer (ADR-053).

Not a new engine, not a new AI agent, not a new dashboard: a read-only
reliability layer that reconstructs and measures what the existing
factory already did, entirely from data it already records — the
orchestrator's immutable execution timeline (ADR-051), decision_engine's
append-only decision/outcome stores (ADR-050), and executive_intelligence's
already-built health/bottleneck functions (ADR-052, reused directly here,
never re-derived).

lifecycle.build_lifecycle(niche) reconstructs the full Signal ->
Analysis -> Decision -> Queue -> Production -> Publishing -> Revenue ->
Learning path for one niche by matching orchestrator.orchestrator.
make_idempotency_key()'s own deterministic key formula against the real
timeline — the exact same function the orchestrator itself uses to
detect duplicates, reused here rather than re-derived, so this can never
silently disagree with what the orchestrator actually did.
"""
