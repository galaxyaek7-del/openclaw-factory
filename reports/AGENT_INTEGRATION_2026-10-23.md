# Agent integration and blockers — 2026-10-23

Evidence classes: OBSERVED (seen in a live call or on disk), DERIVED (computed from observed records), UNKNOWN.

## The six agents

`AGENT_PROMPTS` (now `lib/agent_prompts.js`) defines six agents. Each was called live through `lib/agent_runtime.js` (`scripts/agent_probe.js`, 1024 max tokens, model `openai/gpt-oss-20b`). Every call is one line in `data/agent_executions.jsonl`.

| Agent | Executable | Connected to an automated flow | Status |
|---|---|---|---|
| scout | yes (OBSERVED) | Wired into `POST /api/trends` (daily Sensing run) on 2026-10-23. Becomes connected only when a real Sensing run records a `sensing_trends` call — first expected at the 2026-10-24 07:00 UTC run. | VERIFIED_EXECUTABLE_NOT_CONNECTED until then |
| qa | yes (OBSERVED, also via `POST /api/agent/qa` after restart) | No. UI button; ran in the research chain today (manual run). | VERIFIED_EXECUTABLE_NOT_CONNECTED |
| publisher | yes (OBSERVED) | No. Called inside `runDistributor`, which the write gate keeps shut. | VERIFIED_EXECUTABLE_NOT_CONNECTED |
| builder | yes (OBSERVED) | No. UI button only. | VERIFIED_EXECUTABLE_NOT_CONNECTED |
| design | yes (OBSERVED) | No. UI button only. | VERIFIED_EXECUTABLE_NOT_CONNECTED |
| finance | yes (OBSERVED) | No caller anywhere in the code. | VERIFIED_EXECUTABLE_NOT_CONNECTED |

Production risk found: at 200 max tokens, `openai/gpt-oss-20b` (a reasoning model) returned empty text for scout and finance. The runtime defaults to 1024.

## Handoff

`lib/agent_chain.js` + `lib/research_chain.js`. Run on 2026-10-23 (`task research_2026-10-23`, `data/agent_tasks.jsonl`):

1. Input: today's 10 Sensing trends from `OPPORTUNITIES.md` (the 07:41 UTC catch-up run).
2. scout → brief "DOJ Judge Recusal: A Comprehensive Playbook for Immigration Lawyers", $69.
3. qa received that brief → `REVISE` (unrelated trends, lacks depth).
4. `distribute` → blocked (`FACTORY_LIVE_PUBLISH` not true). Nothing was produced or published.

Data-quality finding: `OPPORTUNITIES.md` carried celebrity and athlete names from Google Trends. `book_generator.py::quality_gate()` only checks a non-empty niche, saved Amazon research (skipped when absent) and a cover theme, so every trend "passed all quality checks".

Fix (same day): `lib/trend_classifier.js`. `POST /api/trends` now asks the scout agent, after the safety filter, whether the trend is a recurring need someone would pay to solve; any classifier failure fails closed. Live run on the same day's 10 real trends plus 3 known product niches (telemetry to a temp file): all 10 trends → NO (people, a game release, a product model, a news event); all 3 niches → YES. This connects scout to the daily Sensing flow (source `sensing_trends`).

Consequence to decide on: Google Trends' daily feed is people and news. With this filter, Sensing will add few or no opportunities per day. A better source (category feeds, or the factory's own Hacker News / GitHub / Stack Overflow connectors) is a change to the live n8n workflow and needs founder approval.

## Mission Control

`GET /api/v1/connection-status` (Mission Control session required; 401 without). Reads `data/connection_status.json`, `data/agent_executions.jsonl`, `data/agent_tasks.jsonl`; a missing file is UNKNOWN with a reason. Verified live after the server restart.

## Blockers

