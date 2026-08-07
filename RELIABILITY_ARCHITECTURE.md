# Galaxy Forge — Reliability Architecture

**Date:** 2026-08-08 | Phase 14, Production Hardening & Autonomous Reliability (ADR-204). Real, evidence-based Single Point of Failure analysis (Section 3) across all 17 named systems, plus file/data integrity (Section 4), queue/worker reliability (Section 8), and autonomous self-healing (Section 9).

---

## Single Point of Failure analysis

| System | Failure Mode | Impact | Detection | Recovery | Backup | Fallback | Human Intervention |
|---|---|---|---|---|---|---|---|
| **Database** | N/A — no database exists (confirmed: `lib/health_checks.js` reports `database: not_applicable`) | N/A | N/A | N/A | N/A | Flat JSON/JSONL files, append-only where it matters | None required — architectural choice, documented |
| **File storage** | Local disk failure/corruption | Total, unrecoverable data loss (no offsite copy exists) | `storage_integrity` check in `computeHealthStatus()` — real per-line JSON/JSONL validation | Manual restore from a `.bak` snapshot if one exists and is recent enough | `recovery/snapshot.py::snapshot_before()` — event-triggered, not scheduled | None | Required if a real restore is ever needed — no automated restore function exists (see `BACKUP_AND_RESTORE.md`) |
| **Product catalog** | `product_master_catalog.py` read failure (missing/corrupt source file) | Catalog view degrades to partial/empty, never crashes (every source read is defensively wrapped) | Real, live-tested this round (10/10 real products returned correctly) | Automatic — a missing file returns an empty list, never raises | Same as File storage (the 3 real source files it reads) | Read-only view; the real per-platform records remain the actual source of truth even if the catalog view itself fails | None for a transient failure |
| **Marketplace adapters** | Credential missing/invalid, platform API down | Only that platform's operations are affected — `BaseArm` never raises past the arm boundary, live-verified with a real invalid-key test in Phase 13 | `ArmStatus`/`health_check()`, real and live | Automatic circuit breaker (`COOLDOWN_THRESHOLD = 3`), no manual reset needed | N/A (stateless credential check) | Other 3 arms unaffected (architecturally proven) — **but only 1 of 4 is actually credentialed today**, a real deployment-level SPOF (`PLATFORM_RELIABILITY_REPORT.md`) | Founder must supply/rotate the credential |
| **Payment integrations** | Paddle account/API outage | 100% of real commercial capability halts (Paddle is the only credentialed platform) | Live `status()`/`health_check()` | None automatic — no second payment provider exists | N/A | None — real, current single point of failure | Founder must resolve with Paddle, or configure a second provider |
| **Webhooks** | N/A — no webhook receiver exists anywhere in this factory | Real consequence: state changes (e.g. a customer-initiated refund) are only discovered on the next poll, not in real time | N/A | N/A | N/A | Polling (`check_payment_status()`) | None required at current (0 real transaction) scale |
| **Authentication** | `MISSION_CONTROL_PASSWORD`/`INTERNAL_SERVICE_TOKEN` — a single shared secret, no per-user accounts | If leaked, full Mission Control access; if lost, founder is locked out | None automated (no login-attempt monitoring) | Founder rotates the env var and restarts | N/A | None | Founder-only, by design (`IDENTITY_ARCHITECTURE.md`'s documented single-Google-account simplicity decision) |
| **AI services** | Groq outage/quota exhaustion | Every AI-generation path (content, market analysis, executive brain) degrades or fails | Real, live network reachability check in `computeHealthStatus()` | Real retry+backoff, `Retry-After`-aware (2026-08-06 fix) | N/A | None — Groq is ~100% of real AI provider usage (`ai_capability/registry.py`, every other provider `DISCOVERY` status only) | None automatic; a sustained outage requires a founder decision to configure a second provider |
| **n8n** | Unreachable/unconfigured | Real, already-limited impact — n8n workflows are documented as not yet activated (`BLOCKERS.md`), so this factory's real automated pipeline does not depend on n8n today | Real reachability check every `factory_loop.js` tick | N/A (nothing currently depends on it completing) | N/A | The equivalent real automation runs directly in `factory_loop.js`/Mission Control actions instead | Founder-only if/when n8n activation is pursued |
| **Background workers** | `factory_loop.js` crashes | The daily tick (evolution queue, reports, resilience monitoring, etc.) stops | Real crash-loop detection | **Automatic** — `scripts/supervisor.js` restarts it, confirmed live this session (real PID respawn observed multiple times) | N/A (stateless process) | None — single process, single supervisor | Only if the crash-loop guard itself trips (too many restarts too fast) — real Telegram alert fires |
| **Schedulers** | N/A — no real cron/scheduler exists except one real Windows Scheduled Task for the weekly report | Loss of the weekly report only | Mission Control's `scheduler-status` panel, live `Get-ScheduledTask` query | Manual re-registration | N/A | Manual trigger via Mission Control | Founder, if it's ever found deregistered |
| **Queues** | N/A — no message queue exists anywhere in this factory (`worker_pool`/`queue_system` both `not_applicable` in `computeHealthStatus()`) | N/A | N/A | N/A | N/A | Direct, synchronous function calls throughout | None required — architectural choice at current scale |
| **Logging** | Local log files fill disk or become corrupted | Reduced observability, not a functional outage | `checkDiskSpace()` (Windows-only, real) | Manual rotation/cleanup — no automated log rotation exists | N/A | N/A | Founder, if disk space becomes a real constraint |
| **Mission Control** | `server.js` crashes | Founder loses the operational cockpit; automated `factory_loop.js` work continues independently | Real crash-loop detection | **Automatic** — `scripts/supervisor.js`, confirmed live this session (respawned during this very test round) | N/A | None needed — recovers automatically | Only on repeated crash-loop |
| **Golden Hunter** | Groq or `multi_source_intelligence` connector outage | Discovery pauses; scoring of already-known candidates still works from cached data | Real, live-tested this round (`golden_hunter_room.py`) | Retries on next tick | N/A | Degrades to stale-but-real cached opportunity data | None automatic |
| **Executive Brain** | Any of its 3 real full-portfolio scans fails/times out | The daily directive isn't generated that day | Real error handling per sub-call (confirmed via code read) | Retries the next daily tick | N/A | Founder can still read the individual underlying reports directly | None automatic |
| **Network dependencies** | Groq/Telegram/GitHub unreachable | Each degrades independently — real, live network checks in `computeHealthStatus()` confirm each is checked separately, never bundled into one pass/fail | Real, per-dependency | Automatic retry where the calling code has it (Groq does; Telegram notifications are fire-and-forget, best-effort) | N/A | N/A | None automatic |
| **External APIs** | Same as above, generalized | Same pattern — every real external call in this factory is wrapped, never left to crash the caller (confirmed throughout Phase 13's failure-injection testing) | Per-integration | Per-integration retry logic (inconsistent — Groq and now Paddle have real `Retry-After` handling; others do not) | N/A | N/A | Varies |

## File and data integrity (Section 4)

**Source of truth for every critical real data store**, verified this round:

| Store | Source of Truth | Backup | Locking/Concurrency | Recovery | Integrity Validation | Migration Recommendation |
|---|---|---|---|---|---|---|
| `data/decisions.jsonl` (2,056 real records) | Itself — append-only | `snapshot_before()`, event-triggered | None explicit — a single Node/Python process writes at a time in practice; no real concurrent-writer collision has ever been observed | Manual restore from `.bak`, real backup content proven valid this round (see `BACKUP_AND_RESTORE.md`) | Real, per-line JSON validation in `computeHealthStatus()`'s `storage_integrity` check | **Do not migrate.** 0 real concurrency incidents ever recorded; append-only JSONL is genuinely safe at this write volume |
| `finance_data.json` | Itself, synced from `data/sales_ledger.jsonl` via `reconcile_ledger_to_finance()` | `snapshot_before()` | Atomic temp-file-then-rename write (confirmed in `channels/ledger.py`) — real, correct pattern that prevents partial-write corruption | Same as above | Same | **Do not migrate.** Atomic-write discipline already provides the real safety a transactional DB would add here |
| `data/paddle_products.json` | The live Paddle account itself (cross-checked exact-match this round) | `snapshot_before()` | No locking; low write frequency (6 real products created over weeks) | Re-derivable from the live Paddle API if ever lost (proven this round: a live `list_products()` call reconstructs the same data) | Live cross-check, performed this round: 6/6 exact match | **Do not migrate.** The live platform is itself the real backup |
| `data/customer_requests.jsonl` | Itself (does not exist yet — 0 real records) | N/A yet | N/A | N/A | N/A | Revisit if/when real customer volume makes concurrent writes plausible |

**Overall recommendation: do not migrate to a transactional database at current scale.** The real trigger conditions for reconsidering (documented, not guessed): (1) a real, observed concurrent-write corruption incident — none has ever occurred; (2) real write volume high enough that append-only JSONL read/scan cost becomes a measured bottleneck — not yet approached (2,056 records reads in well under a second); (3) a real multi-process/multi-server deployment, which does not exist today (single supervised Node process).

## Queue and worker reliability (Section 8)

**No real job queue exists in this factory.** Every "job" today is either a synchronous function call or one of `server.js`'s real async action jobs (`runActionSync`/`runPythonActionAsync`/`runFullCycleActionAsync`, per `PRODUCTION_HARDENING_REPORT.md`'s 2026-07-17 Phase 10B work), each of which already has: a real job ID, `error` field, and bounded timeout (`killAfterTimeout()`). No job silently disappears — confirmed by that same, real, earlier hardening round. What's genuinely absent: attempt count, next-retry-time, and dead-letter handling — none of these exist because none of these async actions currently retry themselves; a failed action reports `failed` once and stops. This is an honest gap, not urgent at current scale (0 real concurrent job volume) but worth closing if job volume ever grows.

## Autonomous self-healing (Section 9)

**Real and already working:**
- Process-level: `scripts/supervisor.js` restarts both `server.js` and `factory_loop.js` on a real crash, confirmed live multiple times this session (including during this very test round).
- API-level: Groq and (as of this round) Paddle both retry transient failures with a real `Retry-After`-aware backoff.
- Publish-level: `PaddleArm.publish()`'s real idempotency check prevents a retry from creating a duplicate product.

**Never allowed to hide the original failure (verified):** `scripts/supervisor.js`'s crash-loop guard sends a real Telegram alert after too many restarts, rather than looping forever silently. `resilience_monitor.py::record_incident()` opens a real, persisted incident record rather than just logging and moving on.

**Genuinely absent:** automatic recovery of an *incomplete* job (since no job queue exists to have an "incomplete" state to resume from), and automatic "rebuild derived analytics" (no derived-analytics cache currently exists that could go stale in a way requiring a rebuild — every report in this factory computes fresh on each call).

---

*See also: `BACKUP_AND_RESTORE.md`, `DISASTER_RECOVERY.md`, `OBSERVABILITY.md`.*
