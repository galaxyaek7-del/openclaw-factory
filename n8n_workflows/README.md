# n8n_workflows/ — fixes applied and verified live (ADR-045)

**Update 2026-07-15: these are now LIVE, not just prepared.** With explicit authorization, applied via: real backup (`backups/pre_build_*.json`) → clean stop of the live n8n process (exact PID, not a broad kill) → `n8n import:workflow` against the now-offline database (zero concurrent-write risk) → restart → fresh export confirmed all 5 workflows intact with both fixes live. See `ADR-045` for the full step-by-step and verification.

The files below are kept as the exact record of what was imported — historical/audit value, not a pending action anymore. **Only workflow activation remains manual** (confirmed: n8n's `--activeState=fromJson` CLI flag errors outside queue/multi-main mode, so this genuinely requires the UI, not a gap in effort) — see `BLOCKERS.md` #1.

## What's fixed and why

**`01_Market_Scout.fixed.json`** — same workflow (same `id`, so importing it updates the existing one rather than creating a duplicate), same manual trigger, but its `HTTP Request` node previously had **no URL configured at all** (`parameters: {options: {}}`, confirmed via the real export — not a guess). Fixed to `POST http://localhost:3000/api/scout/run` — the real, existing endpoint this workflow's own name implies it should call (`CLAUDE.md`'s documented Scout pipeline). Left as a manual trigger, not scheduled: `/api/scout/run` calls Groq (a paid API), so making it fire automatically on a timer is a cost decision for a human to make explicitly, not something to add silently.

**`00_CEO.fixed.json`** — same workflow (same `id`), but its `Execute Workflow` node previously referenced an **unresolved workflow ID** (`value: "="` — an incomplete n8n expression, not a real workflow reference, confirmed via the real export). Rather than guess which other workflow a "CEO" orchestrator should chain to (an arbitrary business decision with no evidence behind it), the node is replaced with a plain `GET http://localhost:3000/api/dashboard` HTTP Request — the real Executive Dashboard aggregator built today. Renamed to "View Executive Dashboard" to match what it actually does now.

## Remaining manual step — activation only (UI-only, confirmed)

1. Log into `http://localhost:5678`.
2. Toggle **Active** on `Openclaw_Sensing_Engine` and `02_Sales_Poll` — both are fully correct today (confirmed by the post-restart export), nothing left to fix on them.

## Gmail connection (`galaxyaek7@gmail.com`) — not started, see `BLOCKERS.md` #1b

Deliberately not hand-built: none of the 5 existing workflows use an email node, so there's no real reference to verify a Gmail node's exact JSON schema against in this installation. Writing one blind risks an invalid or silently-broken node. Needs the account owner's OAuth consent in the browser regardless — see `BLOCKERS.md` #1b for the exact remaining steps.

## What was deliberately NOT built

No new workflows for the other requested "departments" (Customer Support, Backup, Security, Reporting, etc.) — see `ADR-037` for why: no real business logic exists behind most of them yet (zero customers, git already covers backup, `safety_filter.py` already runs in-process), so building empty shells for them would be example workflows by another name.

## n8n Integration Gap audit (ADR-06x, dated after ADR-045)

A full re-audit of every real workflow found the wiring already correct, with one exception: **the Production step of the factory pipeline had no n8n touchpoint at all.**

**Real workflow map today** (the 5th, "My workflow" — a Google Drive scratch workflow in the same instance — is not part of the factory and is excluded):

| Workflow | Trigger | Calls | Status |
|---|---|---|---|
| `Openclaw_Sensing_Engine` | Schedule (daily 8am) + Webhook (`scout-trigger`) | Google Trends RSS → `POST /api/trends` | Correct since before ADR-045 (never needed a fix); **proven live** — see evidence below |
| `01_Market_Scout` | Manual | `POST /api/scout/run` | Fixed by ADR-045 |
| `00_CEO` | Manual | `GET /api/dashboard` | Fixed by ADR-045 |
| `02_Sales_Poll` | Schedule (every 4h) | `POST /api/sales/poll` | Correct since before ADR-045 (never needed a fix) |
| `03_Production_Notify` (new, this audit) | Webhook (`production-notify`) | none (receives only) | **Prepared, not imported** — see below |

