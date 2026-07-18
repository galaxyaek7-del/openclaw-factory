# Disaster Recovery Plan

**Date:** 2026-07-17
**Directive:** "Executive Directive — Phase 10D: Disaster Recovery & Business Continuity," objectives 1–2 (deliverable 1)

---

## Backup strategy — real, versioned, verified

| Category | Backed up? | Mechanism | Versioned? |
|---|---|---|---|
| Knowledge Base (`OpenClaw_Brain/`) | ✅ Yes | git (100 tracked files), pushed to GitHub | ✅ full git history |
| Decision History (`data/decisions.jsonl`) | ✅ Yes | git-tracked, pushed | ✅ full git history |
| Production Queue | ✅ Effectively yes | Purely derived from Decision History at read time (`production_factory/factory.py` writes nothing to disk) — nothing separate exists to lose | ✅ (inherits Decision History's versioning) |
| Configuration (`config/*.json`) | ✅ Yes | git-tracked (5 files), pushed | ✅ full git history |
| Architecture documents (`CLAUDE.md`, `CONSTITUTION.md`, `OPENCLAW_OS_CONSTITUTION.md`, ADRs) | ✅ Yes | git-tracked, pushed | ✅ full git history |
| Logs (`factory_loop.log`, `inspections.log`, `scout_runs.log`, `market_hunter_runs.log`, `finance_errors.log`, `logs/service_layer.log`) | ❌ **No** | Excluded by `.gitignore`'s `*.log` — standard, deliberate practice (log files aren't meant to bloat a git history), not an oversight | N/A |

**The one real, disclosed gap: logs are local-only.** If this machine's disk were lost, every one of the log files above would be permanently gone — none of them are pushed anywhere. This is consistent with `CLAUDE.md`'s "everything local, no cloud" architecture and is standard practice (committing ever-growing log files to git is normally the wrong call), not something this phase "fixes" by reversing that convention. Mitigation available today: `scripts/ops_maintenance.js` (Phase 10C) rotates `logs/service_layer.log` before it grows unbounded; a founder who wants log history preserved long-term would need their own out-of-band backup of the local machine — a decision outside this factory's own architecture, not something to build into it.

**Real verification performed this phase**: `git fetch origin main` + `git rev-list --count` confirmed 0 commits ahead/behind — every backed-up category above is genuinely, currently pushed to the real remote, not just committed locally.

## Recovery strategy — tested, not just documented

