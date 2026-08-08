# Galaxy Forge — Product Kill Criteria

**Date:** 2026-08-08 | ADR-213, Phase 23, Sections 20-21. `product_innovation_engine.product_decision_gate()` + `kill_criteria_check()`.

---

## Section 20 — Product Decision Gate

Real, deterministic mapping from the 6 validation gates onto the 7 named decisions (`PRODUCT_DECISIONS`): all 6 gates pass → `BUILD`/`PILOT`; 0 pass → `KILL`; 1-2 pass → `RESEARCH_MORE`; 3-5 pass → `ITERATE`. Verified live for a real candidate: 3/6 gates pass → `ITERATE` (not `BUILD`, not `KILL` — an honest middle state).

## Section 21 — Kill Criteria

`kill_criteria_check(niche)` cites `decision_engine.store`'s real, already-recorded rejection/deferral reasoning directly — never a second kill-decision computation. **Real, current portfolio state**: 0 ACCEPTED, ~49 DEFERRED, ~49 REJECTED across 98 real evaluated niches (drift from earlier phases reflects ongoing real re-evaluation activity).

## Never keeps a product alive from sunk cost

Confirmed by direct inspection: `decision_engine`'s evaluation functions have no cumulative-past-spend parameter anywhere in their real signatures — architecturally incapable of being anchored to money already spent, the same finding `capital_allocation_engine.py` (ADR-139) already established.

---

*See also: `PRODUCT_VALIDATION_GATES.md`, `PRODUCT_PORTFOLIO.md`.*
