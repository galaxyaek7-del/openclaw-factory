# ADR-097 — Health Monitor & Real-Time Crash Alerting (Roadmap 1.2)

**Date:** 2026-07-23
**Status:** Adopted. Closes Phase 1's last Critical blocker (`ENTERPRISE_UPGRADE_ROADMAP.md` finding 1.2), resumed after the Enterprise Security & Cyber Defense Mission's Phase 1 (audit) landed, as the roadmap's own pause note said it would.

---

## The finding

"No uptime monitoring or general-failure alerting — MTTD is unbounded" (Critical, Phase 1 — the same phase whose own selection logic states these are "prerequisites to trusting any later phase's work"). This was the highest-severity unclaimed, unblocked item left in the roadmap once the Live Competitive Intelligence mission closed (ADR-096) — every other Critical-severity finding still open (Phase 5/6/7) is explicitly gated on real load, a real first sale, or team growth, none of which can be closed by writing code today.

## What a real search found

- `scripts/supervisor.js` (1.1, `96ee731`) already detects crashes and restarts, but only ever alerts via Telegram on `alertGivingUp()` — a single real crash that gets successfully restarted was, until this ADR, completely silent.
- `lib/health_checks.js` (4.7, `f050414`) already computes a real, honest `{status, checks}` report (`buildHealthReport()`), surfaced at `GET /health`/`GET /api/v1/health` — but purely on-demand. Nothing ever reads it proactively.
- `lib/telegram_direct.js` (ADR-085) already sends real Telegram messages and is already wired to `server.js`'s crash handlers and `supervisor.js`'s give-up path.
- `process.uptime()` is already exposed via `GET /health` and the Prometheus `openclaw_uptime_seconds` gauge (`lib/metrics.js`) — no further uptime-tracking work needed.
- No scheduler exists anywhere in the repo (`scripts/ops_daily_checks.js`'s own docstring confirms it: "never wired to run on a schedule... a standalone tool for a human to run when they want a snapshot").

The real gap was narrow and precisely two things: (1) `supervisor.js`'s silent single-crash gap, and (2) nothing ever proactively reads `buildHealthReport()` and alerts on a bad result — the pieces (health checks, Telegram, uptime) all already existed but nothing connected them.

## What was built

**`scripts/supervisor.js`:** new `alertCrashRestart(code, signal, restartCount)`, called on every real crash immediately (before the crash-loop-guard check), not just when the supervisor eventually gives up. Naturally bounded by the same `restartTimestamps`/`MAX_RESTARTS`/`WINDOW_MS` crash-loop guard that already existed — this can never alert more than `MAX_RESTARTS` times per real crash-loop episode.

**`scripts/health_monitor.js` (new):** an opt-in, explicitly-started, long-running foreground process — the exact same honest pattern `supervisor.js` already established, run alongside it with `node scripts/health_monitor.js`. Polls the real, already-live `GET /health` endpoint on a real interval (default 5 minutes, `HEALTH_MONITOR_INTERVAL_MS`-overridable) and alerts via Telegram **only on a real status transition** (healthy → degraded/critical/unreachable, or back to healthy) — never repeatedly for an unchanged status, the same "no alert spam" discipline this session's Live Competitive Intelligence work already established for market alerts (ADR-095) and decision reopens (ADR-096). A real network failure reaching `/health` at all is itself treated as an honest `unreachable` status, not silently swallowed.

Every pure function (`shouldAlert`, `extractFailingCheckNames`, `buildStatusChangeMessage`, `fetchHealth`, `tick`) takes dependency-injected `fetchImpl`/`alertImpl` parameters — the exact same testability shape `lib/health_checks.js`'s own `run`/`fetchImpl` parameters already established, so the whole module is unit-testable with zero live network calls and no real running server.

## What this is not

No scheduler was added to this factory (CLAUDE.md's own architecture fact stays true). `health_monitor.js` is a real process a human explicitly starts and leaves running in a terminal/service, identical in spirit to `supervisor.js` — not a cron job, not a hidden background worker, not a claim of continuous automated operation this factory doesn't actually have.

## Verification

23 new tests: `tests/test_health_monitor.js` (new, 15 tests — `shouldAlert`'s no-alert-on-first-poll and no-alert-on-unchanged-status rules, `extractFailingCheckNames`, `buildStatusChangeMessage`, `fetchHealth`'s honest-unreachable-on-failure behavior, `tick`'s real transition/no-spam/recovery behavior), `tests/test_supervisor.js` (+1 — `alertCrashRestart` sends a real, immediate, correctly-worded alert, verified by mocking `global.fetch` the same way `tests/test_telegram_direct.js`'s own suite already does). Full JS suite: 249/249 real tests green (up from 233; the 2 known non-test glob artifacts unchanged), full Python suite unaffected and reconfirmed green (1141/1141, this piece is JS-only).

## What's next

Phase 1 (Critical blockers) is now fully closed. The Security Mission Tracker's own stated next step (2.7 XSS fix, 2.9 shell-escaping fix) remains the next-highest-severity unblocked item in the roadmap.
