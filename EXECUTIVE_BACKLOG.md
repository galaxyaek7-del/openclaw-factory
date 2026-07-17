# Executive Priority Queue

**Started:** 2026-07-17 (as `EXECUTIVE_BACKLOG.md`; reformatted into a scored, living priority queue under Strategic Autonomy)
**Convention:** every item here was found via direct verification (not speculation), each scored on Value / Effort / Risk / Reversibility so priority is comparable across items, not just listed. Items move to "Done" (with the commit that closed them) rather than being deleted — this is a decision record, not a todo list. Founder-only items are marked explicitly and are never auto-executed, regardless of how they'd score.

---

## Standing note on overall priority

Per the Business Activation directive: **no item in this queue outranks business activation itself.** `ACTIVATION_PLAN.md`'s remaining blocker — a real `GUMROAD_ACCESS_TOKEN` — is still the highest-value work available, and it is not engineering work I can do unilaterally (`MISSION_CONTROL_PASSWORD` and the production redeploy were resolved this session — see Done). This queue exists for the real engineering work that remains genuinely useful while that's pending, not instead of it.

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

## Enterprise Gap Analysis findings (2026-07-17 — see `ENTERPRISE_GAP_ANALYSIS.md`; all 4 audit slices complete)

**Top pick for next session — highest value-to-effort ratio found this cycle:**

| Item | Value | Effort | Risk | Reversibility |
|---|---|---|---|---|
| **Fix CI: `.github/workflows/ci.yml` hardcodes 5 JS test files; the other 13 of 18 (`test_factory_loop_lock.js`, `test_factory_loop_notification.js`, `test_deploy_production.js`, `test_ops_maintenance.js`, `test_pending_review.js`, `test_recovery_log.js`, and 7 more) never run in CI** — verified all 13 pass locally (60/60), so this is a blind spot, not a hidden failure. Replace the hardcoded list with `node --test tests/*.js`; add a real `"scripts"` block to `package.json` (currently has none) so `npm test` runs Python+JS together in one command. | High — every "tests pass" claim made this entire session was only ever checking 28% of the JS suite | Small | None (additive) | Fully reversible |

Highest-value, lowest-risk next picks after that — all Small effort, pure additive/corrective, no founder decision needed:

| Item | Value | Effort | Risk | Reversibility |
|---|---|---|---|---|
| **Reconcile `pollSales()`'s real sales into `finance_data.json`**, not just `data/sales_ledger.jsonl` | High — today invisible only because there have been zero real sales; will silently misreport the company's first real dollar the moment M2 (a live channel credential) resolves | Small | Low (additive, reuse `channels/ledger.py`'s dedup key) | Fully reversible |
| Add an internal shared-secret header (`X-Internal-Token`) so `factory_loop.js`'s calls to `/generate-book`, `/api/distribute`, `/api/scout/run`, and 5 other currently-unauthenticated routes can finally be gated | High (closes the largest concrete, non-founder-gated security gap) | Small | Low (additive; loopback bind is a real compensating control today) | Fully reversible |
| Write the `factory_loop.js` restart runbook into `OPERATIONS_DOCUMENTATION.md` — this session manually killed/restarted it twice by re-deriving the lock-file logic live in chat; that procedure exists nowhere in writing, and it's the sole point of failure for the only live automation | High (real SPOF, zero written recovery procedure today) | Small | None (docs only) | Fully reversible |
| Direct unit tests for `inspectors.py` and `safety_filter.py` first — the two real gates between "AI draft" and "published product" / "unsafe niche blocked" currently have zero direct test coverage (only indirect pass-through via `test_book_generator*`) | High (these two carry real legal/reputational/financial exposure if a regression slips through) | Medium per module | None (additive) | Fully reversible |
| Extend `ops_maintenance.js`'s rotation to `data/*.jsonl` — `orchestrator_timeline.jsonl` (23MB) and `decisions.jsonl` (10.8MB) are already past the 10MB threshold applied to the 3 logs that do rotate; found independently by two separate audit angles this cycle (Security/Reliability fork and Observability fork), which is itself corroborating signal | Medium (real, compounding, currently masked by being "only" a latency cost) | Small (rotation) + Medium (tail-read path without breaking full-history callers) | Low | Fully reversible |
| Fix stale governance docs found this cycle: CLAUDE.md's `/chat` warning (endpoint was auth-gated in `63f7af8`, doc never updated — wrong line number too), `FACTORY_STATUS.md` frozen since 2026-07-09 (add a superseded-by pointer to `CAPABILITY_MAP.md`/`COMPANY_OPERATING_MODEL.md`, don't try to catch it up day-by-day) | Medium (trust/onboarding cost, zero code risk) | Small each | None | Fully reversible |
| Generate `OpenClaw_Brain/00_Governance/ADR_INDEX.md` (74 ADRs, currently no working index — `MASTER_INDEX.md` doesn't cover the ADR-05x/06x series) — script-generated off filenames + each file's own status line, not hand-maintained, so it can't drift the way a hand-written index would | Medium (real onboarding-cost gap) | Small-Medium | Low | Fully reversible |
| Cross-reference `IDENTITY_ARCHITECTURE.md` §6's still-open SPOF mitigations (2FA unknown, no recovery plan, no account backup — undated since 2026-07-11) into this Founder-only tier, so they surface where founder-facing items are actually tracked instead of only in a standalone doc nothing re-visits | Medium (visibility only, not new scope) | Small | None | Fully reversible |
| Document the reboot-survival gap in `OPERATIONS_DOCUMENTATION.md` as an accepted, deliberate limitation (no scheduler exists by design, per `CLAUDE.md` — but the consequence, "a reboot silently stops the whole company with no alert," was never stated outright) | Medium (turns a silent surprise into an accepted, written tradeoff) | Small | None | Fully reversible |
| Add a pre-risky-operation backup step (`scripts/ops_maintenance.js`) copying `finance_data.json`/`golden_opportunities.json` to a timestamped `data/backups/` dir — today's only real safety net for these two files is `git` history, which works but was never an intentional mechanism | Medium | Small | None | Fully reversible |

Real but latent (activate under a specific future trigger, not urgent today):

Real but latent (activate under a specific future trigger, not urgent today):

| Item | Value | Effort | Trigger |
|---|---|---|---|
| Parallelize `factory_loop.js`'s sequential tick steps (worst-case ~490s against a 600s interval, by the code's own comment) | Medium | Medium | Becomes real the moment `FACTORY_AUTO_PRODUCE`/`FACTORY_LIVE_PUBLISH` are turned on |
| Extend `scripts/ops_maintenance.js` rotation to `data/*.jsonl` (`orchestrator_timeline.jsonl` 23MB, `decisions.jsonl` 10.8MB today, unbounded growth, unlike the 3 plain-text logs that already rotate) | Medium | Small (rotation) + Medium (tail-read path without breaking full-history callers) | Grows every session; worth doing before it becomes a real latency problem, not urgent this week |
| Extract a literal `book_engine/` module so CLAUDE.md's 3-layer Core/Engines/Channels model is real, not aspirational | Low today | Medium | Whenever CLAUDE.md's own golden rule (first real dollar) unlocks Path #2 |

