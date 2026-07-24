"""
Galaxy Forge — Strategic Intelligence Layer (ADR-054).

The highest analytical layer of the company, completely separated from
production logic: read-only, no execution, no publishing, no production
changes, no score modification, no self-editing. Not a new engine, not a
new AI agent, not a dashboard.

Where Executive Intelligence (ADR-052) answers "what is the state of the
company today" and Validation (ADR-053) answers "did the pipeline run
reliably," this layer asks a different question entirely: "what
recurring PATTERN, across all history so far, predicts success or
failure" — never re-evaluating a single opportunity, only looking for
trends across everything already decided/executed/sold.

Every module here reuses an already-built real computation wherever one
exists (decision_engine.learning, validation_layer.reliability,
executive_intelligence.inactivity) rather than re-deriving it — the
explicit instruction this layer was built under. Where no existing
report answers the question (rejection-reason frequency, channel
long-term value), the raw append-only stores (decision_engine.store,
channels.ledger) are read directly, never a second copy of logic that
already exists elsewhere.

Every conclusion is either traceable to real evidence or explicitly
"Unknown" — this factory has, as of 2026-07-16, zero real orchestrator
executions and zero real sales ever recorded, so most questions this
layer can ask will honestly answer "Unknown" today. That is the correct
answer, not a bug to route around.
"""
