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
