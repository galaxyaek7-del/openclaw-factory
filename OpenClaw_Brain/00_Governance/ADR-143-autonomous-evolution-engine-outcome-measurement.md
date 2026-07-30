# ADR-143 — Autonomous Evolution Engine: Outcome Measurement + Ranking

**Date:** 2026-07-30
**Status:** Adopted.

---

## The directive

"EXECUTIVE DIRECTIVE — AUTONOMOUS EVOLUTION ENGINE (AEE)": Galaxy Forge must continuously observe (market, customer, revenue, product, competitor, technology, AI capability, infrastructure, cost, execution speed, failure history, knowledge graph), turn observations into ranked Evolution Proposals (reason/evidence/expected impact/risk/required changes/rollback/confidence), rank them (strategic value/revenue impact/execution cost/long-term sustainability/risk/confidence), display them in Mission Control (Queue/Accepted/Rejected/Implemented/Measured Outcomes/Architecture Evolution History), and — the directive's own words — "continuously measures whether every implemented evolution actually improved: Revenue, Reliability, Scalability, Automation, Customer value, Execution speed."

## The real overlap, found before any code was written

`evolution_queue.py` (ADR-133, 2026-07-29 — literally the previous day) already builds almost this entire pipeline: a real `PROPOSED -> SIMULATED -> AWAITING_FOUNDER_APPROVAL -> APPROVED/REJECTED -> IMPLEMENTED` state machine, real Simulate (`affected_modules`/`sensitive_areas_touched`/`rollback_complexity`, a disclosed static-analysis heuristic), real Decide (`policy_risk`/`duplicate_architecture_risk` flags, never auto-approve/auto-reject), a real Learning History (`stage_history`, already the "Architecture Evolution History" the directive asks for), Mission Control's `evolution-queue` panel + approve/reject/mark-implemented actions, a `factory_loop.js` daily tick (`maybeGenerateDailyEvolutionQueueIntake()`), and `knowledge_graph/build.py`'s real `Proposal` node type. `tool_intelligence/proposals.py` already generates 6 real, evidence-cited proposal categories from real signals (bottlenecks, technical debt, capability gaps, stuck customer funnel, marketplace publish-protection, health degradation) — directly covering 6 of the directive's 12 named Observe areas.

Two pieces named explicitly in this directive's own text had genuinely zero prior coverage, confirmed by direct grep before writing any code:

1. **"Continuously measures whether every implemented evolution actually improved"** X — `mark_implemented()` recorded a note and nothing else; no before/after comparison of any real metric existed anywhere.
2. **Ranking by strategic value/revenue impact/execution cost/long-term sustainability/risk/confidence** — no per-proposal ranking of any kind existed; `list_evolution_queue()` returned entries in reverse-chronological order only.

## What was built

### Measure (the real gap)