**Correction to `FACTORY_STATUS.md` §6:** that file's "Next Dollar Actions" claimed the Sensing Engine's HTTP node was still missing and `OPPORTUNITIES.md` "stays empty." Both were already false: `BLOCKERS.md` #1's own `ADR-045` note says Sensing Engine and `02_Sales_Poll` were "untouched, remain exactly as they were" when the other two were fixed — i.e. Sensing Engine needed no fix. Direct proof it fired for real: `OPPORTUNITIES.md` contains `[2026-07-15T06:40:04.543Z] what is a monsoon — نجحت كل فحوصات الجودة` — a timestamp format and exact reason string that only come from `server.js`'s `/api/trends` → `runQualityGate()` path (confirmed by grepping that exact string to its single source, `book_generator.py`'s `--quality-gate` reason). `GET /api/v1/automation-status` (Mission Control's Automation tab) now surfaces this same evidence (`trends_pipeline_evidence`), and reports on all 4 real workflows above, not just the 2 that have `.fixed.json` re-exports (the other 2 are read from `backups/pre_build_20260715_232343.json`, clearly labeled `source_kind: "backup_2026-07-15"` so it's never mistaken for a live re-check).

### `03_Production_Notify.prepared.json` — new, not yet imported

`server.js` now calls `notifyN8nProductionEvent()` after `start-production-pipeline` completes at least one real dossier — a plain, fire-and-forget `POST` of `{event, production_id, niche, generated_at, recommended_price, pre_production_checks_passed}` to `N8N_PRODUCTION_WEBHOOK_URL` (an env var; unset by default). With no URL configured it no-ops immediately — a real production run must never fail or block on n8n being unreachable or not yet wired up. Every attempt (skipped/succeeded/failed) is logged via the same `logServiceCall()`/`logs/service_layer.log` path every other service action uses.

**ADR-077 (Product Generation Pipeline) update, 2026-07-18:** `03_Production_Notify.prepared.json` now actually sends the Telegram Founder Report the pipeline's Requirements list calls for — same 3-node shape as `04_Telegram_Notify` (`Webhook` → `Set` "Build Telegram Message" → `HTTP Request` "Send Telegram Message" straight to Telegram's Bot API, reading `TELEGRAM_BOT_TOKEN`/`OPENCLAW_TELEGRAM_CHAT_ID` from n8n's own process `$env`, never embedded in this file). Before this it only logged the event into the workflow run (`Log Production Event`) — a real completed production dossier never reached the founder. Message includes the real `production_id` (Requirement #5's unique ID, threaded straight through from `production_factory/dossier.py`'s `make_production_id()`), niche, recommended price when known, and whether pre-production checks passed.

**This file is prepared, not imported** — unlike `00_CEO.fixed.json`/`01_Market_Scout.fixed.json`, it was never pushed into the live n8n database, because doing so needs the same stop-the-live-process step ADR-045/ADR-072 used, which requires the founder's explicit go-ahead each time, not a standing authorization (this codebase's own governance around touching the live n8n instance — see `CLAUDE.md` and the memory of the 2026-07-15 credentials blocker — treats this as deliberate, not an oversight). To activate:

1. Import `03_Production_Notify.prepared.json` into n8n — either via the UI's **Import from File**, or the same CLI path ADR-045/ADR-072 used (`n8n import:workflow --input=...` against a stopped instance).
2. Log into `http://localhost:5678`, open **03_Production_Notify**, toggle **Active** (same platform limitation ADR-072 hit: `--activeState=fromJson` fails outside queue/multi-main mode, so this step is genuinely UI-only).
3. Set `N8N_PRODUCTION_WEBHOOK_URL=http://localhost:5678/webhook/production-notify` in `.env`.
4. Restart `server.js` so it picks up the new env var.

