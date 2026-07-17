# Executive Priority Queue

**Started:** 2026-07-17 (as `EXECUTIVE_BACKLOG.md`; reformatted into a scored, living priority queue under Strategic Autonomy)
**Convention:** every item here was found via direct verification (not speculation), each scored on Value / Effort / Risk / Reversibility so priority is comparable across items, not just listed. Items move to "Done" (with the commit that closed them) rather than being deleted — this is a decision record, not a todo list. Founder-only items are marked explicitly and are never auto-executed, regardless of how they'd score.

---

## Standing note on overall priority

Per the Business Activation directive: **no item in this queue outranks business activation itself.** Every item below is real, verified engineering value — but `ACTIVATION_PLAN.md`'s blockers (credentials, `MISSION_CONTROL_PASSWORD`, the automation switches) are the actual highest-value work available, and none of it is engineering work I can do unilaterally. This queue exists for the real engineering work that remains genuinely useful alongside that, not instead of it.

## Founder-only (cannot be safely delegated — flagged, not implemented)

| Item | Value | Effort | Risk | Reversibility | Why founder-only |
|---|---|---|---|---|---|
| Decide `pain_score`'s evidence source | High — directly gates whether `BUILD` can ever fire, even after the `opportunity_gap` fix (`7fd18c0`) | Medium-large (real design work, not a patch) | Low technical risk, real business-strategy risk (changes what counts as validated demand) | Hard to reverse cleanly once niches start being accepted/rejected under a new definition | Real customer-pain evidence currently comes from GitHub Issues/HN — the wrong source for this factory's actual products (journals, planners, cookbooks). Verified: only 75/1,344 real decisions have any `pain_score` at all; 2 ever reached the 50 threshold. Fixing this means deciding what "validated demand" should mean for this specific business — not an engineering call. |
| Retrofit real authentication onto `/generate-book`, `/api/distribute`, `/api/scout/run`, `/api/agent/:name` | High (closes the largest remaining security gap) | Medium (mechanical once the approach is chosen) | Breaks the automated pipeline if done wrong (these are called internally by `factory_loop.js` with no session) | Reversible, but the wrong approach could cause a real outage | Requires deciding whether `factory_loop.js` gets its own credential or a different auth strategy — an architecture decision, not a patch (`ZERO_ASSUMPTION_PRODUCTION_AUDIT.md` Section E) |
| Consolidate or formally deprecate the second automation path (`orchestrator.run_cycle()`, architecturally complete but never auto-triggered, vs. `factory_loop.js`'s Golden Hunter Bridge, which actually runs) | Medium (reduces confusion for future engineers) | Medium | Low if done as documentation-only; higher if code is removed | Reversible if scoped to docs first | Which path is the long-term source of truth is a business/roadmap decision, not something to resolve as a side effect |

## Near Future (real value, larger blast radius — deliberately not rushed)

| Item | Value | Effort | Risk | Reversibility |
|---|---|---|---|---|
| Migrate the remaining ~9 JSONL-read call sites (`factory_loop.js` x6, `lib/dashboard_data.js` x2, `self_awareness.js` x3) to `lib/jsonl.js`'s `readJsonlEntries()` | Low-medium (the primitive and its CI safeguard already exist — this is cleanup, not a new capability) | Small per site, ~9 sites to verify individually | Low (each site has existing test coverage to check against) | Fully reversible |
| Reduce `server.js` (2,600+ lines) and `factory_loop.js` (1,550+ lines) — both mix multiple concerns | Medium (real maintainability gain) | Large (genuine design pass needed first) | Medium — large diff surface, real risk of subtle import/scope breakage | Reversible but expensive to redo if the first attempt picks wrong module boundaries |

---

## Done

- ~~`self_awareness.js`'s self-referential HTTP call + `readDecisionQueueSummary()`'s uncached 10.8MB re-parse~~ — fixed in `bc11471` (measured ~85-90% latency reduction on `GET /api/dashboard`).
- ~~Extract the duplicated safe-output-path logic (`book_generator.py` vs `cover_designer_v2.py`) into one shared `path_safety.py` module~~ — `c918530`. 10 new tests, real end-to-end cover-generation smoke test run.
- ~~Extend `scripts/ops_maintenance.js`'s log rotation to `factory_loop.log`/`inspections.log`~~ — `40116f2`. 4 new tests.
- ~~Document the Unsplash stock-image license basis in `book_generator.py`~~ — `c918530`.
- ~~Write retroactive ADRs for the last 3 real architectural/operational decisions~~ — `9fb3b38`. `ADR-062`/`063`/`064`.
- ~~JSONL-read duplication: Level 1 (extract) + Level 2 (prevent recurrence)~~ — `f8815c6` + `4436df2`. New `lib/jsonl.js`, 2 real sites migrated, `scripts/check_jsonl_duplication.js` in CI, documented in `CLAUDE.md`.
- ~~`opportunity_gap` double-inversion bug (`analyze_opportunity()` passing `competition_favorability` where `compute_opportunity_gap()` expects raw intensity)~~ — `7fd18c0`. Verified against all 1,344 real historical decisions (zero mismatches on the buggy formula, 94% would clear BUILD's threshold on the corrected one). This is very likely the primary reason no real decision has ever been ACCEPTED — the remaining blocker (`pain_score`'s evidence source) is recorded above as founder-only.
