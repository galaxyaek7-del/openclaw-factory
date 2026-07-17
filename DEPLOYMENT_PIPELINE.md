# Deployment Pipeline

**Date:** 2026-07-17
**Directive:** "Executive Directive — Phase 10C: Operations Automation & CI/CD Pipeline," objective 2 (deliverable 2)

---

## Why this is a 3-stage pipeline, not the usual 3 environments

This factory runs as **one real, local environment** (`CLAUDE.md`: "everything local, no cloud") — there is no separate hosted staging or production server to promote code between. Building literal separate cloud environments would contradict that explicit architecture. This pipeline is the honest local equivalent: three real gates, using the one real environment that exists.

```
Development (your working copy)
     │
     ▼  git push
───────────────────────────────────────
 CI — GitHub Actions (.github/workflows/ci.yml)
 Real, runs on GitHub's own runners. Architecture integrity, security
 check, Python/JS/Factory Loop/API contract tests, performance smoke
 check. No merge should happen unless every job passes.
───────────────────────────────────────
     │  all green
     ▼
Staging simulation — scripts/staging_simulate.js (run locally, by you)
 Full regression + a real server booted on an isolated port (3198) +
 smoke test (auth, all 11 services, aggregate health, Mission Control
 page) + clean teardown. Never touches the real running instance.
───────────────────────────────────────
     │  staging passed
     ▼
"Production" — your real, single, local server.js / factory_loop.js
 scripts/deploy_production.js exists, tested (dry-run mode), ready.
 NEVER auto-invoked by CI, by staging, or by an AI agent on its own —
 requires --confirm, and requires a human to have explicitly decided
 this is the moment to deploy. Dry-run mode (no flag) is always safe to
 run and shows exactly what would happen without changing anything.
```

## Stage 1 — CI (real, automated)

Runs automatically on every push/PR to `main`. See `.github/workflows/ci.yml`. Fails the build (blocking merge) if any job fails:
architecture integrity (syntax checks), a security check (`.env` must never be tracked), Python tests, JS tests (includes Dashboard tests), Factory Loop tests, API contract tests, and a lightweight performance smoke check.

## Stage 2 — Staging simulation (real, but locally-invoked, not auto-scheduled)

`node scripts/staging_simulate.js` — the exact manual verification pattern used throughout this project's own development sessions, formalized into one reusable command. Real regression, a real server on a real (isolated) port, real smoke tests, real teardown. Not wired into CI (a design choice, not an oversight — CI already validates the code; this validates the *running system* on this machine specifically, which is a distinct, deliberately human-invoked check).

## Stage 3 — Production deploy (real script, never auto-invoked)

`node scripts/deploy_production.js` (dry run) / `node scripts/deploy_production.js --confirm` (live). Uses the exact safe-restart pattern `ADR-045` already established: stop the *exact* PID holding port 3000, never a broad `taskkill /IM node.exe` (which would kill every other unrelated Node process on the machine, including this session's own background automation). `factory_loop.js` is never auto-restarted by this script — starting it is always its own separate, deliberate action, consistent with this factory's "no scheduler" principle.

**This script was tested only in dry-run mode during this phase's work** — it correctly identified the real running server (PID) without touching it. It has never been run with `--confirm` by an AI agent, and should not be, without you explicitly deciding in the moment that this is the right time to restart the real running factory.

## Rollback

`node scripts/rollback_simulate.js <git-ref>` — proves a prior commit would still pass its own regression suite, using `git worktree add` (additive, creates a separate temp checkout) rather than `git checkout`/`git reset` (which would mutate the real working directory). The real repository state is never touched; the worktree is always removed, success or failure. A real rollback of the live production instance would follow the same `deploy_production.js --confirm` procedure, pointed at the target ref instead of `main`'s latest — same rule: only ever run by explicit human decision.
