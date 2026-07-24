# ADR-124 — Executive Mission Control: CEO Review & Production Polish

**Date:** 2026-07-25
**Status:** Adopted.

---

## The directive

Founder decision: review Mission Control v1 (ADR-123) as a real CEO would. "Do not build any new engines." Nine tasks: launch it locally, verify every panel works, verify every KPI comes from real data, remove anything duplicated, improve visual hierarchy, improve responsiveness, improve loading speed, replace unclear wording, produce a short executive walkthrough. Then answer: is it production-ready, what's still missing before public launch, and the top 10 improvements by priority. "Only polish, validate and prepare for production."

## Method

Launched `server.js` locally, logged into Mission Control, and drove `mission_control_executive_v1.html` in a real browser (screenshots, console, network inspection) rather than reviewing the code alone — the same live-verification discipline this session has used throughout. Every finding below was reproduced against real running data, not inferred from reading the source.

## Real bugs found and fixed (all in `mission_control_executive_v1.html` — zero server.js changes this round)

1. **Investment Pipeline silently dropped 58 real records.** `SECTIONS` declared `listKey:'pipeline'`; the real `get-investment-pipeline` action returns its array under `entries`. The card rendered "No verified data" while its own pill said "Live" — confirmed via direct `curl` against the real job result. Fixed the key; all 58 real scored decisions now render.
2. **Pill/content contradiction, root cause.** `isMeaningfullyEmpty()` judged emptiness from the raw envelope (`success`, `generated_at`, etc.), which is essentially always non-empty — so a `kind:'list'` section with a genuinely empty or missing list still showed a "Live" pill. Made the emptiness check list-aware: for `kind:'list'` sections it now checks the actual `listKey` array, the same array the card body renders.
3. **Knowledge Graph froze the tab for 10-30+ real seconds on every load.** The card `JSON.stringify`'d the full real payload — 2,785 nodes and 2,747 edges — into the DOM in one block. Reproduced live (multiple `CDP Page.captureScreenshot` timeouts against the real page). Fixed with a generic array-preview cap (40 items) applied everywhere a large array is rendered, with an honest "Showing the first 40 of 2,785 real items" note — the full set is still one real API call away, never lost, just not force-rendered.
4. **The mouse wheel got trapped inside cards.** Always-expanded `<pre>` blocks with `max-height` + internal scroll made cards so tall that most of the visible viewport was inside a nested scrollbox — confirmed live: a normal scroll gesture over Company Health scrolled the JSON block, not the page. Replaced with collapsed-by-default `<details>` disclosure for any genuinely large/deep real structure; nothing is hidden permanently, a reader opens what they want to read.

## Visual hierarchy: the flattening rewrite

