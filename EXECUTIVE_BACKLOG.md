# Executive Backlog

**Started:** 2026-07-17
**Convention:** every item here was found via direct verification (not speculation) during a prior audit or fix pass. Classified per the Executive Continuous Improvement Directive's three tiers. Items move to "Done" (with the commit that closed them) rather than being deleted, so this stays a real decision record, not just a todo list.

---

## Immediate — all 4 implemented this pass (see "Done" below for commits)

## Near Future (real value, larger blast radius — deliberately not rushed)

| Item | Why Near Future, not Immediate |
|---|---|
| Extract the duplicated JSONL-read-with-corrupt-line-skip loop (hand-written independently in `lib/dashboard_data.js`, `factory_loop.js`, `server.js`, `scripts/ops_daily_checks.js`) into one shared helper | Real duplication, but touches 4+ files with subtly different call patterns (some read the whole file, some tail N lines, some have different corrupt-line handling) — a rushed extraction risks a genuine behavior difference in at least one call site. Deserves its own dedicated pass with full regression coverage of every call site individually, not a same-session bolt-on. |
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
