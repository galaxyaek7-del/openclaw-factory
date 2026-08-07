# Production Hardening Report

**Date:** 2026-07-17
**Directive:** "Executive Directive — Phase 10B: Performance Engineering & Production Hardening," objectives 3, 5, 6

---

## Error handling, timeouts, retry strategy, graceful degradation

- **Timeouts — one real gap found and fixed** (see `BOTTLENECK_ANALYSIS.md`): every Python subprocess spawn in `server.js` now has a bounded timeout via a new shared `killAfterTimeout()` helper — 30s for fast local-file services, 15 minutes (a hang safety net, not a normal limit) for the slow real-network async actions. Verified with a synthetic hung-process test and a clean-process control test.
- **Retry strategy — already real, confirmed present, not duplicated**: `orchestrator/retry.py`'s `run_with_retry()` (max 3 attempts, configurable backoff) is used by `orchestrator.run_cycle()` — the one real pipeline every market-intelligence/decision path reuses (`ADR-051`). `channels/gumroad_publisher.py` has its own real retry logic for transient publish failures (confirmed via memory of this session's own earlier work, re-verified present via grep this phase).
- **Graceful degradation — already built, re-verified**: `run-full-cycle`'s 8 stages are each independently wrapped (Phase 11); `notifyN8nProductionEvent()` never blocks a real production run if n8n is unreachable (Phase 10A/n8n gap fix). No new graceful-degradation code was needed this phase — the existing mechanism was audited, not rebuilt.
- **Service recovery**: the single-writer guard (Phase 10A) plus this phase's new timeout guard together mean a stuck action now recovers on its own (times out, job marked `failed`) rather than requiring a server restart to un-wedge.
- **Unexpected failures**: `runActionSync`/`runPythonActionAsync`/`runFullCycleActionAsync` all catch and record every error into the job's own `error` field — no unhandled promise rejection path was found during this audit.

## Logging

Every request through the Unified Service Layer, every action trigger, every stage transition, and (new this phase) every timeout event logs a structured entry to `logs/service_layer.log` via the existing `logServiceCall()` — confirmed real and populated throughout this session's live testing, not asserted from code reading alone.

## Security verification

Audited, no new vulnerabilities found:

- **Authentication**: HMAC-signed session token (`crypto.createHmac` + `crypto.timingSafeEqual`), httpOnly cookie — unchanged, confirmed sound.
- **Authorization**: every route on `v1Router` (11 services, 8 actions, metrics, health, docs — including every route added since Phase 8) passes through the single `requireMissionControlAuth` mount point (`app.use('/api/v1', requireMissionControlAuth, v1Router)`) — structurally impossible for a new route to bypass it by omission.
- **Secret handling**: confirmed via grep — every secret (`GROQ_KEY`, `MISSION_CONTROL_PASSWORD`, `N8N_PRODUCTION_WEBHOOK_URL`, `GUMROAD_ACCESS_TOKEN`) is read only via `process.env`, never hardcoded.
- **Configuration safety**: env-var-gated features (`N8N_PRODUCTION_WEBHOOK_URL`, `FACTORY_LIVE_PUBLISH`) all default to the safe/off state when unset.
- **Log sanitization**: checked every `logServiceCall`/`console.log` call site — none logs `req.body`, a password, or a session token; only `method`/`path`/`status`/`duration`/non-sensitive result fields.
- **Input validation**: action names and job IDs are looked up via `Map.get()` against an allowlist (never `eval`'d or used to build a file path/command); the one user-influenced value written to disk (`pause-production`'s `reason` field) is escaped with `escapeHtml()` everywhere it's rendered; report/log filenames are built only from server-generated timestamps, never from user input (no path-traversal surface).

**Result: a clean bill of health.** No new vulnerability was found or needed fixing this phase.

---

## Phase 14 update (2026-08-08, ADR-204) — Production Hardening & Autonomous Reliability

A second, later, much larger hardening round, triggered by Phase 13's real reality-test findings (`FAILURE_REGISTER.md`) rather than a general audit. Preserved above verbatim as the real historical record of the 2026-07-17 round; this section is the current state.

**Real code fixes made this round** (each with regression tests, see `channels/paddle_publisher.py`/`product_master_catalog.py`/`channels/ledger.py`):
- F6 (P2): Paddle API calls now retry a real 429/503 with a `Retry-After`-aware delay, mirroring the Groq fix from 2026-08-06. Previously, a 429 was treated as an immediate, never-retried failure.
- F8 (P3): a malformed JSON response from Paddle used to raise a raw, unwrapped `ValueError` at the publisher layer; now every call site raises a clear `RuntimeError` via a shared `_safe_json()` helper.
- F5 (P2): the Product Master Catalog's `description`/`source_files`/`version` fields used to report `"Unknown"` even when real data existed in `books/_generation_log.jsonl`; now cross-referenced correctly.
- F3 (P1): the real, live Paddle product-creation event for the EU AI Act Compliance Toolkit (created outside the standard `distributor.py` path) was never recorded in `data/sales_ledger.jsonl`. `record_publish_attempt()` gained an optional, additive `backfill_reason` kwarg; the one real historical event was backfilled once, tagged `backfilled: true`, with a full disclosed reason — an addition, never a silent correction.

**New this round, not fixed (real, disclosed, deliberately out of scope):**
- F1 (P1): no Paddle sandbox exists anywhere — payment/refund testing remains structurally BLOCKED, not simulated. Not fixable by code (requires a real Paddle sandbox account).
- F2 (P1): no checkout URL exists in this factory's own records for its one real product — generating one requires a live, mutating call on production Paddle, appropriately requiring explicit founder authorization rather than unilateral action.
- F10 (P1): legal-jurisdiction placeholders on the trust pages — a real founder decision, not an engineering task.
- A real, safe, low-cost `restore_from_snapshot()` function is genuinely missing (`BACKUP_AND_RESTORE.md`) — deliberately not built this round to keep a real data-recovery code path as its own focused, reviewed change rather than a rushed addition.

**New real finding, not in the original Phase 13 register**: a real, measured concurrency test this round (10 simultaneous requests to `GET /api/v1/health`) took ~2.4s total wall time versus ~0.22s for a single request — suggesting the server processes concurrent requests closer to sequentially than in parallel, at least for this route. Not investigated further this round (see `PRODUCTION_READINESS_REPORT.md`'s Performance section) — flagged as a real, disclosed observation, not a diagnosed root cause.

See `RELIABILITY_ARCHITECTURE.md`, `SECURITY_HARDENING_REPORT.md`, `AI_RELIABILITY_REPORT.md`, `OBSERVABILITY.md`, `BACKUP_AND_RESTORE.md`, `DISASTER_RECOVERY.md`, `ROLLBACK_PROCEDURE.md` for the full Phase 14 body of work.
