# التشغيل والبنية الأساسية (منقول من CLAUDE.md)

## Running the project

```powershell
# Install Node dependencies (first time)
npm install

# Install Python dependencies (first time)
pip install reportlab

# Start the server
node server.js
# Runs at http://localhost:3000 (or PORT env var)

# Start it supervised instead (Enterprise Upgrade Roadmap Phase 1.1,
# 2026-07-23) — auto-restarts on a real crash, gives up and alerts via
# Telegram after too many restarts in a short window instead of looping
# forever. Fully opt-in: the manual `node server.js` above still works
# exactly as before, nothing about it changed.
node scripts/supervisor.js

# Start factory_loop.js supervised too (2026-08-07 — Autonomous CEO
# continuous-improvement round): scripts/supervisor.js's own
# SUPERVISOR_TARGET override (already real, already tested,
# tests/test_supervisor.js) was documented as "testing only" but is a
# real, unconditional code path with no such restriction -- factory_loop.js
# had been manually restarted twice in one real session after the
# environment killed it (once found already-dead, once mid-tick) with
# nothing watching it. Same real crash-loop guard + real Telegram alert
# on every crash + safe backoff, now covering factory_loop.js too, zero
# new code.
SUPERVISOR_TARGET=factory_loop.js node scripts/supervisor.js
```

There is no build step, test suite, or linter configured.

## Architecture

**Galaxy Forge** is an Arabic-language (RTL) dashboard for a self-publishing business selling digital products on KDP, Etsy, and Gumroad.

### Stack

| Layer | Technology |
|---|---|
| Frontend | Single-file vanilla HTML/CSS/JS (`index.html`), Arabic RTL, no framework |
| Backend | Express 5 (`server.js`), port 3000 |
| AI | Groq SDK — `llama-3.1-8b-instant` via `POST /chat` and `POST /api/agent/:name` |
| PDF generation | Python + reportlab (`book_generator.py`) |
| Data | `finance_data.json` (flat JSON, written directly by server) |

### Key flow: book generation

The browser calls `POST /generate-book` → `server.js` spawns a Python subprocess (`book_generator.py --json`) → passes parameters via `stdin` as JSON → reads JSON result from `stdout`. The PDF is written to the project root directory with a filename derived from the book title.

`book_generator.py` is standalone and can be run directly:
```bash
python book_generator.py          # generates demo_cookbook.pdf
```
When invoked with `--json`, it reads a JSON object from stdin:
```json
{"title":"...", "subtitle":"...", "type":"journal", "theme":"blue", "pages":120, "author":"...", "output":"filename.pdf"}
```
Supported `type` values: `journal`, `planner`, `habit`, `gratitude`, `fitness`, `tracker`, `healthy_eating`, `budget`, `mindfulness`, `cookbook`.

### Environment variables (`.env`)

```
GROQ_KEY=<your Groq API key>
PORT=3000
N8N_PRODUCTION_WEBHOOK_URL=<optional — n8n webhook URL for production-completion notifications, unset by default>
```

`N8N_PRODUCTION_WEBHOOK_URL` gates `server.js`'s `notifyN8nProductionEvent()` (n8n Integration Gap fix): when the `start-production-pipeline` Mission Control action completes at least one real dossier, it fire-and-forget `POST`s a plain projection of that dossier to this URL if set. Unset by default — a real production run must never fail or block on n8n being unreachable or unwired. See `n8n_workflows/README.md`'s "n8n Integration Gap audit" section for the full workflow map, what's proven live vs. still blocked on manual n8n activation (`BLOCKERS.md` #1), and the exact steps to wire this up.

(This file's own env-var list above predates several since-added optional vars from later work sessions — e.g. `MISSION_CONTROL_PASSWORD`, `FACTORY_LIVE_PUBLISH`, `GUMROAD_ACCESS_TOKEN`, `INTERNAL_SERVICE_TOKEN` (2026-07-23, a shared secret real internal automation — `factory_loop.js`, the `01_Market_Scout` n8n workflow — sends as `X-Internal-Token` to reach the handful of routes that need real automated access with no browser session available; see `server.js`'s `requireMissionControlOrInternalToken`) — each documented at its own point of use in `server.js` rather than cross-referenced here; not fully re-catalogued in this edit, which is scoped to the n8n gap fix only.)

### Agent endpoints

`POST /api/agent/:name` — **live Groq calls**, not stubs. **Gated behind `requireMissionControlAuth` since the Enterprise Security & Cyber Defense Mission's Phase 1 Security Audit (2026-07-23, finding 2.1)** — this route previously had zero authentication, meaning anyone who could reach it could spend the founder's real Groq API budget with an arbitrary `message` and no rate limit; that is now fixed. A logged-in Mission Control session (via `mission_control_login.html`) is required before `index.html`'s own buttons that reach this route will work — the same real prerequisite `/finance/add` already had before this fix, now extended here and to most other previously-open routes (see `ENTERPRISE_UPGRADE_ROADMAP.md`'s finding 2.1 for the full route list and which ones instead accept `INTERNAL_SERVICE_TOKEN` for real internal automation callers that have no browser session). Each of the six agents has a dedicated `system` prompt defined in the `AGENT_PROMPTS` object in `server.js` (lines 127–190):

