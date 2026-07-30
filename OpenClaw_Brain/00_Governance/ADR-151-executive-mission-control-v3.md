# ADR-151 — Executive Mission Control V3: Division Command Center

**Date:** 2026-07-30
**Status:** Adopted and built. Additive only — zero rewrite of the existing 64-panel drill-down layer (ADR-146) or any Python module.

---

## The directive (verbatim)

> Founder Executive Directive — Executive Mission Control V3
>
> The Affiliate Commerce Division is now established and validated as a permanent business division.
>
> No further expansion of Affiliate Commerce should occur until a real affiliate account is approved and connected.
>
> The company's highest priority now becomes the Executive Mission Control.
>
> Mission Control must evolve from a technical dashboard into a true Executive Command Center.
>
> Its purpose is not to display data.
>
> Its purpose is to allow the Founder to understand, supervise and direct the entire company from one screen.
>
> Requirements:
>
> 1. Create a premium executive interface suitable for managing a global AI company.
>
> 2. Every business division must have its own live status panel, including: Executive Brain, Market Intelligence, Global Opportunity Exchange, Capital Allocation Engine, Evolution Queue, Autonomous Operations, Digital Products Division, KDP Publishing, Affiliate Commerce, Finance, Knowledge Graph, Production, Quality Assurance, Infrastructure, Automation, Alerts, Executive Decisions.
>
> 3. Every panel must display: Current status, Health, Live activity, Pending work, Errors, Performance indicators, Last execution time.
>
> 4. Build an Executive Summary section containing: Company Health Score, Revenue Overview, Active Opportunities, Publishing Status, Affiliate Status, Production Queue, Strategic Alerts, Founder Actions Required.
>
> 5. The dashboard must support: Real-time refresh, Dark premium design, Responsive layout, Zero duplicated information, Clear visual hierarchy, Fast loading.
>
> 6. Preserve every existing API and architecture. No rewrites unless strictly necessary.
>
> 7. Every new panel must reuse existing services whenever possible.
>
> 8. If information already exists elsewhere, consolidate it instead of duplicating it.
>
> 9. Produce a complete implementation report explaining: What was reused, what was added, which APIs feed every panel, remaining executive improvements.
>
> Galaxy Forge Mission Control should resemble the control center of a world-class technology company rather than a developer dashboard. Architectural quality, maintainability and executive usability are the primary objectives.

The directive's opening two lines (Affiliate Commerce validated as permanent, no further expansion until a real account is approved and connected) are a status confirmation, not new work — they restate ADR-149/150's own already-recorded state and validation gates. No code change was needed for that part; it's recorded here only because the directive itself is quoted verbatim per this session's standing convention.

## What was found before any code was written

A direct diff of `server.js`'s `SERVICE_REGISTRY` (66 real entries) against every currently-wired Mission Control panel (`mission_control_executive_v1.html`'s `SECTIONS` array, 64 real panels as of ADR-146) found **20 real, already-working services with zero Mission Control panel** — including exact 1:1 matches for named-but-unrepresented divisions in this directive: `ai-doctor` (Quality Assurance), `infrastructure-status` (Infrastructure), and `founder-console` (a real, literal match for "Founder Actions Required" — its own docstring calls it "the only view framed as 'you need to decide something'").

Further research found the directive's per-panel field list (Status/Health/Live activity/Pending work/Errors/Performance/Last execution time) is almost entirely already real and already available, just not yet surfaced together:

- **Status** — the existing `pillFor()`/`state[id].status` machinery (ADR-146) already computes this per panel.
- **Health** — `GET /api/v1/health` (server.js, pre-existing observability layer) already returns a real per-service `{name, status, detail}` array via `computeServiceLayerHealth()`.
- **Errors** — the same `/api/v1/health` response's `detail` field, already real, already populated when a service's own `health()` check fails.
- **Last execution time** — every existing panel already shows `Updated: <relTime(s.fetchedAt)>`, sourced from the real `generated_at` timestamp the Unified Service Layer stamps on every response.
- **Performance indicators** — the one genuine gap. `lib/metrics.js`'s `METRICS_REGISTRY` already records real per-route request count, error count, and latency sum/count (`recordRequest()`, Phase 10A Production Stability) — but was only ever exposed as Prometheus text at `GET /api/v1/metrics`, not consumable by the dashboard's own JS.
- **Live activity** / **Pending work** — real, but inherently per-service: no single generic field exists across all 66 services. Live activity is answered by each division's own real payload (condensed, not duplicated verbatim — see below); Pending work is answered honestly only for the small number of divisions with an explicit, named real "awaiting" array field (Evolution Queue's `awaiting_approval`, Founder Console's `pending_decisions`) — every other division honestly shows "—", never a guessed or heuristic count.