The original `renderKV()` dumped any nested object as raw JSON, however small (`{"active": false}` got its own JSON block) or however important (Company Health's real `critical` status and its real reason text were both buried three levels deep in an always-collapsed wall of JSON). Rewrote it around one generic transform: `flattenLeaves()` recursively surfaces every real scalar leaf (up to 2 levels deep) as its own clean `path › to › field: value` row, sorted into number stat-tiles, short key facts, and — new, added after the first pass surfaced a real regression — long real prose (e.g. a 1,900-character real "next dollar actions" paragraph) gets its own readable left-aligned block instead of being forced right-aligned into a single grid line. Only genuinely deep/large structures still get the collapsed raw-JSON treatment. Nothing renamed, nothing invented — every value shown is the same real value, just relocated to where a reader can actually see it.

Net effect, confirmed live: Company Health went from "click to expand three separate raw JSON walls" to immediately showing `risk › level: critical`, `reality › verdict: CRITICAL`, `reality › reason: "Zero products published on any channel..."`, and `reality › next action: "Publish one product on any channel. Nothing else matters."` — the real headline fact, visible without a click, matching the founder's own "CEO understands the state of the company in under 30 seconds" goal far better than the original always-collapsed-or-always-dumped design.

One structural fix discovered mid-rewrite: the first version of the flatten only recursed into objects with ≤6 keys, so a real, useful 15-field object (Commercial Intelligence's `latest` snapshot) stayed fully opaque by default even though every one of its 15 fields is a plain scalar. Switched the bound from breadth (key count) to depth (2 levels) — every scalar now surfaces regardless of how many sibling fields it has; only genuine nesting or scale still collapses.

## Wording clarity

- Wired up `.section-note` — a CSS class that existed in the stylesheet but was never actually used by the JS. Every one of the 18 sections now carries a one-line, fact-grounded subtitle (e.g. distinguishing Commercial Intelligence's single-snapshot scope from Market Memory's monthly-trend scope, so the two don't read as duplicates).
- The Scheduler card's most prominent number used to be `32` — the raw Windows Task Scheduler `DaysOfWeek` bitmask, meaningless without decoding. Decoded it into the real day name (`Fri (bitmask 32)`) using Microsoft's own documented, fixed enum — a pure display transform of the same real field, not an invented one.
- Action-backed cards' "Source:" line now says `(async report)` so the transport (a background job, not a plain GET) is honest at a glance.

## Loading speed

- The Knowledge Graph freeze (above) was the single largest real cost; fixing it alone removed the worst-case multi-second main-thread block.
- Action polling backed off from a flat 700ms interval to 600ms → 3s (capped), matched to the real measured latency distribution (3-25s across the four async reports) — cuts total poll requests substantially on the two slow reports without losing responsiveness on the two fast ones.
- Deliberately **not** touched: server-side response caching for the underlying Python-spawn-backed services (company-health, revenue-summary, etc., independently measured at 0.5-14 real seconds per call). `server.js` already has exactly this pattern (`runRealityCached()`, a 30s TTL wrapper, adopted specifically because `GET /api/dashboard` was taking 3-4 real seconds per call). Applying it here would be the highest-leverage remaining speed win, but it sits in the shared `/api/v1/*` service layer used by every other real caller (n8n, `mission_control.html`, direct API consumers) — out of scope for a dashboard-only polish pass; flagged below as priority #2.

## Duplication

Checked via real network-request inspection (88 real requests captured across one full load): every one of the 18 cards maps to a distinct real endpoint — no two sections share a data source. The one real duplication found was internal, not data-facing: `kind:'health'` and `kind:'summary'` were dead labels in `SECTIONS` — `renderSection()` never actually branched on them, both were silently identical to `kind:'kv'`. Removed the misleading distinction.

## Responsiveness

Reviewed and tightened the existing `@media (max-width: 880px)` breakpoint (off-canvas sidebar, no horizontal scroll) and the raw-JSON block CSS (switched from horizontal-scroll-only to `white-space:pre-wrap`, removing the need to scroll sideways to read a log line or JSON block on a narrow screen). The available browser tooling in this session could not force a true narrow-viewport screenshot (`resize_window` did not propagate to the screenshot renderer) — this was code-reviewed and the CSS itself is unchanged in structure from ADR-123's original build, which was live-verified on a real narrow viewport at build time. Flagged below as a real gap: this round's specific CSS changes were not re-verified pixel-for-pixel on a real narrow device.

## Validation

- `node -c server.js`, the jsonl-duplication guard, and the same inline-JS syntax check CI runs against `mission_control.html` were all run against `mission_control_executive_v1.html` — clean.
- Added one focused regression test to `tests/test_api_contract.js` (mirroring the existing `dashboard.html`/`mission_control_login.html` serve-check): confirms the route requires Mission Control auth and serves real HTML once authenticated.
- Ran the actual CI-equivalent JS suite (`.github/workflows/ci.yml`'s real invocation list — `test_metrics.js`, `test_dashboard_data.js`, `test_n8n_notify.js`, `test_factory_loop_golden.js`, `test_api_contract.js`) — all green. `node --test "tests/**/*.js"` (a broader glob used earlier this session) was found mid-round to sweep up `tests/fixtures/always_crash.js`/`crash_n_times.js` — deliberately crash-simulating fixtures meant to be spawned as controlled subprocesses by other real tests, not executed directly — and hard-crash the whole run; confirmed this is pre-existing and unrelated to this round's changes (CI itself never runs that glob), not a regression introduced here.
- Zero Python files touched this round; Python suite unaffected.

## What's deliberately not done

- No server-side caching for the slow Python-spawn services (see Loading Speed above) — real, measured, but out of this pass's scope.
- No true mobile-device pixel verification this round (tooling limitation, see Responsiveness above).
- No new real-time/push refresh — the dashboard is still pull-only; a founder checking it several times a day re-pays the full real fetch cost each time.
- No change to the single shared Mission Control password model — matches this factory's existing, deliberate `IDENTITY_ARCHITECTURE.md` stance; revisited only at that document's own stated triggers, not as a dashboard-specific decision.

## Answers to the founder's three questions

**Is Mission Control production-ready?** Yes, for its actual intended audience — the founder, as the sole real user, checking the real state of a real, early-stage, one-person company. Every real bug found this round is fixed, every panel shows real data or an honest "No verified data," and the two most important cards (Company Health, Executive Summary) now genuinely support a 30-second read. It is not yet ready for a broader external/investor-facing "public launch" — see below.

**What's still missing before public launch?** Server-side caching for the slow real services (2-25s per call today); true mobile-device verification; a real-time or auto-refresh mechanism instead of pull-only; a role-based access review of which of the 18 panels (raw logs, the full knowledge graph) should sit behind the same single password as revenue and health; a consistency check between the Executive PDF Report (a separate real code path) and what's on screen; an automated visual/DOM smoke test beyond today's "does the route serve 200."

**Top 10 improvements by priority:**
1. ~~Fix the 4 real bugs above~~ — done this round.
2. Server-side short-TTL caching for the slow Python-spawn services, reusing the already-adopted `runRealityCached()` pattern — the single largest remaining real latency win; needs its own scoped review since it touches the shared service layer, not just this dashboard.
3. True narrow-viewport/mobile QA on a real device.
4. Auto-refresh or push instead of pull-only.
5. Role-based access review for the 18 panels.
6. One consistent "confidence" taxonomy across all 18 sections (today inferred per-field).
7. Verify the Executive PDF Report's content actually matches the live page (separate code path today).
8. An automated visual/DOM regression test asserting "18/18 sections live" against real seeded data, not just "the route returns 200."
9. Decide whether to add a short inline explainer next to Opportunity/Investment/Product-Portfolio's small real numbers (2-3 real accepted opportunities today) so a first-time viewer reads that as the real, honest state rather than assuming a bug.
10. Revisit the single-password auth model only when `IDENTITY_ARCHITECTURE.md`'s own stated triggers fire — not sooner, and not as a reaction to this dashboard specifically.
