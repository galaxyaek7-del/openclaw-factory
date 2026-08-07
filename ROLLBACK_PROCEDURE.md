# Galaxy Forge — Rollback Procedure

**Date:** 2026-08-08 | Phase 14, Section 15/22. This factory has no CI/CD pipeline (`CLAUDE.md`'s own words: "There is no build step, test suite, or linter configured" — a project-wide test runner exists via `unittest`, but there is no automated build/deploy gate). Deployment and rollback are both real, but manual and git-based.

---

## The real, current deployment process

1. Code changes are committed to `main` via `git commit`.
2. `git push origin main` publishes them.
3. The running server picks up changes only on its next restart — `scripts/supervisor.js` supervises `server.js`/`factory_loop.js` but does **not** auto-pull or auto-restart on a new commit; a human (or Claude, on request) manually kills the supervised child process, and the supervisor respawns it running the new code (confirmed, this exact mechanism, live, multiple times this session).
4. No automated pre-deployment validation, migration step, or post-deployment smoke test currently runs — verification is manual (`node -c`, `python -m py_compile`/`ast.parse`, and running the relevant test suite), a discipline this session has followed consistently but that is not itself enforced by tooling.

## Rollback path

| Requirement | Real status |
|---|---|
| Previous version available | **YES** — every change is a real git commit; `git revert`/`git checkout <prior-commit>` recovers any prior state |
| Database compatibility | NOT APPLICABLE — no database, no schema to be incompatible |
| Configuration compatibility | **PARTIAL** — `.env` variables are additive by convention (new optional vars, old code paths unchanged) throughout this factory's real history; no case was found this round of a rollback requiring a corresponding config rollback |
| Asset compatibility | **YES** for code; data files (`decisions.jsonl` etc.) are append-only, so rolling back code never invalidates already-written data |
| Rollback procedure | Manual: `git revert <commit>` (preferred, preserves history) or `git checkout <prior-commit> -- <files>`, then restart the supervised process the same way a forward deployment does |
| Rollback tested | **Not tested this round** — git-based rollback of code is a well-understood, low-risk mechanism (git itself is the tested component), but no live "commit, then roll it back, then verify the running server reflects the rollback" drill has been performed in this factory's history |

## Real gap and recommendation

The one genuine, disclosed gap: **no automated post-deployment verification exists.** A deployment "succeeds" today when the process restarts without a crash-loop alert — there is no automated smoke test confirming the *specific* new functionality actually works post-restart (this session's own discipline of manually curl-testing new routes after every restart is a human practice, not enforced by code). Given $0 real revenue and a single founder/AI-pair deploying, building a full smoke-test harness now would be premature relative to real need — but it is the correct next automation candidate if deployment frequency or team size ever grows.

**Do not deploy changes that cannot be safely reversed unless explicitly approved** (the directive's own words) is already this session's standing practice — every real, higher-risk action this session (financial-adjacent, e.g. the F3 ledger backfill) has been append-only and explicitly disclosed, never a blind overwrite.

---

*See also: `DISASTER_RECOVERY.md`, `RELIABILITY_ARCHITECTURE.md`.*
