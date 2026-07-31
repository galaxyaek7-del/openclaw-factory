# ADR-157 — Autonomous Company Runtime (documented + safe parts)

**Date:** 2026-07-31
**Status:** Adopted. Full Runtime/Event Bus/Workflow Engine/Queue Manager architecture documented, zero code. Health Monitoring extension, Executive Replay, Autonomous Daily Cycle status, Self-Healing citation, and a read-only Company State label built — all real, additive, citation-based.

---

## The directive (verbatim)

> Founder Directive — Autonomous Company Runtime (Next Core Phase)
>
> The Executive Brain is complete.
>
> Do NOT create new divisions.
>
> The next mission is to transform Galaxy Forge into a continuously operating autonomous company.
>
> Objectives:
>
> 1. Build Company Runtime. The company must operate continuously as one living system.
>
> 2. Build Global Event Bus. Every division publishes events. Every interested division subscribes. No polling where events are possible.
>
> 3. Build Autonomous Workflow Engine. Every task flows automatically through departments according to dependency rules.
>
> 4. Build Enterprise Queue Manager. Prioritize every workload dynamically. Support retries, failures, escalation and recovery.
>
> 5. Build Company State Machine. Define clear company states: BOOT, READY, PRODUCTION, LEARNING, OPTIMIZING, SCALING, MAINTENANCE, RECOVERY.
>
> 6. Build Health Monitoring. Every service exposes: Health, Latency, Failure rate, Resource usage, Last successful execution.
>
> 7. Build Self-Healing. Automatically restart failed workflows. Retry transient failures. Escalate only when recovery fails.
>
> 8. Build Executive Replay. Allow the CEO to replay any important company decision chronologically.
>
> 9. Build Autonomous Daily Cycle. Morning review. Opportunity scan. Production. QA. Publishing. Affiliate updates. Analytics. Knowledge update. Executive report.
>
> 10. Mission Control must evolve into a true live Operations Center where every workflow, queue, dependency and recovery process is visible in real time.
>
> Rules: Reuse existing architecture. No duplicate systems. Simulation mode remains first-class. Production mode remains isolated. No fake operational metrics. Everything must be testable. ADR + tests + documentation required.

## The real conflict, surfaced before any code was written

Objectives 1-4 and 7 together — "operate continuously as one living system," a Global Event Bus, an Autonomous Workflow Engine that auto-flows tasks across departments, an Enterprise Queue Manager, and Self-Healing that "automatically restarts failed workflows" — describe an always-on autonomous daemon with new real-time event/queue infrastructure. **This exact question has been asked and declined 5 times in this codebase's history**: ADR-107 → ADR-110 ("Global Autonomous Business Operating System," nearly this exact directive under a different name) → ADR-115 → ADR-142 (Final Executive Directive, reconfirmed the 4 protected human-gates) → ADR-147 (GF-OS, this same session, hours before this directive: *"the Mission Queue is a real citation of already-real scheduler.py/orchestrator.py, no new queue infrastructure"*).

Flagged via `AskUserQuestion` before any code. **The founder's answer: document the full architecture, build only the genuinely safe, real, citation-based parts.**

## What was documented only (zero code)

- **Company Runtime** as an always-on process (no OS-level daemon, no persistent background loop — `factory_loop.js` remains manually invoked, exactly as every prior round today confirmed).
- **Global Event Bus** (no pub/sub infrastructure, no new event system beyond the real, already-append-only ledgers this factory already writes to).
- **Autonomous Workflow Engine** (no automatic cross-department task execution beyond what already flows through the existing human-gated decision points).
- **Enterprise Queue Manager** (no new queue infrastructure — `scheduler.py`'s real buckets and `orchestrator.py`'s real stages, already cited by `gfos.py::mission_lifecycle_summary()`, ADR-147, remain the only real "queue" this factory has).
- **Self-Healing's "automatically restart failed workflows"** specifically (the *retry* and *escalate* halves of Objective 7 are real and already built — see below; auto-*restart* of a workflow that failed, without human review, is not built and stays out of scope).

## What was built

