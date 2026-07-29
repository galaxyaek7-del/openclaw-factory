# ADR-142 — Final Executive Directive: Autonomous Operations

**Date:** 2026-07-29
**Status:** Adopted.

---

## The directive

"FINAL EXECUTIVE DIRECTIVE — Galaxy Forge must evolve into a fully autonomous digital enterprise." Every operational activity — discover, validate, analyze competition, allocate capital, create blueprints, build, test, publish, monitor, optimize pricing, collect feedback, learn, improve, expand, retire, reinvest, report, maintain knowledge, detect risks, recover, continuously improve — must execute automatically, with Founder approval mandatory only for strategic direction changes, major financial commitments, and legal obligations.

## The real conflict, surfaced before any code was written

The literal ask would loosen 4 standing, explicitly human-gated systems, two of them built earlier the same day: `evolution_queue.py`'s Execute step (its own governing text: "must not be loosened without asking again"), `capital_allocation_engine.py`'s "the engine recommends, the Founder decides", business retirement (no real system exists, by design — `value_engine.py`'s `retirement_recommendation` is explicitly "never a final retirement decision"), and `channels/publish_protection.py`'s Founder Protection layer for a genuinely new channel arm's first publish or any elevated-risk publish.

**Asked via `AskUserQuestion`. The Founder's answer: keep all 4 gates exactly as-is.** Treat capital reallocation, business retirement, self-improvement execution, and new-channel/elevated-risk publishing as themselves falling under this directive's own strategic/financial/legal exception clause. See `[[feedback_final_executive_directive_scope]]` (memory).

**A second, load-bearing finding**: this exact "should Galaxy Forge run as an always-on autonomous daemon" question was already asked and *declined three times* in prior sessions — `master_loop.py`, ADR-107 → ADR-110 → ADR-115. `master_loop.py` exists today only as a real, read-only citation layer (`trace_lifecycle()`, `mission_control_heartbeat()`), deliberately never wired into `factory_loop.js`'s tick. This directive does not resurrect that rejected daemon — `factory_loop.js` is a separate, already-approved, already-running continuous tick mechanism (once started, it ticks every ~10 minutes with no OS-level scheduler needed). The real, narrow scope here is adding a couple of confirmed-safe, read-only, no-execution steps to that *already-approved* tick.

## What was already automatic (confirmed via direct code research, not assumed)

`factory_loop.js`'s real, current per-tick list already covers 10 of the directive's ~21 named activities with zero new code: discover (`huntGolden()`), validate demand (same call's real score-gate + `evidence_completeness.py`), build/test/publish (all inside the same `huntGolden()` call, gated by existing env flags and `channels/publish_protection.py`), monitor sales (`pollSales`), improve existing assets (daily evolution-queue intake, stops at `AWAITING_FOUNDER_APPROVAL`), generate executive reports (4 daily reports), detect risks (`resilience_monitor.py`, every tick).

3 activities were found genuinely ambiguous on closer inspection and deliberately excluded rather than guessed at: `decision_engine/feedback.py::sync_outcomes()` ("learn from results") is reachable via a registry/plugin dispatch path (`orchestrator/engines/learning.py` → `orchestrator.orchestrator.run_cycle()` → `factory_loop.js`'s `--run-ladder-opportunity` call) whose exact per-tick automaticity could not be confirmed with full certainty; auto-refreshing `competitor_discovery.py` risks a real, rate-limit-sensitive live network call from a read path; `growth_engine.py::evaluate_channel_expansion()` is real but only invoked on-demand, not tick-wired. Each is tagged `ambiguous_not_touched` with its own disclosed reason, not silently assumed either way.

## The 2 genuinely new, confirmed-safe additions

1. **`knowledge_graph.build_graph()`** ("maintain institutional knowledge") — confirmed via direct grep: zero existing callers anywhere in `factory_loop.js` or the orchestrator. A pure, read-only rebuild of already-real data, persisted via `knowledge_graph.build.save_snapshot()` (already existed, never called until now) to `data/knowledge_graph_snapshot.json`. Wired as `mission_control_api.py`'s new `knowledge_graph_daily_snapshot` endpoint, called by `factory_loop.js`'s new `maybeGenerateDailyKnowledgeGraph()` — same once-per-calendar-day gate as the 4 existing daily reports.
2. **`autonomous_business_builder.generate_pending_business_blueprints()`** ("create business blueprints") — new function in `autonomous_business_builder.py` (built earlier the same day with zero automatic wiring until now). For every real ACCEPTED decision without an already-recorded real Business Blueprint, generates and records up to a capped batch (default 2) per call — append-only dedup ledger at `data/generated_business_blueprints.jsonl`, same convention as `data/board_meetings.jsonl`/`data/incidents.jsonl`. Read-only/no-execution: a blueprint is pure analysis, never a publish or spend. Wired as `mission_control_api.py`'s new `generate_pending_business_blueprints` endpoint, called by `factory_loop.js`'s new `maybeGenerateBusinessBlueprintsForNewAcceptedDecisions()` — same once-per-calendar-day gate.

Both additions are read-only/no-execution and touch none of the 4 Founder-protected gates.

## The one new module: `autonomous_operations_status.py`

A real, citation-only status map answering the directive's own implicit question — is Galaxy Forge running autonomously right now, and exactly what does that include. `activity_status()` tags each of the directive's 21 named activities `automatic` / `automatic_new` (the 2 additions above) / `human_gated_by_design` (the 4 protected gates + business retirement) / `ambiguous_not_touched` (the 3 deferred items above) — every tag citing the real function/file that proves it. `autonomous_operations_summary()` aggregates real counts + the 4 protected-gate names + a citation of the `master_loop.py`/ADR-107/110/115 precedent, so this decision's history is never lost or silently re-litigated by a future session.

## Mission Control

`mission_control_api.py` gained 3 endpoints: `autonomous_operations_status`, `knowledge_graph_daily_snapshot`, `generate_pending_business_blueprints`. `server.js`'s `SERVICE_REGISTRY` gained `autonomous-operations-status` (no-input, cheap — pure dict lookups, no timeout disclosure needed). `mission_control_executive_v1.html` gained one read-only panel. Verified live via a real logged-in `server.js` HTTP round-trip on a disposable test server (port 3199, killed by exact PID after) — login → `GET /api/v1/autonomous-operations-status` → real 21-activity payload confirmed → `.../health` confirmed `ok`.

## Validation

New tests: `tests/test_autonomous_operations_status.py` (new, 9 — every status tag validated, the 4 protected gates never mis-tagged `automatic`, the 2 new additions correctly tagged `automatic_new`, counts internally consistent, the `master_loop.py` precedent cited). `tests/test_autonomous_business_builder.py` (+8 — `_read_generated_blueprint_niches()`/`_record_generated_blueprint()`'s real dedup/append behavior, `generate_pending_business_blueprints()`'s capped-batch/idempotent/zero-limit/`None`-blueprint/niche-filter behavior, every real source mocked). `tests/test_factory_loop_daily_knowledge_graph.js` / `test_factory_loop_business_blueprint_generation.js` (error paths only — the real success path touches real files and (for blueprints) costs real ~16s/niche compute, so it was verified manually instead, matching the existing convention for every other daily-report tick function).

Live E2E against real factory data: both new `factory_loop.js` functions were run directly (bypassing the ~10-minute tick wait) against this factory's 3 real ACCEPTED decisions. First run: `maybeGenerateDailyKnowledgeGraph()` built a real 2938-node/2759-edge graph and persisted it; `maybeGenerateBusinessBlueprintsForNewAcceptedDecisions()` generated exactly 2 of 3 real blueprints (capped at the default limit), correctly leaving 1 pending. Second run (same calendar day): both correctly reported `action: 'none'` — the daily gate held, proving no redundant regeneration. `data/generated_business_blueprints.jsonl` confirmed append-only with the 2 real generated records.

## Constitution-first / no-autonomous-high-risk boundary (deliberately unchanged)

Both new tick additions are read-only and recommend-only. Neither touches any of the 4 Founder-protected gates reconfirmed above. `master_loop.py`'s always-on-daemon proposal stays declined — this ADR extends the already-approved `factory_loop.js` tick only, never introduces a new standalone process.

## What's still honestly deferred / not built

`analyze_competition` (auto-refresh), `learn_from_results` (per-tick automaticity of `sync_outcomes()`), and `expand_successful_businesses` (tick-wiring `evaluate_channel_expansion()`) remain `ambiguous_not_touched` — each has a real, disclosed reason above, not a guess. A future round can verify each precisely rather than risk a redundant or wrongly-gated addition made under this directive's own time pressure.
