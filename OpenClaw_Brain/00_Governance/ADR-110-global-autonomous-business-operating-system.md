# ADR-110 — Global Autonomous Business Operating System (CEO Dashboard signals + real cross-module reuse)

**Date:** 2026-07-24
**Status:** Adopted.

---

## The directive

A permanent Company Operating Loop repeating forever; every opportunity as a tracked business project with stage, expected revenue/cost/ROI, owner, dependencies, bottlenecks, completion %, confidence, next action, and learning history; Mission Control as the real CEO dashboard (Company Health, Revenue, Active Products, Global Markets, China Division, Premium Products, AI Products, Automation Status, Production Capacity, Bottlenecks, Growth Forecast, Strategic Recommendations); every completed commercial event automatically improving future decisions.

## What this mission actually is: three more already-settled questions, restated

Before writing anything, a real check against today's own work found this directive re-asks three questions already answered earlier the same day, with the same standing decisions applying unchanged:

1. **"repeat forever"** is the live, always-on scheduler process explicitly declined via AskUserQuestion in ADR-107 ("on-demand only... matches CLAUDE.md's current architecture exactly"). Applied the same decision a second time without re-asking.
2. **"Global Markets" / "China Division"** is ADR-103's Global Market Expansion ask, already deferred and reaffirmed twice (ADR-106, ADR-108) for the same unchanged reason. Applied a fourth time without re-asking — nothing has changed.
3. **"Every completed commercial event must automatically improve future decisions"** is ADR-109's Objective 4, already explicitly declined the same day: auto-adjusting `profit_oracle.py`'s real scoring weights off a currently-empty real sample is a materially higher-risk action than a read-only report, and this factory's core acceptance gate does not change itself autonomously. Applied a second time without re-asking.

The remaining, genuinely new part of this directive — the 10 named per-project fields and the 8 new named CEO-dashboard signals — was checked field-by-field against `execution_status.py`/`mission_control_api.py::_get_global_execution_view()` (both ADR-107, shipped the same day). 9 of 10 project fields and 4 of 8 dashboard signals already existed. What follows is only the real, incremental, non-duplicate work.

## What was built

**`execution_status.py`** gained the 2 genuinely missing project fields: `expected_roi` (reused verbatim from `value_engine`'s already-computed `board_summary.expected_roi` — zero new computation) and `dependencies` (honestly `{value: None, reason: ...}` — no real business-level opportunity dependency tracking exists anywhere in this factory; `dependency_graph.py` computes code-file import dependencies, a different, unrelated real thing, never conflated with this).

**`next_action` and `bottleneck_summary`**, the real "next action" and "bottlenecks" the directive named: `build_execution_status_report()` now joins each opportunity with its real `scheduler.py` bucket assignment (run_now/wait/accelerate/stop/cancel) and tallies real `blocking_issue` reasons portfolio-wide. To avoid a second, redundant full-portfolio computation, `scheduler.decide_next_actions()` gained a `portfolio=` reuse parameter (same pattern already used by `execution_status.build_execution_status(profile=...)`) — with one real safety rule, tested explicitly: it must only ever be passed an *unlimited* portfolio, since scheduling must cover every real opportunity and a limited view may legitimately drop some for display only.

**`growth_engine.py`** gained 3 new functions covering the CEO-dashboard signals with no prior real source:
- `portfolio_growth_summary()` — the real "Premium Products" / "AI Products" / "Automation Status" tally, reusing already-computed `dimensions.upgrade_potential`/`dimensions.automation_potential` from `value_engine.build_value_engine_report()`'s existing profiles (zero new per-niche computation) plus `product_families.registry`'s real adapter status.
- `production_capacity_summary()` — the real "Production Capacity" signal. This factory has no live worker pool or forward-looking capacity concept (CLAUDE.md: no scheduler exists), so the honest substitute is real, measured historical throughput from `books/_generation_log.jsonl`'s real timestamps — never a fabricated forward number.
- `growth_forecast()` — the real "Growth Forecast" signal, deliberately evidence-gated rather than projected. Real forecasting needs a real trend across ≥2 comparable time windows of sales data; with zero real sales today, this honestly reports that a forecast isn't computable rather than extrapolating from nothing — the mission's own stated rule ("zero fake data... no assumptions") is exactly why no number is produced here.

**Mission Control's `get-global-execution-view` action** wires all of the above in. `commercial_recommendations` (already shipped, ADR-106) is explicitly documented as already being the real "Strategic Recommendations" signal — not duplicated under a second key.

## Verification

15 new tests across `tests/test_execution_status.py` (5), `tests/test_scheduler.py` (1, confirming `portfolio=` reuse produces byte-identical results to a fresh computation), `tests/test_growth_engine.py` (7), `tests/test_mission_control_api.py` (2 updated with new mocks). Full regression: highest-risk suites first (execution_status, scheduler, growth_engine, mission_control_api, value_engine), then the full repository (Python + Node), then the API contract test.

## What's deliberately not built

- No live, always-on scheduler process (standing decision, ADR-107, applied again).
- No Global Markets / China Division intelligence (standing decision, ADR-103, applied a fourth time).
- No automatic scoring-weight adjustment from completed sales (standing decision, ADR-109, applied again).
- No fabricated growth forecast number — real, tested, honestly gated code exists; it will start reporting a real trend the moment real sales data supports one.
