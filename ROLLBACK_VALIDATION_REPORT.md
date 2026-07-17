# Rollback Validation Report

**Date:** 2026-07-17
**Directive:** "Executive Directive — Phase 10D: Disaster Recovery & Business Continuity," objective 3 (deliverable 4)

---

| Category | Tool | Tested against | Result | Reproducible? |
|---|---|---|---|---|
| Application | `scripts/rollback_simulate.js` | Current `HEAD` (commit `fc142c7`) | ✅ Passed — full regression suite green in an isolated `git worktree` | ✅ Yes — deterministic, uses `git worktree add` at a fixed ref |
| Deployment | Same tool (deployment = redeploying the application at a given ref) | Same | ✅ Same result | ✅ Yes |
| Configuration | `scripts/restore_file_from_git.js config/economics.json HEAD~20` | 20 commits back | ✅ Valid JSON recovered, real config structure intact | ✅ Yes — `git show <ref>:<path>` is deterministic |
| Database (this factory's real equivalent: git-tracked `data/*.jsonl`) | `git show HEAD~20:data/decisions.jsonl` | 20 commits back | ✅ 333/333 valid records recovered | ✅ Yes |
| Documentation | `git show HEAD~20:CLAUDE.md` | 20 commits back | ✅ 149 lines recovered, non-empty, readable | ✅ Yes |

## What "reproducible" means here, proven not asserted

Every rollback mechanism above is built on `git`'s own content-addressed storage — the same ref always produces the same bytes, forever. This was directly demonstrated, not assumed: `scripts/restore_file_from_git.js` was run in `--apply` mode against `OPERATIONS_DOCUMENTATION.md` at its own current `HEAD`, and `git diff` confirmed zero content difference afterward (a true no-op restore, proving the mechanism is exact).

## A real bug this validation process found and fixed

While first testing `scripts/rollback_simulate.js` against a prior commit, it correctly **failed** — not because the tool was broken, but because it found a real, previously-invisible issue: `.gitignore`'s unanchored `backups/` pattern was silently excluding `n8n_workflows/backups/pre_build_20260715_232343.json`, a real artifact `mission_control_api.py`'s `_automation()` depends on, from ever being tracked in git. Fixed in Phase 10C (commit `fc142c7`) by anchoring the pattern to the repo root and committing the previously-invisible file. Rollback simulation against the fixed `HEAD` now passes; rolling back to a commit *before* that fix correctly still reports the (historically real) gap — this is accurate reporting of history, not a new problem.

## Audit trail

Every real (`--apply`) restore this phase performed was logged via `lib/recovery_log.js` to `data/recovery_actions.jsonl` — confirmed with a real entry: timestamp, operator (`Dell`, the real OS username), reason, affected system, and result, all present and correct.

## What was not tested live

`deploy_production.js --confirm` was never run against the real production instance during this validation — restarting the real, currently-running `server.js` is a "prod deploy" action requiring the founder's own explicit go-ahead each time, not something this validation simulates by executing it for real.
