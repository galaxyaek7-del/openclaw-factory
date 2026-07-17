# Operations Documentation

**Date:** 2026-07-17
**Directive:** "Executive Directive — Phase 10C: Operations Automation & CI/CD Pipeline" (deliverable 4)

---

This is the index of every operational tool this phase built, what each does, and when to run it.

## Day-to-day

| Command | What it does | When to run it |
|---|---|---|
| `node scripts/ops_daily_checks.js` | Real-time snapshot: server availability, background automation recency, decision history integrity, knowledge sync, git backup status, storage usage | Whenever you want a real health snapshot — not scheduled by design |
| `node scripts/ops_maintenance.js` | Reports whether logs need rotating or old reports need cleanup (dry run by default) | Occasionally, or when `logs/` or `reports/` feels large |
| `node scripts/ops_maintenance.js --apply` | Actually rotates logs / deletes old reports beyond retention | Only after reviewing the dry-run output |
| `node scripts/generate_release_notes.js [range]` | Real release notes, build version, change summary, migration notes from `git log` | Before/after a significant batch of commits |

## Before merging a change

| Command | What it does |
|---|---|
| CI (automatic on push/PR) | `.github/workflows/ci.yml` — see `CI_PIPELINE.md` |
| `node scripts/staging_simulate.js` | Local staging gate — full regression + a real smoke-tested server on an isolated port | 

## Before/around a production deploy

| Command | What it does | Safety |
|---|---|---|
| `node scripts/deploy_production.js` | Shows exactly what a deploy would do, changes nothing | Always safe |
| `node scripts/deploy_production.js --confirm` | Actually stops the exact PID on port 3000 and restarts `server.js` with current code | **Only run when a human has explicitly decided this is the moment** |
| `node scripts/rollback_simulate.js <ref>` | Proves a prior commit would pass its own regression suite, using an isolated `git worktree` — never touches the real branch/working directory | Always safe |

## What "operational" means for this factory specifically

This factory runs as one real local environment, not a fleet — every tool above was built around that fact rather than pretending otherwise. "Monitoring" means checking the one real instance's real state; "deployment" means restarting one real process with new code, safely, only when a human says so; "rollback" means proving an older commit still works, without ever touching what's currently running.

## Known, disclosed limitation

`ops_daily_checks.js`'s server-availability check just found that the real server has been stale for 2+ days (see `AUTOMATION_REPORT.md`) — this documentation describes the tools as built and tested; it does not claim the real running instance currently reflects any of them until a deploy actually happens.
