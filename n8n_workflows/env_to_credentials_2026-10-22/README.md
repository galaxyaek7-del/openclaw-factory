# n8n fix: `$env` → encrypted credentials (2026-10-22)

## What was wrong (OBSERVED, read-only copy of `~/.n8n/database.sqlite`)

Every company workflow on the live n8n (2.25.7) was failing, every run:

| Workflow | Runs | Errors | Failing node | Error |
|---|---|---|---|---|
| 02_Sales_Poll (every 4 h) | 64 | 64 | Poll Sales (server.js Brain) | `access to env vars denied` |
| Openclaw_Sensing_Engine (daily) | 11 | 11 | HTTP Request1 (9), HTTP Request (2) | `access to env vars denied`; 2× connection error |
| 04_Telegram_Notify | 6 | 6 | Send Telegram Message | `access to env vars denied` |
| 03_Production_Notify | 1 | 1 | Send Telegram Message | `access to env vars denied` |
| 01_Market_Scout | 0 | — | manual trigger only | would fail the same way |

The errors run from 2026-10-10 to today. Only the demo workflows succeed.

**Cause.** n8n 2.x blocks `$env` in node expressions by default, and every
company workflow read its secrets through `$env.INTERNAL_SERVICE_TOKEN`,
`$env.TELEGRAM_BOT_TOKEN` or `$env.OPENCLAW_TELEGRAM_CHAT_ID`. Unblocking it
would not have helped. `start-n8n.cmd` passes n8n only the user-level variables
(`N8N_EDITOR_BASE_URL`, `N8N_LISTEN_ADDRESS`, `N8N_PROXY_HOPS`), and n8n does
not read the repo's `.env`, so those variables were empty inside n8n anyway.
Unblocking `$env` would also weaken a default security control on an instance
exposed through ngrok.

**Related gaps found on the way**
- `OPENCLAW_TELEGRAM_CHAT_ID` is not set anywhere, neither `.env` nor the user
  environment. `factory_loop.log` records "TELEGRAM_BOT_TOKEN or
  OPENCLAW_TELEGRAM_CHAT_ID not configured", so the factory's direct Telegram
  alerts (`lib/telegram_direct.js`) are not reaching the founder either.
- The factory health check reports `sensing_engine` OK because n8n answers on
  port 5678, even though every run of that workflow fails. That is a false
  green.
- The Google Trends URL in Openclaw_Sensing_Engine ended in a stray newline.
- Five `GF-*.json` workflows in `n8n_workflows/` were never imported into the
  instance.

## The fix (files in this folder)

`build_fixed.py` turned the live definitions into the five JSON files here.
They contain **no secrets**: a scan of every `.env` value of 12+ characters
found none.

- The three calls to `server.js` (Sales_Poll, Sensing, Market_Scout) use an
  **HTTP Header Auth credential** (`GFinternalTokn01`, header
  `X-Internal-Token`) instead of a `$env` expression.
- The two Telegram workflows use n8n's **Telegram node** with a **Telegram
  credential** (`GFtelegramBot001`). The bot token is no longer placed in a URL.
  The chat id is the placeholder `__GF_TELEGRAM_CHAT_ID__`, which the apply
  step fills.
- The Sensing Trends URL is trimmed.
- Workflow ids, webhook nodes, triggers and connections are unchanged.

## Verified before touching the live instance

The steps below ran in a **separate, empty n8n user folder** with fake secrets,
never against the live database:

1. `import:credentials`: both stored encrypted (`U2FsdGVkX1…`), and decrypt back to
   the input values.
2. `import:workflow --separate`: 5 imported, ids preserved.
3. `publish:workflow`: all 5 active with an active version.
4. Runtime: the exact fixed Sales_Poll HTTP node, pointed at a local echo
   server, executed successfully. The echo server received
   `X-Internal-Token: FAKE-DRYRUN-TOKEN`, read from the encrypted credential.

The Telegram node was not executed, because that would call Telegram for real.

## Applying it (needs founder approval)

`python apply_fix.py` does the following, in order:

1. Backs up `~/.n8n/database.sqlite*`.
2. Stops only the exact PID of `n8n start`.
3. Imports the credentials from a temp file that is deleted in a `finally` block.
4. Imports and publishes the workflows.
5. Restarts n8n through the `GalaxyForge-N8N-Autostart` scheduled task.

The Telegram workflows are **skipped** until `OPENCLAW_TELEGRAM_CHAT_ID` is
set. To roll back, run `python apply_fix.py --rollback <backup dir>`; the
script prints that command.
