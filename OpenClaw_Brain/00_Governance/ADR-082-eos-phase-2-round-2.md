# ADR-082 — Enterprise Operating System, Phase 2, Round 2

**Date:** 2026-07-19
**Status:** Adopted.

---

## Why this exists

The founder reframed OpenClaw's mission (Five Permanent Pillars — durable memory, not a build task) and named 7 focus areas for this round: Department Events, Unified Priorities Engine, Autonomous Execution, Opportunity Intelligence, Commercial Intelligence, Revenue Intelligence, Evolution Engine — instructing that nothing working be rebuilt, and every change be evaluated against 6 CEO-level questions (smarter? better decisions? more valuable assets? bigger future revenue? harder to copy? closer to a real global company?) before writing code.

Three research passes against the real, current repo found **4 of the 7 named areas already real and substantially complete**:

- **Commercial Intelligence** (`commercial_execution/` + the `commercial` tab) — nothing genuinely missing. No new work.
- **Evolution Engine** (`evolution_engine.py`) — its own docstring already declines general duplicate-work/logic detection (needs AST/semantic analysis this factory doesn't have). No new work.
- **Opportunity Intelligence** — the discovery→score→rank pipeline is complete; the only real gap is that a founder needs 4 separate tabs (market/goldenhunter/pioneer/opportunities) to see the whole picture — the exact gap the Unified Priorities Engine closes.
- **Revenue Intelligence** (`revenue_pipeline/`) — complete for what it does; the one real gap is a genuine revenue trend over time (`finance_data.json` only ever held current totals).

**Autonomous Execution** needed the most care: `ADR-081` (Track C) already drew a deliberate line — autonomous execution of any recommendation engine's output stays manual, because every autonomous action in this factory is operational, never architectural. That line is confirmed still correct and was **not** moved. Instead, research surfaced one real, concrete safety asymmetry: `FACTORY_LIVE_PUBLISH` did not gate the modern ladder pipeline at all — only `FACTORY_AUTO_PRODUCE` did (`orchestrator/orchestrator.py::_cli_run_ladder_opportunity()` hardcoded `execute_production=True`), even though `AUTO_PRODUCE_ACTIVATION_CHECKLIST.md` (citing `ADR-009` §9.2) explicitly documents three independent barriers to a real, live publish: Dual Inspection AND `FACTORY_LIVE_PUBLISH` AND a real platform token. Tightening a gate can only reduce risk, never increase it — a bug fix restoring compliance with the founder's own pre-existing design, not a new invented safety feature. A broader "run more ACTION_REGISTRY entries on an automatic cadence" question is deferred to Track C — applying the founder's own instruction ("if the answer is no, reconsider before writing code") to my own uncertainty about whether it's additive or redundant with Golden Hunter's existing daily tick.

## What Round 2 built

**Track A — production-safety hardening**
- `orchestrator/engines/publishing.py::run()` now computes `dry_run = context.get("dry_run", True) or not _live_publish_enabled()` — a real live publish attempt on the modern pipeline now requires both `context["dry_run"] is False` AND `FACTORY_LIVE_PUBLISH=true`, matching the legacy path's existing convention. 3 new tests (`tests/test_orchestrator.py::TestPublishingEngineHonorsFactoryLivePublish`) confirm all three truth-table cases.

**Track B1 — Department Events**
One shared envelope log, `data/department_events.jsonl` — `{event_id, emitted_at, department, event_type, ref_id, source_log, summary}`, envelope-only (no business data ever duplicated). New `department_events.py` (Python) + `lib/department_events.js` (JS). Wired at the same call site as each existing real writer — never a re-derivation scan:
- `factory_loop.js::appendGoldenHunterEvent()`
- `lib/recovery_log.js::recordRecoveryAction()`
- `ai_capability/registry.py::record_capability_request()`

Pioneer and Researchers/Customer Intelligence get a schema slot only, no real emitter — confirmed Pioneer shares Golden Hunter's write point, and Researchers/Customer Intelligence still have no real code to emit from.

A test-isolation gap was found and fixed mid-round: the first pass of these 3 emit points had no way to redirect the `department_events.emit()` call to an isolated path independent of the caller's own already-isolated log path, so running the existing test suites was silently writing test data into the real `data/department_events.jsonl`. Fixed by adding an optional `departmentEventsPath`/`department_events_path` parameter at all 3 call sites, threading it through every existing test, and adding one explicit regression test per language confirming the real default log is untouched when an override is given.

**Track B2 — Unified Priorities Engine** (also closes Opportunity Intelligence's real gap)
New `unified-priorities` service (`server.js`) combining, side by side, **never merged into one fabricated score**: `readNextDollarActions()` (existing FACTORY_STATUS.md scrape), the ranked ACCEPTED queue (`decision_engine/ranking.py::rank_queue()` via the existing `opportunity-queue` service), and a new markdown-section read of `OpenClaw_Brain/00_Governance/MASTER_CHARTER.md`'s `## 2. Strategic Production Priority Ladder` heading (same technique as `readNextDollarActions()`). New `unified-priorities` `SERVICE_REGISTRY` entry + one new Mission Control tab (`unifiedpriorities`), verified live end-to-end with real authentication.

**Track B3 — Revenue trend over time** (the one real Revenue Intelligence gap)
New `channels/ledger.py::revenue_trend()` reads the ledger's own real, timestamped `sale` events, bucketed by day — the same "recent 7d vs. trailing daily average" pattern already proven by `lib/infrastructure_intelligence.js::getCostTrend()` and `factory_loop.js::revenueSince()`. Surfaced as an additive field in the existing `revenue-summary` service / `revenue` Mission Control tab, not a new tab. With zero real sales recorded today, it honestly reports that rather than fabricating a trend line — verified live.

## Duplication avoided

- Department Events emits at the same call site as each real existing writer; no re-derivation/scan job was built (that would be the actual duplicate-store risk this design exists to avoid).
- Unified Priorities Engine reuses `readNextDollarActions()` and the existing `opportunity-queue` service verbatim rather than re-scoring opportunities a second way.
- `revenue_trend()` reuses `channels/ledger.py`'s existing `read_events()`/`_extract_sale_amount()` rather than re-parsing the ledger a second way.

## Deferred, documented (Track C)

Broader automatic-cadence execution of read/decision-only `ACTION_REGISTRY` entries (e.g. `rerun-market-analysis`, `trigger-opportunity-evaluation`) — pending founder confirmation these are additive, not redundant with Golden Hunter's daily tick, given real live-network cost. Autonomous execution of any recommendation engine's output — unchanged, never, by this system's own design. Per-product sale attribution, general duplicate-work/logic detection, and revenue forecasting — unchanged from `ADR-081`, still blocked on the same real platform/technical limitations.

## Tests

`tests/test_department_events.py` (6) + `tests/test_department_events.js` (6), 3 new tests in `tests/test_orchestrator.py` (`TestPublishingEngineHonorsFactoryLivePublish`), 5 new tests in `tests/test_ledger.py` (`TestRevenueTrend`), plus isolation-regression tests added to `tests/test_recovery_log.js` and `tests/test_ai_capability.py`. Full suite green: 806 Python tests, 189 `node --test` JS tests, plus the two custom-runner suites (`test_factory_loop_golden.js` — 56, `test_department_events.js` — 6). Every new service/tab verified live against a real running server instance with real authentication.