**1. Health Monitoring (Objective 6) — `lib/metrics.js` extension.** `recordRequest()` gains two small additive Maps, `lastSuccessAt`/`lastFailureAt` per route (populated at the same real call site every other counter already uses — no new instrumentation). `summarizeRoutes()` gains real `error_rate_pct` (errors/count, honestly `null` when count is 0) and `last_success_at`/`last_failure_at` per route. `GET /api/v1/metrics.json` (ADR-151) automatically reflects the new fields. Health and Latency were already real (`GET /api/v1/health`, `summarizeRoutes()`'s existing `avg_latency_ms`); Resource usage is already real company-wide (`infrastructure-status`, not yet per-service — disclosed, not force-fit).

**2. `company_runtime.py`** (new):

- **`executive_replay()`** (Objective 8) — real chronological walk over `gfos.py::enterprise_timeline()` (ADR-147, already merges 6 real ledgers), optionally date-filtered, threading in `executive_decision_memory.py::explain_decision()`'s (ADR-145) real detail when a `decision_id` is passed. No new storage, no new event log.

- **`autonomous_daily_cycle_status()`** (Objective 9) — a real, disclosed, static citation (same convention `execution_status.py`'s own `_OWNER_BY_STAGE` mapping already established) of `factory_loop.js`'s real tick-driven functions for 7 of the 9 named stages. 2 are honestly `NOT_ARCHITECTED`: "morning review" (no real, single equivalent function exists) and "affiliate updates" (`affiliate_commerce/`, ADR-149/153, is genuinely not tick-wired into `factory_loop.js` yet). Adds zero new automatic calls — this factory's real daily cadence is unchanged.

- **Self-Healing (Objective 7)** — deliberately **not** a separate function. `mission_control_api.py::_recovery()`'s existing dispatcher already surfaces `pending_retries` (the real "retry transient failures" mechanism, replayed every real tick by `factory_loop.js::processPendingRetries()`); it gained one new field, `escalation_when_recovery_fails`, citing the real, already-wired `checkNeedsAttention()`/`writeNeedsAttention()` (writes `NEEDS_ATTENTION.md`, notifies the founder via the existing Telegram channel). No duplicate citation path — per the directive's own "no duplicate systems" rule.

- **`company_state()`** (Objective 5) — a real, priority-ordered, **read-only** status label. Every condition cites a real signal: RECOVERY (real active critical/emergency `resilience_monitor.py` alerts, or a real active `safe_mode.py` marketplace-publishing emergency stop); MAINTENANCE (a real unstable `ai_generation`/`market_intelligence` subsystem); PRODUCTION (a real `factory_state.py` `current_task` in flight); OPTIMIZING (real `evolution_queue.py` proposals `AWAITING_FOUNDER_APPROVAL`); LEARNING (real `IMPLEMENTED` proposals not yet measured); READY (default). **SCALING is defined (the directive's own named state) but never selected** — no real scale-out signal exists anywhere in this factory (single Express process, no worker pool, no queue system). **BOOT is deliberately not computed in Python** — `mission_control_api.py` runs as a fresh, stateless subprocess per call, so it has no real process uptime to measure; the real Node server's own `process.uptime()` (the same real signal `GET /api/v1/health` already exposes) overrides to BOOT at the `company-state` route handler in `server.js` when the server process itself started under 60 real seconds ago. `company_state()` is purely informational — nothing in this factory reads its output to change what it does.

**3. Mission Control**: 3 new `SERVICE_REGISTRY` entries (`executive-replay`, `autonomous-daily-cycle-status`, `company-state`) + panels; `self_healing` folds into the existing `recovery-status` panel rather than a 4th new one, per the directive's own "no duplicate systems" rule.

## A real, pre-existing bug found and fixed while building this

While testing `company_state()`'s PRODUCTION check, `factory_state.load_state()`'s real `active_workflow` field was found stuck at `"learning"` even though `current_task` was `null` — meaning no real task was actually in flight. Root cause, confirmed in **both** language mirrors (`factory_state.py` and `lib/factory_state.js`): `clear_current_task()`/`clearCurrentTask()` clears `current_task` but never clears `active_workflow`, so it stays permanently "sticky" to whatever task last started, forever. This directly affects the **already-shipped** `recovery-status` Mission Control panel today — it has been showing a stale "active workflow" since the first real task this factory ever ran.

Fixed in both files (one real, additive line each: `active_workflow = None` alongside `current_task = None`), the real stale value in `data/factory_state.json` corrected to match, and test coverage added to both `tests/test_factory_state.py` and `tests/test_factory_state.js` (neither previously asserted `active_workflow` was cleared — the exact gap that let this ship unnoticed). `company_state()`'s PRODUCTION check now uses `current_task` (always reliably cleared) as its primary signal, citing `active_workflow` only as secondary evidence.

## What is explicitly NOT done this round

No always-on daemon/runtime process (6th time this exact question has been declined). No event bus. No new queue infrastructure. No new automatic cross-department task execution. No new auto-restart mechanism beyond the existing real tick-driven retry/escalation. `company_state()` never switches any real behavior — informational only.

## Validation

Live-verified via CLI: `executive_replay()` returns real, date-filterable timeline entries; `autonomous_daily_cycle_status()` correctly cites 7 real tick-wired stages and honestly flags 2 gaps; `company_state()` correctly returned `OPTIMIZING` live (5 real proposals genuinely `AWAITING_FOUNDER_APPROVAL`) both before and after the `active_workflow` fix, and never returns `SCALING`/`BOOT`. `_recovery()`'s new `escalation_when_recovery_fails` field confirmed present. `lib/metrics.js`'s new fields verified via 18 passing tests (`node --test tests/test_metrics.js`, including 4 new `summarizeRoutes()` tests closing a real, pre-existing zero-coverage gap for that function since ADR-151). `tests/test_company_runtime.py` (11 new tests) confirms `company_state()` never returns SCALING/BOOT and every field carries a real source citation. Both `factory_state` test suites (JS + Python) extended with the missing `active_workflow` assertion and re-verified passing. Full test suite re-run.