Already known, correctly blocked on the founder (no new engineering possible until unblocked — unchanged from before this cycle): n8n's production-notify workflow import + UI activation, a real remote (Gmail) notification channel beyond the desktop toast.

---

## Done

- ~~`self_awareness.js`'s self-referential HTTP call + `readDecisionQueueSummary()`'s uncached 10.8MB re-parse~~ — fixed in `bc11471` (measured ~85-90% latency reduction on `GET /api/dashboard`).
- ~~Extract the duplicated safe-output-path logic (`book_generator.py` vs `cover_designer_v2.py`) into one shared `path_safety.py` module~~ — `c918530`. 10 new tests, real end-to-end cover-generation smoke test run.
- ~~Extend `scripts/ops_maintenance.js`'s log rotation to `factory_loop.log`/`inspections.log`~~ — `40116f2`. 4 new tests.
- ~~Document the Unsplash stock-image license basis in `book_generator.py`~~ — `c918530`.
- ~~Write retroactive ADRs for the last 3 real architectural/operational decisions~~ — `9fb3b38`. `ADR-062`/`063`/`064`.
- ~~JSONL-read duplication: Level 1 (extract) + Level 2 (prevent recurrence)~~ — `f8815c6` + `4436df2`. New `lib/jsonl.js`, 2 real sites migrated, `scripts/check_jsonl_duplication.js` in CI, documented in `CLAUDE.md`.
- ~~`opportunity_gap` double-inversion bug (`analyze_opportunity()` passing `competition_favorability` where `compute_opportunity_gap()` expects raw intensity)~~ — `7fd18c0`. Verified against all 1,344 real historical decisions (zero mismatches on the buggy formula, 94% would clear BUILD's threshold on the corrected one). **Correction (2026-07-17, Mission 001 — this line previously overstated the fix's real reach, kept visible per this doc's own convention rather than silently edited):** `factory_loop.js`'s live path calls `profit_oracle.opportunity_score()` directly and never touches `market_intelligence_engine.py`, where this fix lives — it does not affect why the live system has never accepted a decision. That real cause is `CAPABILITY_MAP.md`'s M1 (no real evidence source fits this product category), corroborated again on 2026-07-17 by the `ADR-028`/`tier1_intake`/`ADR-035`/`ADR-038` trail. This fix remains real and correct for the dormant richer path (`market_intelligence_engine.py`/orchestrator) — just not the live one.
- ~~`MISSION_CONTROL_PASSWORD` activated + production redeployed with every accumulated fix~~ — real, live `--confirm` deploy run twice this session. Verified directly against the running server: loopback-only binding, `/finance/add`/`/chat` now require auth, real login + authenticated `/api/v1/docs` call succeeded end-to-end.
- ~~`deploy_production.js` pre-flight syntax check before touching the live server~~ — `0e2cb44`. Found by reflecting on this session's own two real deploys: the script killed the existing server before checking anything about the new code. `checkServerSyntax()` now gates that. Does not solve the full rollback question (still Near Future/founder-scoped below) — closes the cheapest, most likely real failure mode only.
