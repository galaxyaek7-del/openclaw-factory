# ADR-123 — Galaxy Forge Executive Mission Control v1

**Date:** 2026-07-24
**Status:** Adopted.

---

## The directive

Founder decision: "Do NOT build any new engines. The priority is to expose everything that already exists through one production-grade executive dashboard." 18 named sections, dark premium design, desktop-first/mobile-responsive, every card showing live status/last-update/data-source/confidence, global search/filters/refresh/export/executive PDF report, "no placeholders, no fake charts, no invented KPIs."

## What real infrastructure this was built on

Audited before writing any UI: this factory already had a real, versioned, authenticated, self-documenting API surface — `server.js`'s `SERVICE_REGISTRY` (33 real services, each backed by an already-built, already-tested module, each with its own real health check) and `ACTION_REGISTRY` (mutating/longer-running real operations, sync or async, job-tracked), both served under `/api/v1/*` and enumerable at `GET /api/v1/docs`. **14 of the 18 requested sections already had a real, ready GET service.** Only 4 needed anything new:

- **Evidence Engine** — a real aggregate over `data/market_evidence.jsonl` (the ledger built this session, ADR-121/122): total events, niches with any, breakdown by type, payment-evidence count. Honestly empty (it has never been auto-populated, by design).
- **Scheduler** — a real, live `Get-ScheduledTask` query against the one real durable scheduler this factory has (`OpenClaw-WeeklyPublicReport`, ADR-119), including its real next-trigger day/time.
- **Recent ADR Decisions** — a real directory read of `OpenClaw_Brain/00_Governance/ADR-*.md` (123 real files today), parsing each file's own real title/date/status header.
- **Live Logs & System Diagnostics** — a real tail (last 20 lines) of the 5 real operational log files this factory actually writes.

All 4 are plain reads over existing real files — zero new scoring, zero new decisions, zero new external connectors. `infrastructure-status` (already real) covers the diagnostics half of the last section.

**A real distinction discovered mid-build, not assumed:** several services the founder's spec implied would be simple `GET` calls (Executive Summary → `get-ceo-dashboard`, Investment Pipeline → `get-investment-pipeline`, Product Portfolio → `get-portfolio-report`, Market Memory → `get-monthly-market-evolution-report`) are actually registered as real `ACTION_REGISTRY` entries — three of them genuinely `kind: 'async'` (a real Python subprocess job, polled via `GET /api/v1/actions/:id` until it actually finishes, not returned synchronously). The dashboard's own data layer was built to use the correct real transport for each — `POST /api/v1/actions/<name>` + real polling — rather than force a GET call that would 404. Two of these four real reports (`get-investment-pipeline`, `get-portfolio-report`) take ~25-30 real seconds (scanning all 58 real decisions) — confirmed by direct testing, not assumed; the dashboard's poll timeout was set to 45s specifically because of this real, measured latency.

## What was built

- **4 new `SERVICE_REGISTRY` entries** in `server.js` (`evidence-engine-status`, `scheduler-status`, `recent-adr-decisions`, `system-logs`), each a thin real handler function, each with a real health check.
- **`mission_control_executive_v1.html`** — a new, separate, purpose-built executive page (dark, English, card-based) over the exact same real `/api/v1/*` services — deliberately not a rewrite of `mission_control.html` (the pre-existing, Arabic, day-to-day operational console with its own established real tab structure). Same auth (`requireMissionControlAuth`) as every other Mission Control page.
- **Real honesty conventions, not invented per-card:** "Confidence" reads a real field already present in the payload (e.g. this factory's existing `maturity`/`confidence.level` taxonomy) where one exists, else derives Verified/No-verified-data from real presence/absence — never a fabricated percentage. Empty, erroring, or timed-out real calls all render "No verified data" (or the real, timed-out reason), never a placeholder or a zero standing in for missing data.
- **Global search** filters already-rendered real card content client-side — no server round-trip, no invented result.
- **Export** downloads a real, timestamped JSON snapshot of exactly what's currently loaded on screen.
- **Executive PDF Report** reuses the real, pre-existing `export-executive-report` action (`validation_layer/daily_report.py` + `revenue_pipeline/pipeline.py`) rather than a second report generator, then opens the browser's own print dialog (Save as PDF) — no new PDF library dependency.

## A real layout bug found and fixed during testing

Live testing (not just unit tests) caught that deeply-nested real objects (e.g. `company-health`'s full `health`/`risk`/`self_awareness` payload) broke the initial 2-column key-value grid layout — nested JSON was squeezed into a narrow value column, pushing labels far left with large gaps. Fixed by detecting "complex" values (objects, long arrays) and rendering them as their own full-width block instead of forcing them into the grid.

## Verification

Live-tested end-to-end in a real browser session (not just curl): logged in with the real Mission Control password, confirmed all 18 sections reach "18/18 sections live," confirmed the real async action polling actually resolves (not just times out), confirmed search correctly filters on real nested content, confirmed mobile-width rendering. 4 new focused tests added to `tests/test_api_contract.js` for the 4 new services' real content shape (already-existing generic contract tests in the same file automatically cover all 33+ services' envelope/health contract, including these 4, since they enumerate `GET /api/v1/docs` dynamically).

## What's deliberately not done

- No new engines, scoring, or decision logic anywhere in this round — confirmed by construction, every card is a read over something that already existed.
- `mission_control.html` (the Arabic ops console) is untouched — this is a second, purpose-built executive layer, not a replacement.
- No server-side PDF-generation library added — the real, existing markdown report + the browser's own print-to-PDF is the honest, dependency-free choice.
- Commercial Intelligence and Alerts render the single most recent real record / the current real flag state rather than a full per-niche browser — a real, disclosed scope choice for v1, not a missing feature hidden as complete.