Until all four steps are done, `start-production-pipeline` continues to work exactly as before (the notify call safely no-ops) — nothing about existing behavior changes by this file merely existing on disk.

## `04_Telegram_Notify.prepared.json` — imported and live, one click from fully active (`ADR-072`)

The mission's "nervous system" step: `factory_loop.js`'s Golden Hunter Bridge fires `notifyGoldenHunterAccepted()` (reusing `lib/n8n_notify.js`'s generic sender, same one `03_Production_Notify` uses) the moment a real opportunity clears `profit_oracle.py`'s acceptance gate — a plain `POST {event, niche, opportunity_score, reason, generated_at}` to `N8N_TELEGRAM_WEBHOOK_URL` (a new, separate env var from `N8N_PRODUCTION_WEBHOOK_URL` — different payload contract, different workflow). Unset means safe no-op; a real Golden Hunter tick must never fail or block on this.

This workflow is the receiving side: `Webhook` → `Set` (builds the message text) → `HTTP Request` node (calls Telegram's Bot API `sendMessage` directly, reading `TELEGRAM_BOT_TOKEN`/`OPENCLAW_TELEGRAM_CHAT_ID` from **n8n's own process environment** via `{{ $env.* }}` expressions — not an n8n Telegram credential, since this instance's UI/REST API wasn't reachable this session to create one; this also means neither value is ever committed to this repo or embedded in the workflow JSON).

**Done, 2026-07-18 (`ADR-072`), with the founder's real bot token:**
1. Founder generated a real bot via `@BotFather` (`@OpenClaw_Abdelkader_bot`) and gave the token directly.
2. Verified the token live (`getMe`), stored in `.env` as `TELEGRAM_BOT_TOKEN` (gitignored, never committed).
3. Real `chat_id` (`5236670532`) fetched via `getUpdates` after the founder messaged the bot — stored as `OPENCLAW_TELEGRAM_CHAT_ID`.
4. **A real test message was sent directly via Telegram's API and confirmed delivered** — proves the bot/chat channel itself works end-to-end, independent of n8n.
5. n8n's live database backed up (`n8n_workflows/backups/pre_telegram_activation_*.json`), then the updated workflow imported via CLI while n8n was offline (same safe pattern as `ADR-045`) — zero concurrent-write risk.
6. n8n started with `TELEGRAM_BOT_TOKEN`/`OPENCLAW_TELEGRAM_CHAT_ID`/`N8N_BLOCK_ENV_ACCESS_IN_NODE=false` in its process environment, confirmed healthy (`/healthz`).
7. `N8N_TELEGRAM_WEBHOOK_URL=http://localhost:5678/webhook/golden-hunter-notify` set in `.env`.

**Confirmed, directly from n8n itself, not assumed:** `n8n import:workflow --activeState=fromJson` fails outright in this instance's deployment mode ("can only be used when n8n is running in queue or multi-main mode"), and a POST to the production webhook URL returns n8n's own error: *"The workflow must be active for a production URL to run successfully. You can activate the workflow using the toggle in the top-right of the editor."* This is a genuine n8n platform limitation, not a permissions or effort gap — **only one manual step remains:**

1. Open `http://localhost:5678` (n8n is already running) → open **04_Telegram_Notify** → toggle **Active** (top-right).

That's it. The moment that toggle is on, `factory_loop.js`'s next real accepted opportunity sends a real Telegram message with zero further code changes — the whole chain from `TELEGRAM_BOT_TOKEN` through to a delivered message has already been built and independently verified piece by piece. Until that toggle is on, `notifyGoldenHunterAccepted()` still safely no-ops (webhook not registered → connection/404, logged, never blocks a real tick).