`evolution_queue.py` gained `_capture_metrics_snapshot()` — a real, source-cited snapshot across the only three post-implementation signals this factory can actually measure today: revenue (`channels/ledger.py`'s real `revenue_trend()`), reliability (`health_trend.py`'s real `GET /health` snapshot history), and customer value (`customer_pipeline.py`'s real `funnel_conversion_summary()`). Scalability, automation, and execution speed are deliberately excluded from the snapshot itself — no real per-proposal signal for any of them exists anywhere in this factory, confirmed by grep, and `measure_outcome()` reports them as an explicit `NO_REAL_SIGNAL` string rather than fabricating a number.

`mark_implemented()` now captures this snapshot as `baseline_snapshot` at the real moment of implementation (best-effort — a snapshot failure never blocks the real state transition). `measure_outcome(proposal_id, min_days_elapsed=7)` compares a fresh snapshot against that baseline no sooner than 7 real elapsed days later (refuses, honestly, to measure sooner), reporting `IMPROVED`/`DEGRADED`/`NO_CHANGE`/`NOT_ENOUGH_DATA` per dimension — never a fabricated verdict when a value is missing on either side. Each real call appends a dated entry to the record's own `outcome_measurements` list, which is the actual trend the directive's "continuously" asks for, not a one-shot check. `run_daily_outcome_measurement_cycle()` is the one automatic path — it iterates every real `IMPLEMENTED` record and calls `measure_outcome()`, honestly skipping (not silently) any still under the 7-day window. `list_measured_outcomes()` is the Mission Control aggregate.

**A real bug found and fixed during implementation**: `_record_history()` appends a second `stage_history` row still tagged `IMPLEMENTED` every time a measurement logs its own detail line. The first draft derived `implemented_at` by scanning `stage_history` for the last `IMPLEMENTED` entry — which meant every second real measurement silently reset its own elapsed-time clock to zero, permanently blocking any factory from ever accumulating a real multi-measurement trend past the first call. Fixed by storing `implemented_at` once, explicitly, as its own field at `mark_implemented()` time, with a stage_history-derived fallback only for a record implemented before this field existed. Covered by a named regression test (`test_repeated_measurement_does_not_reset_the_elapsed_time_clock`).

### Rank (the real gap)

`rank_proposal(record)` computes a disclosed heuristic over fields the record already has — never a second, fabricated numeric priority score. `revenue_impact` is a real keyword match (same disclosed-heuristic discipline as `SENSITIVE_AREA_KEYWORDS`) over the proposal's own `why_needed`/`evidence`/`tool` text. `execution_cost` reuses `simulation.rollback_complexity` verbatim. `long_term_sustainability_concern` reuses `decision_flags.duplicate_architecture_risk` verbatim. `risk` combines `policy_risk` and `rollback_complexity`. `confidence` is mechanical: whether the proposal's own `estimated_roi`/`implementation_effort` fields carry real data or the honest "غير مقاس بعد" (not yet measured) marker. `strategic_value` is honestly reported `not_computed` with a stated reason — `strategic_intelligence_core.strategic_score()` is per-niche, not per-proposal, and most evolution proposals are company-wide, so no real per-proposal strategic-value signal exists in this factory today. Wired into `list_evolution_queue()`'s own entries as `entry["ranking"]` — no new endpoint needed.

## What was deliberately NOT built

New proposal-generator categories for the directive's other named actions (create/merge department, replace AI model, retire product, expand market, redesign pipeline) were not added — no real underlying signal exists for any of them today (department lifecycle tracking, AI-model-swap evaluation, and product retirement all remain genuinely absent from this factory, same disclosed gap `capital_allocation_engine.py`/ADR-139 already recorded for "Reduce vs. Pause" / "Accelerate vs. Increase"). Building generators for these would mean fabricating a signal, which this factory's own standing discipline forbids. The directive's other 6 Observe areas not yet feeding `tool_intelligence.proposals` (competitor evolution, AI capability evolution, cost efficiency, revenue trend as a standalone generator, execution speed, knowledge graph) each have a real underlying module already (`competitor_discovery.py`, `ai_capability/registry.py`, `channels/ledger.py`, `knowledge_graph/build.py`) but are not yet wired as proposal generators — a real, scoped, disclosed gap for a future round, not fabricated to look closed here.

Execute stays exactly as human-gated as ADR-133 left it — this round adds zero new execute-capable action; `measure_outcome`/`run_daily_outcome_measurement_cycle` only ever append to a record already `IMPLEMENTED` by a real, separately-reviewed founder action.

## Mission Control

`mission_control_api.py` gained `evolution_outcome_daily_cycle` (dispatches `run_daily_outcome_measurement_cycle()`) and `evolution_measured_outcomes` (dispatches `list_measured_outcomes()`). `server.js`'s `SERVICE_REGISTRY` gained `evolution-measured-outcomes`; the existing `evolution-queue` entry's description was updated to mention the new `ranking` field. `mission_control_executive_v1.html` gained one read-only panel. `factory_loop.js` gained `maybeMeasureEvolutionOutcomes()` — same once-per-calendar-day gate as every other daily tick addition, wired immediately after `evolution_queue_intake` in the tick's actions array.

Verified live via a real logged-in `server.js` HTTP round-trip on a disposable test server (started via `node server.js`, killed by exact PID after): login → `GET /api/v1/evolution-queue` (confirmed real `ranking` field present on all 5 real `AWAITING_FOUNDER_APPROVAL` proposals) → `GET /api/v1/evolution-measured-outcomes` (honestly empty — zero real `IMPLEMENTED` proposals exist yet) → `/health` confirmed still responding. `data/evolution_queue_state.json` confirmed byte-identical after (all reads, one write path — `mark_implemented` — never exercised against the real file).

## Validation

`tests/test_evolution_queue.py` gained 18 new tests (39 total, all passing): baseline-snapshot capture on `mark_implemented` (including a snapshot-failure-must-not-block-the-real-transition case), `measure_outcome`'s stage guard / min-days-elapsed refusal / IMPROVED / DEGRADED / NOT_ENOUGH_DATA paths, the elapsed-time-reset regression test above, `run_daily_outcome_measurement_cycle`'s honest skip behavior, `list_measured_outcomes`'s `NOT_YET_MEASURED` state, and `rank_proposal`'s revenue-keyword/policy-risk/strategic-value-not-fabricated behavior. Every test uses a temp state path and mocks `_capture_metrics_snapshot` directly — never the real `data/evolution_queue_state.json` or a live network/file read.
