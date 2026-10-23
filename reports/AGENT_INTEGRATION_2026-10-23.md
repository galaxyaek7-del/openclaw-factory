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