| Item | State | What clears it |
|---|---|---|
| Paddle | Live key (`pdl_live_apikey`, `api.paddle.com`) returns 403 `forbidden` on `/products`, `/transactions`, `/event-types`. Paddle: the key is valid but lacks the permission; new permissions are not added to existing keys. 50 of 145 `paddle_checkout_notification` runs failed in 24 h for this reason. | Founder: Paddle dashboard → Developer Tools → Authentication → edit the key (or create a new one) with at least `product.read`, `price.read`, `transaction.read` (add `.write` only if checkout creation is wanted), then replace `PADDLE_API_KEY` in `.env`. If the key already has them, send the `request_id` to sellers@paddle.com. |
| Telegram | Bot token valid (`getMe` ok). `OPENCLAW_TELEGRAM_CHAT_ID` missing; `getUpdates` returned 0 updates. | Founder sends any message to the bot; the chat id can then be read and set. |
| Gumroad 82 vs catalog 83 | Reconciled in `reports/COMMERCIAL_RECONCILIATION_2026-10-22.md`. | — |
| 14 Gumroad repairs, 2 unpublish, 1 delete | Prepared in `drafts/release_packages/REPAIR_MANIFEST.json`; live mutations. | Founder authorization per action. |
| Push to `main` | Local commits not pushed. | Founder decision. |
| freelancer.com | Monitoring continues per founder order 2026-10-01; exempt from the write gate. | Founder decision to stop. |
| `fd394165` | False evidence record; correction item `0572d147f1b5` queued. | Data-integrity correction, not an approval. |
| Market_Scout (n8n `01_Market_Scout`) | Only a manual trigger; it runs the full KDP production pipeline. No real run made. | Founder decision (golden rule, live n8n change). |
| Claude updater | `claude doctor`: no installation issues; last update succeeded (2.1.309, 2026-10-23). | — |

## Automated product chain (added the same day)

`lib/product_chain.js` + `lib/daily_product_chain.js`, called by `factory_loop.js` (`agent_product_chain` step, right after `sensing_catchup`). Once per UTC day, when OPPORTUNITIES.md has a trend for that day:

scout brief → qa (REVISE stops the chain as a decision) → finance (price, platform) → design (cover, interior, palette) → builder (chapter outline) → publisher (listing title, description, tags) → package written to `drafts/agent_packages/product_<day>.json` with status `AWAITING_FOUNDER_REVIEW` → `distribute`, protected, blocked unless `FACTORY_LIVE_PUBLISH` is true.

Bounds: one finished run per day; at most 3 failed tries a day, each resuming at the failed step; 5-minute cap per tick; errors are reported in the tick, never thrown. Agent calls are recorded with source `loop`, so the verifier marks an agent connected only after the loop has really called it.

Live check (2026-10-23, real model, temp state/package paths, trends "small business bookkeeping" and "eu late payment interest"): all six agents answered within their contracts in 6 s; qa PASS; finance $49 / kdp; an 8-chapter outline; an English listing with 7 tags; distribute blocked.

## Tools

- npm: every dependency is current within its declared range. Only major versions are newer (dotenv 18, pdfkit 0.20); not applied — a major bump needs its own test run.
- Python: newer minor versions exist for certifi, pypdf, reportlab; pillow 13 is a major version. Not applied in this round.

## Pre-existing, not touched

`tests/test_factory_loop_daily_product_lifecycle_snapshot.js` is untracked (dated 2026-09-21) and calls `runRecordDailyProductLifecycleSnapshot`, which exists in no commit of `factory_loop.js`. It fails on its own; it is someone else's unfinished work.

## Revenue reality check (2026-10-23)

Measured, not estimated: 31 page views and 29 affiliate clicks recorded in three months (`data/affiliate_page_views.jsonl`, `data/affiliate_clicks.jsonl`); 79 live Gumroad products, 0 sales (`reports/COMMERCIAL_RECONCILIATION_2026-10-22.md`). The binding constraint is traffic, not production. $100,000 in a year is about $8,300 a month: roughly 280 sales at $30, or about 14,000 visits a month at a 2% conversion rate, against about 10 visits a month today.

## Founder decisions (2026-10-23, AskUserQuestion)

1. Clean the unpushed history of the three paid B12 files, then publish; afterwards the loop may push site-page-only updates that pass the tests.
2. Automatic search-engine notification (IndexNow) is authorized. Gumroad auto-publishing and Telegraph articles were not authorized.

Done:

- History: backup branch `backup/pre-history-clean-20261023`; the 62 unpushed commits rewritten without `books/batch12/B12-007_*` and `B12-009_*`; every commit's tree otherwise identical.
- `GF_ALLOW_SEARCH_PING` (allows search pings only) added to `.env`; `FACTORY_LIVE_PUBLISH` stays `false`.
- `scripts/indexnow_auto.py`: daily, changed published pages only, live-checked, always with `keyLocation`. Finding: the key file answers 404 at the host root and 200 under `/openclaw-factory/`; earlier submissions omitted `keyLocation`, so IndexNow could not verify them.
- `scripts/auto_publish_site.py`: pushes only ranges that touch site pages alone; code waits for a reviewed push.
- `lib/demand_sensing.js`: Stack Exchange + Ask HN questions through the same `/api/trends` gates.

