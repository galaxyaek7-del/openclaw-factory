# OpenClaw / Galaxy Forge — Executive Prioritization Engine

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). The directive's 7 named prioritization factors are checked here against `capital_allocation_engine.py`'s real 14-dimension Investment Score (ADR-139) and `executive_brain.py`'s real tier arbitration (`EXECUTIVE_BRAIN.md`) — the two real systems that already decide what this company works on next.

---

## The 7 requested factors, mapped to real dimensions

| Requested factor | Real dimension | Source |
|---|---|---|
| Revenue impact | `expected_revenue` | `value_engine.compute_value_profile()`'s real closed-sale revenue to date (never a forecast) |
| Customer value | `customer_impact` | `value_engine.compute_value_profile()`'s `expected_customer_value` |
| Strategic importance | `strategic_importance` | `strategic_intelligence_core.strategic_score()`'s `strategic_value` dimension |
| Automation potential | `automation_potential` | `strategic_intelligence_core.strategic_score()`'s `automation` dimension |
| Technical complexity | `engineering_cost` | `value_engine.compute_value_profile()`'s `estimated_build_cost` (`revenue_pipeline.plan.estimate_production_cost()`) |
| Time to execute | **Real, disclosed gap** | No real historical per-task duration data exists anywhere in this factory — confirmed independently by `execution_status.py`, `gfos.py`, and `strategic_planning.py`, all reporting `Unknown` for the same reason. Never estimated with a guess. |
| Long-term value | `long_term_asset_value` | `strategic_intelligence_core.strategic_score()`'s `long_term_value` dimension |

**6 of 7 factors have real, numeric or evidenced coverage. "Time to execute" is the one genuine, repeatedly-confirmed gap — disclosed the same way every time it comes up, not silently different here.**

## "Always execute the highest-value work first" — how that's actually decided

Two real, distinct mechanisms, not one:

1. **Within an already-ACCEPTED portfolio:** `scheduler.py::decide_next_actions()`'s real 5 buckets (accelerate/run_now/wait/stop/cancel), ordered by the real Priority Score `value_engine.build_value_engine_report()` computes.
2. **Across everything, including work not yet accepted:** `executive_brain.py`'s tier arbitration (`EXECUTIVE_BRAIN.md`) — Tier 1 System Stability outranks Tier 5 Self Evolution by a named, fixed rule, not a computed score, because some classes of work (a real active incident) must always outrank even a high-ROI opportunity, and this company has decided that explicitly rather than let a single blended score make that call silently.

## Real, disclosed non-numeric priorities

Not everything this company prioritizes reduces to the 7 factors above. `DECISION_FILTERS.md`'s six-question gate runs *before* any of this scoring — an opportunity that fails "does it align with the mission" is never reached by the Prioritization Engine at all, regardless of how high its revenue or ROI number would otherwise be. Priority scoring ranks what already passed the filters; it does not override them.

## Opportunity cost — the real check against over-committing

`capital_allocation_engine.py::opportunity_cost()` names, for every real accepted-but-lower-ranked initiative, exactly which higher-ranked real opportunity its resources are effectively going to instead — the mechanical enforcement of "highest-value work first," not just a stated intention.

---

*See also: `EXECUTIVE_BRAIN.md`, `DECISION_PROTOCOL.md`, `EXECUTIVE_MEMORY.md`.*
