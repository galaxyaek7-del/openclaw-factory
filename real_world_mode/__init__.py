"""
OpenClaw Factory — Real World Operating Mode (ADR-056).

Not a new engine, not a new AI agent, not a dashboard, not a redesign.
The current infrastructure (orchestrator.orchestrator.run_cycle(),
ADR-051) already implements Signal -> Analysis -> Decision -> [Production
-> Publishing] -> Learning end to end. What did not exist yet was the
wiring between "a real external signal exists somewhere in this factory"
(OPPORTUNITIES.md, tier1_intake/candidates/*.json) and "the existing
pipeline has actually seen it." This package is exactly that wiring,
nothing more:

  signal_intake.py    reads real, already-existing signal sources and
                       shapes each into the (niche, external_signal)
                       contract orchestrator.run_cycle() already accepts
  operating_mode.py     calls orchestrator.run_cycle() once per real
                         signal — no new decision logic, no new storage,
                         no new orchestration

execute_production defaults False everywhere here too, the same safety
convention orchestrator.run_cycle() itself already enforces. Running
this with defaults never spends real money or publishes anything live.
Flipping it for a real batch is a deliberate, separate decision, never
made silently by this module or any test in this repository.
"""
