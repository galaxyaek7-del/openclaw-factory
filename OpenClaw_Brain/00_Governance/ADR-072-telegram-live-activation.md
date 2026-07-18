# ADR-072 — Telegram Channel Activation: Real Token, Real Message, n8n One Click Away

**Date:** 2026-07-18
**Status:** Adopted. **The Telegram channel itself is verified live.** n8n's automated route is built, imported, and running — one manual UI click (a confirmed n8n platform limitation, not a permissions gap) from fully active.

---

## What happened

The founder provided a real Telegram bot token (`@OpenClaw_Abdelkader_bot`, created via `@BotFather`) and asked for the full chain to be activated: store it, get the chat_id, wire n8n, and prove a real message lands.

**First token given was invalid** (`401 Unauthorized` on `getMe`, confirmed byte-for-byte against what was pasted — not a transcription error on this end) — reported back rather than guessed around. The founder regenerated it via BotFather; the fresh token verified live on the first try.

## Real, verified steps

1. Verified with `getMe` before storing anything — `{"ok":true,"result":{"username":"OpenClaw_Abdelkader_bot",...}}`.
2. Stored `TELEGRAM_BOT_TOKEN` in `.env` (gitignored, confirmed not tracked by git before writing).
3. Fetched the real `chat_id` (`5236670532`) via `getUpdates`, after the founder sent the bot a message.
4. **Sent a real test message directly via Telegram's `sendMessage` API — delivered (HTTP 200, real `message_id`).** This alone satisfies the founder's own stated success bar ("a message reaching you from your bot = the first key worked") independent of n8n.
5. n8n was found **not running at all** in this session (no node process, port 5678 closed) — simpler and safer than the previously-documented "stop a live process" scenario: zero concurrent-write risk touching its database directly via CLI.
6. Backed up all 5 existing workflows (`n8n_workflows/backups/pre_telegram_activation_*.json`) before changing anything.
7. Rebuilt `04_Telegram_Notify.prepared.json`'s send step as a plain **HTTP Request** node calling `https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage?chat_id={{ $env.OPENCLAW_TELEGRAM_CHAT_ID }}&text=...` instead of an n8n Telegram credential — this instance's UI/REST API wasn't reachable this session to create a credential (still true, unchanged from `project_n8n_credentials_blocker_20260715`), and hand-crafting an encrypted credential blob via CLI was assessed as too fragile/risky for a live system's credential store to attempt blind. The `$env` approach keeps both values out of the workflow JSON entirely — nothing secret is ever committed to this repo.
8. Imported the workflow via `n8n import:workflow` (offline DB, same safe pattern as `ADR-045`) — verified directly via a read-only query against `database.sqlite` that the real node content (the exact HTTP Request URL expression) landed correctly, before ever starting the process.
9. Started n8n with `TELEGRAM_BOT_TOKEN` / `OPENCLAW_TELEGRAM_CHAT_ID` / `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` in its process environment — confirmed healthy (`/healthz` → `{"status":"ok"}`).
10. Set `N8N_TELEGRAM_WEBHOOK_URL=http://localhost:5678/webhook/golden-hunter-notify` in `.env`.

## The one remaining step — confirmed by n8n itself, not assumed

Tried `n8n import:workflow --activeState=fromJson` to activate it via CLI — **n8n itself refused**: `"The 'activeState=fromJson' flag can only be used when n8n is running in queue or multi-main mode. In regular deployment mode, workflow activation is not supported."` Then POSTed to the real production webhook URL to double-check — n8n's own 404 response states plainly: `"The workflow must be active for a production URL to run successfully. You can activate the workflow using the toggle in the top-right of the editor."`

This is n8n's own platform restriction on regular (non-clustered) deployments, re-confirmed live in this exact instance (n8n 2.25.7) — the same limitation `ADR-045`'s session already found, now doubly verified rather than assumed stale. **No CLI/API path activates a workflow in this deployment mode; it is a real, structural one-click requirement**, not a corner cut.

**Remaining action, for the founder only:** open `http://localhost:5678` (already running) → `04_Telegram_Notify` → toggle **Active**. After that, the next real accepted opportunity from `factory_loop.js`'s Golden Hunter Bridge sends a real Telegram message — zero further code changes.

## Impact

- `.env`: `TELEGRAM_BOT_TOKEN`, `OPENCLAW_TELEGRAM_CHAT_ID`, `N8N_TELEGRAM_WEBHOOK_URL` (all local, gitignored, never committed).
- `n8n_workflows/04_Telegram_Notify.prepared.json`: HTTP-Request-based send step (no credential dependency), imported live into n8n's real database.
- `n8n_workflows/backups/pre_telegram_activation_*.json`: real pre-change backup of all 5 workflows.
- `n8n_workflows/README.md`: updated to reflect what's actually done vs. the one real remaining step.
- No code in `factory_loop.js`/`lib/n8n_notify.js` needed to change — the wiring built in `ADR-065`/`ADR-067` already targeted exactly this webhook contract.
