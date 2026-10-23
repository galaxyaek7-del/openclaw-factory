# Factory current state (verified 2026-10-23)

Every line below was observed or measured in this session; anything not measured is marked UNKNOWN. Evidence classes: OBSERVED (seen directly), DERIVED (computed from observed inputs), INFERRED, UNKNOWN.

## Environment

| Fact | Value | Class |
|---|---|---|
| Working directory | `C:\openclaw-dasgboard` (not `openclaw-dashboard`) | OBSERVED |
| OS / runtimes | Windows 11 Pro; Python 3.14.6; Node 24.16.0 | OBSERVED |
| Branch / HEAD | `main`, `0216522` (pushed; `origin/main` equal) | OBSERVED |
| Tracked files | 3,564 (1,083 Python, 143 JS) | OBSERVED |
| Tests | 369 Python + 76 JS test files; CI floor 4,369 Python cases | OBSERVED |
| Working tree | 177 modified and 2,111 untracked files that predate this work (parallel sessions) | OBSERVED |
| Documentation | 557 Markdown files at the repository root, 377 files in `reports/`, ~174 ADR files | OBSERVED |

## Running system

| Component | State | Evidence |
|---|---|---|
| `server.js` (Express, port 3000) | running under `scripts/supervisor.js` | `/health` 200 after restarts |
| `factory_loop.js` | running supervised, 53 steps per ~10-minute tick | `factory_loop.log` |
| n8n | 3 company workflows: Sales_Poll OK, Openclaw_Sensing_Engine OK, 01_Market_Scout manual-only | `scripts/n8n_workflow_health.py` |
| Connection verifier | 49 VERIFIED, 3 DEGRADED (diagnose, evidence_recording_audit, paddle_checkout_notification) | `connection_verifier.py` |
| Six AI agents | all executable; scout and qa connected to the loop; finance, design, builder, publisher connect on the first qa PASS | `data/agent_executions.jsonl` |
| CI (GitHub) | 36/36 green on `cde4f73`; later commits pending at time of writing | Actions API |

## Commercial reality

| Fact | Value | Class |
|---|---|---|
| Gumroad listings | 92 (82 before + 10 published 2026-10-23) | OBSERVED (API) |
| Verified sales, any channel | **0**; revenue **$0.00** | OBSERVED (`config/reality.json`, Gumroad `/v2/sales`) |
| Site traffic | **UNKNOWN: not measured.** GitHub Pages has no page-view receiver, so the beacon (`customer_site/assets/gf-pageview.js`) gets 404 and records nothing; the 32 rows in `data/affiliate_page_views.jsonl` are local probes and tests (3 classified as browsers) | OBSERVED |
| Paid product files publicly downloadable | 168 in the repository tree before 2026-10-23; removal in progress (founder decision) | OBSERVED |
| Paddle | live key returns 403 (missing permissions) | OBSERVED |
| Telegram | bot token valid; chat id not set | OBSERVED |

The binding constraint is demand reaching the products, not production capacity: 92 listings and 0 sales. How many people visit the site is unknown, because public traffic is not measured.

## What works and is trustworthy

- External-write gate (`channels/write_gate.py`) with separate classes for catalog, checkout, messages and search pings; single-use scopes (`channels/write_scope.py`); auth-state freshness and fingerprint check (`gumroad_auth_watch.py`).
- Read-back verification of Gumroad writes (`channels/gumroad_publisher.py`: update, cover).
- Independent spreadsheet recalculation (`lib/xlsx_eval.py`) and file tests (`file_testing_engine.py`).
- Operating doctrine with machine checks (`scripts/check_doctrine.py`, 53/53).
- Ledgers: publish attempts (`data/sales_ledger.jsonl`), agent executions, agent tasks, connection status.

## What is not trustworthy as a status

- Readiness labels in the 293 Mission Control services and 306 API endpoints: many are citation layers over the same few signals.
- `data/catalog.json`: keyed by platform id; 71 of 83 rows `UNREVIEWED`, quality `UNKNOWN`; does not contain the 10 products published on 2026-10-23.
- The canonical inventory (`reports/CYCLE104/DIGITAL_PRODUCT_INVENTORY.json`) covers 21 products and mixes Paddle ids, Amazon ASINs (affiliate items), Gumroad ids and internal ids.