| Scenario | Tested how | Result |
|---|---|---|
| Server crash | Abruptly killed a live throwaway `server.js` (`taskkill /F`, no clean shutdown) mid-action, then restarted it | ✅ Application state (Mission Control, Unified Service Layer, single-writer guard) recovered fully and correctly. ⚠️ **Real gap found**: the spawned Python subprocess survived as an orphan (Windows `taskkill /F` without `/T` doesn't kill children) — see `RECOVERY_TEST_RESULTS.md`. Diagnostic tool built: `scripts/check_orphan_processes.js`. |
| Power failure | Same simulation as server crash (an abrupt kill is the closest safe local proxy for a power failure) | Same result as above |
| Interrupted production | Reviewed `production_factory/factory.py`'s actual code: it only ever reads state and returns an in-memory result — it writes nothing to disk itself. An interruption at any point leaves either a complete result or nothing at all; no partial-dossier state is structurally possible. | ✅ Safe by design, confirmed by code review |
| Corrupted configuration | Replaced `config/economics.json` with invalid JSON, called the real `system_configuration` endpoint and `economics.load_config()` directly | ✅ Both already fail gracefully with a clear, structured error (`EconomicsConfigError` / `{"success": false, "error": "..."}`) — no crash, no corruption of the real file (restored and byte-diffed identical afterward) |
| Interrupted deployment | Reviewed `scripts/deploy_production.js`'s real structure: each step (`git pull`, `npm ci`, stop, start) is wrapped in one try/catch that records a failed recovery action and exits non-zero on any failure, without leaving the old process torn down before confirming the new one can start | ✅ Fails safely — the "stop old server" step only runs after `git pull`/`npm ci` succeed |
| Partial data loss | Truncated a real copy of `data/decisions.jsonl` mid-line (simulating a crash during a write) | ✅ 1343/1344 valid records recovered; the corrupt trailing partial line was skipped gracefully, not fatal |

## Rollback strategy

See `ROLLBACK_VALIDATION_REPORT.md` — application, configuration, deployment, data, and documentation rollback are all tested and reproducible via git (either `scripts/rollback_simulate.js` for application/deployment, or `scripts/restore_file_from_git.js` for a single config/data/doc file).

## Auditability

Every real recovery action (`deploy_production.js --confirm`, `restore_file_from_git.js --apply`) now appends a real, complete record — timestamp, operator (real OS username), reason, affected systems, result — to `data/recovery_actions.jsonl` via `lib/recovery_log.js`. Verified this phase: a real restore produced a real, correctly-populated audit entry.

---

## Unified Recovery System (2026-07-18) — built on top of the above, not a replacement

The founder asked for a single, integrated Recovery System — safe startup detection, an offline retry queue, Telegram founder notifications, publish-idempotency, a Mission Control dashboard, and automatic snapshots — verified together, not as four separate patches. This section records what was actually built, in one pass, all sharing the same spine: `data/factory_state.json` (`factory_state.py`/`lib/factory_state.js`), the single "what's happening right now" view already established by an earlier phase (Phase A).

| Piece | What it is | Where |
|---|---|---|
| **Safe startup detection** | Classifies a reclaimed-stale-lock restart as `HEALTHY` (auto-resume), or `NEEDS_CONFIRMATION` (a duplicate-sensitive stage — production/publishing, or a risky `golden_hunter_tick` step — was in flight with no confirmed success record). Fails closed: an unreadable state always means "confirm first," never "assume fine." | `recovery/startup_check.py`, wired into `factory_loop.js`'s `main()` right after `acquireLock()` |
| **A real, pre-existing bug found and fixed while verifying this** | `process.on('exit', releaseLock)` passed Node's exit CODE as `releaseLock`'s first argument (its `lockFile` parameter), so `fs.unlinkSync(<a number>)` silently failed on **every** exit path, clean or not — the PID lock was never actually being released. This made the whole "detect an unclean shutdown" mechanism meaningless until fixed (now `process.on('exit', () => releaseLock())`). | `factory_loop.js` |
| **Offline retry queue, exponential backoff** | `pending_retries` (Phase A) gained `attempt`/`next_retry_at` (0s, 60s, 120s, 240s..., capped at 1h) and an optional `context` snapshot. Wired at the 3 real network call sites: Groq generation (`book_generator.py`), a real failed arm publish (`distributor.py`), and n8n/Telegram delivery (`lib/n8n_notify.js`). `factory_loop.js`'s tick replays due `telegram_notify:*` entries for real (they carry enough context); `arm_publish`/`groq_generation` entries are counted and reported, not yet auto-replayed (an honest scope limit — full replay needs the original product/generation request captured too, a real follow-up, not guessed at here). | `factory_state.py`/`.js`, `book_generator.py`, `distributor.py`, `lib/n8n_notify.js`, `factory_loop.js`'s `processPendingRetries()` |
| **Telegram integration** | 4 new founder-facing events — `factory_stopped_unexpectedly`, `factory_recovered`, `recovery_completed`, `retry_queue_status` (counts only, fires only when the queue's size actually changes — never spams) — same payload-builder pattern as the existing 2 events, routed through `03_Production_Notify`/`04_Telegram_Notify`'s already-present but previously-unused `event` field. | `lib/n8n_notify.js` |
| **Payment/publish safety** | The real, confirmed duplicate-publish gap — `paddle_arm.py`'s `publish()` had no pre-check before creating a Paddle product — is closed: `production_id` is now embedded as Paddle's own `custom_data` at creation, and `publish()` searches `list_products()` for a match before ever creating a new one. A crash-and-retry now reuses the existing product instead of creating a second one. Revenue recording was already idempotent (`channels/ledger.py`'s `(platform, raw_id)` dedup) — confirmed, not changed. Gumroad has the identical latent risk but is archived/deprioritized (`ADR-065`) — documented, not fixed, consistent with not investing in a deprioritized path. No customer-facing notification system exists yet in this codebase — the requirement is honestly vacuous today, not silently ignored. | `channels/paddle_publisher.py`, `channels/paddle_arm.py` |
| **Recovery Dashboard** | Mission Control gained a `recovery-status` service (`GET /api/v1/recovery-status`, auto-generated route from the existing `SERVICE_REGISTRY`) and a `confirm-safe-to-resume` action (same shape as `pause-production`/`resume-production`, refuses honestly if nothing is actually marked interrupted) — surfacing current task, recovery state, pending retries, last checkpoint, and the last real recovery action, all already-computed, nothing new calculated. | `mission_control_api.py` (`_recovery`/`_resolve_recovery`), `server.js`, `mission_control.html`'s new "الاسترجاع" tab |
| **Automatic backups** | `recovery/snapshot.py`'s `snapshot_before()` generalizes the existing `.corrupt-{ts}.bak` quarantine pattern into a reusable helper — snapshots `factory_state.json`/`production_control.json`/`data/decisions.jsonl` immediately before a real Paddle publish call and before an orchestrator production/publishing stage runs. Best-effort, never blocks the real operation. **Automatic Git commits were deliberately not built** — this conflicts with this session's own standing rule ("never commit unless explicitly asked") and remains gated behind the founder's separate, explicit go-ahead, exactly as flagged when this system was first architected. | `recovery/snapshot.py`, wired into `channels/paddle_arm.py` and `orchestrator/orchestrator.py`'s `_run_stage()` |

**Verified**: the full existing test suite (Python + JS) stayed green throughout every step above — every change was additive to already-passing behavior. A real abrupt-kill-and-restart of `factory_loop.js` mid-`golden_hunter_bridge` step was performed (not simulated): the next startup correctly classified `NEEDS_CONFIRMATION`, wrote `NEEDS_ATTENTION.md`, and recorded real `recovery_info` — the same evidence-based verification discipline `RECOVERY_TEST_RESULTS.md` already established for `server.js`, now extended to `factory_loop.js` specifically.
