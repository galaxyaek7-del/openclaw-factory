# Galaxy Forge — Commercial Resource Allocation

**Date:** 2026-08-08 | ADR-217, Phase 27, Section 22. `commercial_autonomy_engine.commercial_resource_allocation()` — reuses `capital_allocation_engine.py::opportunity_cost()` (ADR-139) directly, never a second resource-allocation computation.

---

## The 4 named finite resources this factory actually tracks

Founder attention/human review time (`founder_console.py`), AI compute (`ai_capability/registry.py`), automation capacity (`autonomous_operations_status.py`), publishing capacity (`channels/publish_protection.py`) — real citations already established in `enterprise_capital_allocation.py` (Phase 15). Engineering/Design/Support/Marketing effort have **no real tracking anywhere** in this factory — honestly disclosed, never estimated.

## Real opportunity-cost pairing

For every real ACCEPTED opportunity, cites which higher-ranked candidates are effectively receiving resources instead — currently moot (0 real ACCEPTED opportunities exist).

---

*See also: `COMMERCIAL_QUEUE_ENGINE.md`, `ENTERPRISE_CAPITAL_ALLOCATION` (session history).*
