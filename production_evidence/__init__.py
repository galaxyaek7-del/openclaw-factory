"""
OpenClaw Factory — Production Evidence Layer (ADR-055).

Not a new engine, not a new AI agent, not a dashboard, not a new scoring
dimension. The objective is no longer more intelligence — it is a
trustworthy, immutable evidence record for every real opportunity,
assembled ENTIRELY from already-immutable sources this factory already
writes: orchestrator.timeline (ADR-051), decision_engine.store
(ADR-050), channels.ledger.

record.build_evidence_record(niche) does not re-implement lifecycle
stitching — it calls validation_layer.lifecycle.build_lifecycle()
(ADR-053) directly, the one function that already matches timeline
records to a niche via orchestrator.orchestrator.make_idempotency_key().
Duplicating that matching logic a second time here is exactly what this
directive's "no duplicate orchestration" forbids.

Every record is a pure function of already-immutable data, so there is
nothing here to "overwrite" — no new store is created; recomputing this
function twice for the same niche at the same point in history always
returns the same evidence. Where a required field has no real source
yet (customer feedback, most notably — this factory has no connected
feedback channel of any kind), the field is explicitly "Unknown" with
its reason, never guessed.
"""