This meant the directive was achievable almost entirely through **reuse**, exactly as it asked (#6, #7, #8) — not a second dashboard, not new Python logic, not a rewrite of ADR-146's real 64-panel layer.

## What was built

**1. `lib/metrics.js`** gained `summarizeRoutes(registry)` — a pure function turning the exact same real counters `recordRequest()` already fills into a JSON-shaped `{ [route]: {count, errors, avg_latency_ms} }` map. No new instrumentation, no second measurement system — a second, JSON-shaped view of data already being recorded for the pre-existing Prometheus endpoint.

**2. `server.js`** gained `GET /api/v1/metrics.json`, calling `summarizeRoutes()` — real per-route performance data the dashboard can actually consume (Prometheus text can't be parsed cheaply client-side).

**3. Three new `SECTIONS` entries** in `mission_control_executive_v1.html`: `ai-doctor`, `infrastructure-status`, `founder-console` — each pointing at a real, already-working `SERVICE_REGISTRY` entry that simply had never been wired to a panel. Zero backend change; this only adds them to the pre-existing fetch/render pipeline (`fetchSection()`/`renderSection()`, ADR-146) that every other panel already uses.

**4. A new "Division Command Center" + "Executive Summary" tier**, `renderDivisionGrid()`/`renderExecutiveSummary()` (new JS), rendered above the existing 64-panel drill-down layer (`#sections`, completely unchanged). Reads exclusively from data already fetched into the existing `state` cache, plus two new lightweight once-per-refresh fetches (`fetchHealthMap()` → `/api/v1/health`, `fetchMetricsSummary()` → `/api/v1/metrics.json`) — zero duplicate fetching of any per-service data. Each Division Card and Executive Summary tile shows a condensed real summary (`renderDivisionCardBody()`, reusing the existing `flattenLeaves`/`labelFor` helpers, capped at 3 real numeric fields) plus the 7 directive-named fields, and links (`View full detail →`) to its own real, unabridged detail panel further down the same page — satisfying "zero duplicated information" (#5) by design: the summary tier cites, never re-renders in full, what the drill-down tier already shows.

**5. Division → real service mapping** (all 17 named divisions, all real, no fabrication):

| Division | Real service | Division | Real service |
|---|---|---|---|
| Executive Brain | `executive-brain` | Digital Products Division | `product-portfolio` |
| Market Intelligence | `commercial-intelligence` | KDP Publishing | `distribution-status` |
| Global Opportunity Exchange | `global-opportunity-exchange` | Affiliate Commerce | `affiliate-commerce-status` |
| Capital Allocation Engine | `capital-allocation-dashboard` | Finance | `revenue-status` |
| Evolution Queue | `evolution-queue` | Knowledge Graph | `knowledge-graph` |
| Autonomous Operations | `autonomous-operations-status` | Production | `production-status` |
| Quality Assurance ★ | `ai-doctor` | Infrastructure ★ | `infrastructure-status` |
| Automation | `automation-status` | Alerts | `alerts` |
| Executive Decisions | `decision-memory` | | |

★ = newly wired this round (previously orphaned real service). Executive Summary: Company Health Score → `company-health`; Revenue Overview → `revenue-status`; Active Opportunities → `opportunity-pipeline`; Publishing Status → `distribution-status` (deliberately reused rather than adding a 4th new panel — see below); Affiliate Status → `affiliate-commerce-status`; Production Queue → `production-status`; Strategic Alerts → `alerts`; Founder Actions Required ★ → `founder-console`.

**Implementation-level refinement from the plan reviewed with the founder**: "Publishing Status" was planned to cite the `get-company-reality-score` action, but that action has no existing `SECTIONS` entry (it's an `ACTION_REGISTRY` async report, not a plain `GET` service) — wiring it would have meant a 4th new panel beyond the 3 scoped in the approved plan. `distribution-status` (already wired, real per-platform publishing checklist) answers the same real question just as honestly, so it was reused instead — keeping this round to exactly the 3 new panels the plan committed to.

**6. Visual/premium design.** New, purely additive CSS (`.exec-tier`, `.division-grid`, `.division-card`, `.exec-tile`, `.division-drilldown`) reusing the existing theme variables (`--bg`, `--ink`, `--accent`, `--good`, `--warn`, `--shadow`) and the existing `.card-top`/`.card-meta`/`.pill`/`.stat-row` component classes verbatim — no new theme system, no rewrite of any existing style rule. Responsive via the same `repeat(auto-fit, minmax(...))` grid convention `.card-grid` already used (ADR-146). Fast loading: zero new per-panel network round-trips (2 new fetches total per refresh cycle, not 17).

## What is honestly disclosed as partial, not fabricated

- **Pending work** is a real, named field only for divisions with an explicit real "awaiting" array in their own payload (Evolution Queue, Founder Console/Executive Summary). Every other division shows "—" rather than a guessed or heuristic count — there is no generic, safe way to infer "pending work" from an arbitrary payload without risking a false signal.
- **Performance** is real (backed by `/api/v1/metrics.json`) but reflects requests made *during this server process's uptime* — a freshly restarted server honestly shows "No requests recorded yet" for every division until each service is actually called at least once, never a fabricated historical average.
- **Health**, where a service's `/api/v1/health` check hasn't run this cycle (e.g. a transient fetch failure), honestly shows "not separately tracked" rather than assuming "ok."

## What was deliberately not wired this round

17 further real, orphaned `SERVICE_REGISTRY` entries were found during research but are **not** part of the directive's named 17 divisions or 8 Executive Summary tiles, so they were left unwired to keep this round scoped to what was actually asked (per the directive's own #6, "no rewrites unless strictly necessary," read as "no unscoped expansion either"): `decision-history`, `evolution-report`, `market-review`, `golden-hunter-status`, `pioneer-status`, `production-families`, `commercial-execution`, `knowledge-base`, `research-department`, `strategic-recommendations`, `integration-registry`, `system-configuration`, `recovery-status`, `unified-priorities`, `product-concept-comparison`, `department-health`, `opportunity-queue`. These remain a disclosed candidate list for a future consolidation round, not silently dropped.

No Python module changed. No existing `SERVICE_REGISTRY`/`ACTION_REGISTRY` handler logic changed. No existing panel in the 64-panel drill-down layer changed. No new top-level `GROUPS` entry. No new execute-capable code path — every new element in this round is a read-only citation of already-real data.

## Validation

Live-verified against a disposable local server (see this session's established pattern): `GET /api/v1/metrics.json` returns real per-route counts/latency after real requests are made; `GET /api/v1/ai-doctor`, `/api/v1/infrastructure-status`, `/api/v1/founder-console` return their pre-existing real payloads unchanged (confirming these services themselves needed zero modification — only a panel was added); a real logged-in browser session confirmed the Executive Summary's 8 tiles and all 17 Division cards render real data (real book/opportunity/click/node counts, e.g. Knowledge Graph's real 2948 nodes / 2759 edges, Affiliate Commerce's real 0 clicks / 4 products) with zero console errors, and that all pre-existing 64 panels below them render unchanged (regression check). The full 2048-test suite was re-run and passed with zero regressions.

**A real, previously-hidden fact this round's own verification surfaced**: `ai-doctor` (Quality Assurance) and `product-portfolio` (Digital Products Division) both genuinely timed out on one live run (30s and 45s respectively) — real, slow Python-subprocess computations that had simply never been observed before because neither had a Mission Control panel until this round. The dashboard's existing honest-timeout handling (`"No verified data — timed out waiting for a real result (Ns)"`) rendered correctly rather than hanging or showing a fabricated result — but this is a real latency characteristic worth a founder's attention independent of this ADR, not a regression this round introduced.
