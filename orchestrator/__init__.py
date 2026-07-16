"""
OpenClaw Factory — Executive Orchestrator / Factory OS (ADR-051).

The single runtime coordinator: every engine (Market Intelligence,
Decision Engine, Production, Publishing, Learning) is invoked only
through this package, in a declared order, with every execution recorded
to an immutable timeline, retried on transient failure, and never
duplicated for an action with a real, costly, irreversible side effect.

Signal -> Market Intelligence -> Decision -> [Production -> Publishing,
gated on ACCEPTED and an explicit execute_production=True] -> Learning.

Governance note: building a single company-wide coordinator is exactly
the "Company Operating System" class of work ADR-034 gated behind an
objective trigger (real sale / live API key / real Tier-1 candidate) —
none of which has fired. This was already flagged once, explicitly, in
ADR-048's architecture review, with the question left open for the
President. This build proceeds on the President's own explicit,
detailed direction ("This is not another feature. This is the operating
system of the autonomous company.") — documented here as a deliberate,
named override, the same pattern ADR-034 itself used for its own
2026-07-15 override entry, not a silent bypass.
"""