## Open: paid products are public

168 product-like files (PDF/XLSX/ZIP), mostly the delivery bundles in `cohort_GF_BATCH10_2026_09/` and `cohort_GF_BATCH11_2026_09/dist/`, are in the public repository's current tree and download without login (checked: `B12-001_freelancer_rate_raise_calculator.xlsx` → HTTP 200 on raw.githubusercontent.com). Removing them from the current tree stops casual access; removing them from history needs a force push. Needs a founder decision.

## Evidence ledger, 2026-10-23 afternoon (PASS / FAIL / HOLD / BLOCKED / UNKNOWN)

| Item | Status | Evidence |
|---|---|---|
| History cleaned of 3 paid B12 files | PASS | 62 commits rewritten; every commit's tree identical except those paths; 0 occurrences in the pushed range; raw.githubusercontent.com → 404 for both files. Backups: `backup/pre-history-clean-20261023`, `backup/pre-history-clean-20261023-final`. |
| Push to origin/main | PASS | `7cb880f..08e65a9`, then `08e65a9..cde4f73`; fast-forward, no force. |
| CI-equivalent run on the clean tree (CI=true, GITHUB_ACTIONS=true) | PASS | groups b 203 OK (6 skipped), e 626 OK (5), f 237 OK (3), i-p 1615 OK (12); a, c-d, g-h, q-z passed in the first pass; 0 unimportable of 5853; all JS batches and checks passed. Python 3.14 locally vs 3.12 on CI. |
| GitHub CI on 08e65a9 | FAIL | run 39937686646: 35 of 36 jobs passed; `test` failed at "Python tests (b)": `test_b12_010_workbook` read Windows paths with `Path(...).name`, which on Linux returns the whole string. |
| Fix for that failure (`cde4f73`) | PASS | `PureWindowsPath(...).name`; group b 203 OK on the clean tree; GitHub CI on `cde4f73`: 36 of 36 jobs successful (2026-10-23 12:47 UTC), the first green CI on the public main in this cycle (`7cb880f` had failed). |
| Phase-3 permission patch (`d375735`) | PASS | Test-only: `@patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"})` on the two classes that test the gates behind the write gate, same pattern as `tests/test_distributor.py`. Without it: exactly 3 failures; with it: 28/28. No production file changed; 0 non-dry-run publish attempts recorded today. |
| publish_queue test fix (`8f0fe40`) | PASS | Prepared in the working tree by the parallel session; committed unchanged with that provenance stated. |
| Classifier retry (`f46387c`) | PASS | Telemetry: 3 of 14 calls returned empty output. Two attempts, then fail closed; both new tests fail on the previous code. |
| Live loop steps after restart | PASS | `demand_sensing` 35 fetched / 20 sent / 18 accepted; `indexnow` HTTP 200, 73 URLs (11 retried next tick); `site_publish` none; `agent_product_chain` ended for today (qa REVISE on the pre-filter trends). |
| Classifier strictness on Stack Exchange questions | HOLD | 18 of 20 accepted; the small model is lenient on personal questions. qa and founder review remain downstream. |
| Agents connected | PASS: scout, qa / HOLD: finance, design, builder, publisher | The four connect on the first day qa passes a brief. |
| Paid product files in the public tree (168) | BLOCKED | Founder decision (remove from tree, and/or rewrite history with force push). |
| Gumroad / Telegraph auto-publishing | BLOCKED | Not authorized. `FACTORY_LIVE_PUBLISH=false`. |
| Paddle 403, Telegram chat id | BLOCKED | Founder actions (key permissions; message the bot). |
| Spend | PASS | TOTAL_NEW_SPEND=$0. |

Side findings, not fixed here:

- Running the Python suite modified three tracked files in the test checkout (`GOLDEN_OPPORTUNITIES.md`, `QUARANTINE.md`, `REJECTED_NICHES.md`): some tests write to real repository files instead of temp paths.
- `tests/test_b12_010_workbook.py` line ~131 (the parallel session's uncommitted test) uses the same `Path(...).name` on a Windows path and will fail on CI the same way once committed.
