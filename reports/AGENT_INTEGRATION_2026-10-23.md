# Agent integration and blockers — 2026-10-23

Evidence classes: OBSERVED (seen in a live call or on disk), DERIVED (computed from observed records), UNKNOWN.

## The six agents

`AGENT_PROMPTS` (now `lib/agent_prompts.js`) defines six agents. Each was called live through `lib/agent_runtime.js` (`scripts/agent_probe.js`, 1024 max tokens, model `openai/gpt-oss-20b`). Every call is one line in `data/agent_executions.jsonl`.

| Agent | Executable | Connected to an automated flow | Status |
|---|---|---|---|
| scout | yes (OBSERVED) | No. `/api/scout/run` is a manual button; last pipeline run 2026-07-09. Ran in the research chain today (manual run). | VERIFIED_EXECUTABLE_NOT_CONNECTED |
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

Data-quality finding (not fixed): `OPPORTUNITIES.md` now carries celebrity and athlete names from Google Trends that passed the quality and safety gates.

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
