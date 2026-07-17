# Executive Backlog

**Started:** 2026-07-17
**Convention:** every item here was found via direct verification (not speculation) during a prior audit or fix pass. Classified per the Executive Continuous Improvement Directive's three tiers. Items move to "Done" (with the commit that closed them) rather than being deleted, so this stays a real decision record, not just a todo list.

---

## Immediate — all 4 implemented this pass (see "Done" below for commits)

## Near Future (real value, larger blast radius — deliberately not rushed)

| Item | Why Near Future, not Immediate |
|---|---|
| Migrate the remaining ~9 JSONL-read call sites (`factory_loop.js` x6, `lib/dashboard_data.js`'s 2 not-yet-migrated functions, `self_awareness.js` x3) to `lib/jsonl.js`'s `readJsonlEntries()`, now that it exists | The shared primitive and its permanent CI safeguard (`scripts/check_jsonl_duplication.js`) are done — this is now a safe, mechanical, low-risk follow-up (no design questions left), just individually verifying each of the ~9 remaining call sites against its own existing tests. Deliberately not rushed into the same pass that built the primitive itself. |
| Reduce `server.js` (2,600+ lines) and `factory_loop.js` (1,550+ lines) — both mix multiple concerns (routing, business logic, subprocess orchestration, healing/hunting/scheduling) | Real maintainability cost, but splitting either file is a structural change with a large diff surface and real risk of subtle import/scope breakage. Not "isolated and reversible" in the sense this directive requires — needs a deliberate design pass (what the module boundaries should be) before any code moves. |

## Long Term (needs a founder decision, not an engineering-only call)

| Item | Why this needs the founder, not a unilateral fix |
|---|---|
| Retrofit real authentication onto the remaining unauthenticated-but-internally-depended-upon legacy routes (`/generate-book`, `/api/distribute`, `/api/scout/run`, `/api/agent/:name`) | These routes are called both by the UI (no session) and internally by `factory_loop.js` over plain `http://localhost` with no credential. Gating them with Mission Control's cookie auth would break the automated pipeline; the real fix requires either giving `factory_loop.js` its own credential or a different auth strategy — a genuine architecture decision (see `ZERO_ASSUMPTION_PRODUCTION_AUDIT.md` Section E), not a quick patch, and risky to make unilaterally on a system whose "no scheduler / everything local" architecture is itself a deliberate, documented founder decision (`CLAUDE.md`). |
| Two parallel, inconsistent automation paths exist (`factory_loop.js`'s Golden Hunter Bridge, which actually runs; `orchestrator.run_cycle()`, which is more architecturally complete but never auto-triggered) | Real architectural inconsistency, but consolidating them is a business-logic decision (which path is the source of truth going forward) as much as an engineering one — not something to resolve as a side effect of an unrelated task. |
| The 20 real Immediate/Near-Future items above still leave `MISSION_CONTROL_PASSWORD`/channel credentials/`FACTORY_AUTO_PRODUCE`/`FACTORY_LIVE_PUBLISH` unset | Standing configuration decision from every prior phase — not an engineering task at all. |

---

## Done

- ~~`self_awareness.js`'s self-referential HTTP call + `readDecisionQueueSummary()`'s uncached 10.8MB re-parse~~ — fixed in `bc11471` (measured ~85-90% latency reduction on `GET /api/dashboard`).
- ~~Extract the duplicated safe-output-path logic (`book_generator.py` vs `cover_designer_v2.py`) into one shared `path_safety.py` module~~ — real, previously-undocumented behavior gap closed as a side effect (`cover_designer_v2.py` now sanitizes an explicit `output` filename the same way `book_generator.py` always did; the one real caller never passes `output`, so this is unreachable in the live pipeline today). 10 new tests (`tests/test_path_safety.py`), full existing suites re-confirmed passing, real end-to-end cover-generation smoke test run.
- ~~Extend `scripts/ops_maintenance.js`'s log rotation to `factory_loop.log`/`inspections.log`~~ — generalized to one parameterized function shared by all 3 logs. 4 new tests (`tests/test_ops_maintenance.js`).
- ~~Document the Unsplash stock-image license basis in `book_generator.py`~~ — honest disclosure comment added directly above `FOOD_IMAGES`.
- ~~Write retroactive ADRs for the last 3 real architectural/operational decisions~~ — `ADR-062` (recovery-audit-log convention), `ADR-063` (Executive Go-Live Audit methodology), `ADR-064` (red-team fix cycle).
- ~~JSONL-read duplication: Level 1 (extract) + Level 2 (prevent recurrence)~~ — Engineering Evolution Mode pass. New `lib/jsonl.js` (canonical `readJsonlEntries()`), migrated `lib/dashboard_data.js`'s `readJsonlTail` and `lib/recovery_log.js`'s `readRecoveryActions` onto it (the 2 sites verified byte-for-byte identical in behavior). The real Level 2 fix: `scripts/check_jsonl_duplication.js` now runs in CI and fails the build if the pattern's count in any file exceeds `config/jsonl_duplication_baseline.json`'s recorded, already-accepted occurrences — verified live that it both passes cleanly today and genuinely fails on a real injected new occurrence. Documented in `CLAUDE.md` so future work reaches for it before writing a 9th copy. Remaining ~9 call sites moved to Near Future above (safe, mechanical, no design questions left — the primitive and its safeguard already exist).