| Agent | Role |
|---|---|
| `scout` | Market analysis — trending niches, pricing, competition level |
| `builder` | Content generation — book structure, sample pages |
| `design` | Cover & interior design ideas for 6×9 inch books |
| `qa` | Quality checklist, common KDP/Etsy rejection reasons |
| `publisher` | SEO-optimised titles, descriptions, keywords, Amazon categories |
| `finance` | Pricing strategy, profit margins per platform, break-even |

Each agent accepts an optional `message` in the request body; if omitted, a default `trigger` prompt fires automatically. `index.html` only wires UI buttons for `builder`/`design`/`publisher`/`qa` — the bare `scout` and `finance` agents above are live and reachable via `POST /api/agent/scout` / `POST /api/agent/finance`, but have no UI trigger (the fuller `/api/scout/run` pipeline below is what the UI's Scout button actually calls).

There is also a separate, more complete Scout pipeline: `POST /api/scout/run` runs a real end-to-end chain — Groq market brief → pricing (`getButterPrice()` in `factory_loop.js`) → niche safety filter (`safety_filter.py`) → `book_generator.py` → auto-distribution (`autoDistributeScoutBook()` → `distributor.py`). This is distinct from the simple `POST /api/agent/scout` text-analysis call above and is what the dashboard's Scout button triggers.

`POST /chat` (`server.js:1768`) — a raw Groq passthrough (any `message` in the request body goes straight to `llama-3.1-8b-instant`). Confirmed via full-repo audit (STRUCTURAL_DIAGNOSIS.md disease #8) to have **zero callers**: not `index.html`, not `factory_loop.js`, not any test, not any other doc. Predates the six-agent `POST /api/agent/:name` system above and was superseded by it in every practical sense. **Gated behind `requireMissionControlAuth` since the Full Factory Integrity Audit (2026-07-22)** — this line previously described it as unauthenticated; that was fixed in code but never updated here until now. Still zero real callers, so still a candidate for removal rather than a route to build on.

### Finance data

Finance is persisted to `finance_data.json` in the project root. The server reads/writes this file synchronously. Structure:
```json
{"sales": [...], "totalKDP": 0, "totalEtsy": 0, "totalGumroad": 0}
```
`DELETE /finance/delete/:id` (`server.js:558`) exists alongside `POST /finance/add` but has no UI button wired to it in `index.html` — a half-finished CRUD pair, not dead code (low risk: local JSON mutation only, id-validated).

### Executive Dashboard

`GET /api/dashboard` (`server.js`) and the static page `dashboard.html` (served automatically by `express.static`, plain UTF-8 unlike `index.html`) aggregate real, already-existing signals into one view: `computeHealthStatus()`, `self_awareness.assessSelfAwareness()`, and `lib/dashboard_data.js`'s pure file reads over `golden_opportunities.json`, `finance_data.json`, `market_hunter_runs.log`, `pending_review/`, `tier1_intake/candidates/`, `NEEDS_ATTENTION.md`, `NEEDS_REVIEW.md`. It computes nothing new and fabricates no metric — a section with no data yet reports that honestly (e.g. `tier1_discovery.accepted` is 0 today, matching `ADR-035`/`ADR-036`'s real finding, not an invented KPI). `lib/dashboard_data.js` has no Express/`child_process` dependency, so it's unit-tested in isolation (`tests/test_dashboard_data.js`) without needing a live server.

`GET /health` (`computeHealthStatus()`, `server.js`) gained real infrastructure checks (Enterprise Infrastructure & HA Mission, 2026-07-23, finding 4.7): memory, CPU (honestly reports `os.loadavg()` as unavailable on Windows rather than faking a number), disk space (Windows-only today — no POSIX deployment exists yet to build a cross-platform check against), real network reachability to this factory's actual external dependencies (Groq, Telegram if configured, GitHub), and `storage_integrity` — real per-line JSON/JSONL validation of `data/decisions.jsonl`/`finance_data.json`/`data/factory_state.json`, the honest analog to "database health" for an architecture that has none. `database`/`queue_system`/`worker_pool` are reported as explicit `not_applicable` (never a fabricated green check) — this factory has no database, no message queue, and no worker pool. Logic lives in `lib/health_checks.js`, same no-Express-dependency isolation-testing pattern as `lib/dashboard_data.js` (`tests/test_health_checks.js`).

