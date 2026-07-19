# ADR-079 — Intelligence Layers → Ladder Scoring: Two Real Connections, Three Honest Non-Connections

**Date:** 2026-07-19
**Status:** Adopted. Two real, traceable data flows built and tested; three modules deliberately left unconnected to per-opportunity scoring, with the specific reason each one can't be honestly wired yet.

---

## The ask, and why it needed a judgment call

The founder asked to "connect the new intelligence layers (executive_intelligence, strategic_intelligence, infrastructure_intelligence, ai_capability, tool_intelligence) into the 10-minute tick so their reports actually influence ladder_opportunity_score weights — data flows, not isolated modules."

`ladder_opportunity_score()`'s five components (`market_demand`, `competition_favorability`, `profit_potential` — each 0.15 — `recurring_revenue_potential` 0.25, `reusability` 0.30) are **mission-specified weights** (`MASTER_CHARTER.md` §2's explicit business-strategy reasoning), not something this session should silently rewrite. Rewriting them to "average in" five modules that mostly have no per-niche signal today would have meant inventing a number to make the connection look more complete than it is — exactly what this factory's own culture (this entire session, `quality_doctor.py`'s fabricated fixes, `config/capability_registry.json`'s REAL/ESTIMATED/DISCOVERY discipline) exists to prevent.

So: build every connection that's real and traceable, and say plainly which modules don't have one yet, instead of forcing five arbitrary hooks.

## What's real and built

### 1. `infrastructure_intelligence` → `profit_potential` (via `_score_margin()`)

`_score_margin()` already used `_real_average_ai_cost_per_call()` — a flat all-time average of every real logged Groq call — as the real cost input to its margin calculation. A flat average understates a genuine recent cost spike. New `profit_oracle._real_ai_cost_trend()` computes the same real signal `lib/infrastructure_intelligence.js`'s `getCostTrend()` already surfaces on the dashboard (recent 7-day average vs. the real trailing daily average, flagged as an outlier only when the recent average is genuinely more than double a real trailing baseline) — reimplemented in Python since `_score_margin()` needs it as a scoring input, not a display value. When a real outlier exists, `_score_margin()` now uses the recent average instead of the flat one, and records why in its notes. No real outlier today (only 39 logged calls, all in the `2026-07-18`/`19` window) — this is real, active wiring waiting for real data, not a currently-visible effect.

### 2. `executive_intelligence` → a real production dispatch gate (not a scoring weight)

`ladder_opportunity_score()` has no field for "is the production engine itself currently reliable" — that's a fair question about *whether to act on* a score, not a fifth scoring component. New `executive_intelligence/production_gate.py::check_production_engine_health()` reuses `engine_health.compute_engine_health()` (already real, tested, ADR-052) to check the real `production` stage's success rate from `data/orchestrator_timeline.jsonl`; `factory_loop.js`'s `huntGolden()` now calls it (via a new `profit_oracle.py --production-health-gate` CLI flag, `checkProductionEngineHealth()`) right before dispatching a ladder-tagged opportunity to `runLadderOpportunityPipeline()`, and skips this cycle with an honest, logged reason if the real success rate is below the same 80% alert threshold the daily executive report already uses to flag a bottleneck. Fails OPEN on any error (spawn/parse failure), same discipline as the pre-existing opportunity-score gate — a check that can't run must never block production. Real data today: 1,344 real `production` executions, all `SKIPPED_NOT_APPLICABLE` (matches the known 0/1344 ladder-unblocked history, `project_strategic_ladder_pivot_20260717.md`) — `success_rate` is honestly `None` (no real successes or failures yet to compute a rate from), so this gate reports `ok:true` with "not enough data" rather than fabricating a rate.

## What's deliberately NOT connected, and why

- **`strategic_intelligence`**: its own `which_decision_patterns_lead_to_success` answer is already, honestly, `"Unknown"` — 0 real sales samples matched, below the minimum of 3 for any real recalibration (`decision_engine.learning.recalibration_report()`). There is no real signal here to feed into scoring yet; the module is correct to say so, and this ADR doesn't override that with a fabricated pattern.
- **`ai_capability`**: has exactly one measured provider (Groq). There is no comparative AI-provider signal to route scoring or production decisions by — every other provider is honestly `DISCOVERY`-level (Track B2, `COMPANY_INTEGRATION_MAP.md`'s "Autonomous Digital Company v1" section). Nothing to connect until a second provider has real logged usage.
- **`tool_intelligence`**: its proposals (vector store, image-diff QA, a second AI credential) are org-level infrastructure recommendations, not per-niche signals. There is no honest way to make a tool-integration proposal influence a specific opportunity's score — that would be a category error, not a missing wire.

## Tests

- `tests/test_production_gate.py` (4 tests): the gate never blocks on missing/insufficient history, correctly blocks on a real low success rate with an honest reason, never blocks on a different engine's real problems.
- `tests/test_opportunity_score.py`: 6 new tests (`TestRealAiCostTrend`, `TestScoreMarginUsesRealCostTrendOnAGenuineOutlier`) — missing log/no-recent-data/genuine-spike/steady-spend cases for the trend function, plus confirms `_score_margin()`'s behavior is byte-for-byte unchanged when no real outlier exists.
- `tests/test_factory_loop_golden.js`: 2 new tests for `checkProductionEngineHealth()` — a real call against real data, and a broken-script-path case confirming it fails OPEN (`ok:true`), never blocking production on its own error.
- Full suite green throughout (Python + JS), zero regressions in every module that calls `score_opportunity()`/`_score_margin()`/`ladder_opportunity_score()` (market_hunter, revenue_pipeline, product_families, orchestrator, etc.).
