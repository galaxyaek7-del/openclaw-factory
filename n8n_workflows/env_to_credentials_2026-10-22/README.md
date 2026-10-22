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

## Change record (applied 2026-10-22 ~11:30 UTC, founder-approved)

**Pre-change state.** Read-only DB copy, 2026-10-22 ~10:50 UTC:
- Sales_Poll: 64 runs, 64 errors. Sensing: 11/11. Telegram_Notify: 6/6.
  Production_Notify: 1/1. Market_Scout: 0 runs.
- Last error on all of them: `access to env vars denied`.

**Applied.** `apply_fix.py`:
- 1 credential: `GFinternalTokn01` (HTTP Header Auth).
- 3 workflows imported and published: 01_Market_Scout, 02_Sales_Poll,
  Openclaw_Sensing_Engine.
- The Telegram credential and the 2 Telegram workflows were **not** applied.
  `OPENCLAW_TELEGRAM_CHAT_ID` is unset, so they are unchanged and still failing.
- Backup: `C:\Users\Dell\.n8n\backup_gf_envfix_20261022_123022`.

**Verified after the change: static only, no real execution yet**
- n8n `/healthz` returns 200 after restart.
- The 3 workflows are active, updatedAt 11:31 UTC. The 4 demos are still
  active.
- The stored credential value equals `.env`'s `INTERNAL_SERVICE_TOKEN`. This
  was compared by SHA-256 prefix; the value was never printed.

**NOT yet verified**
- That any of the 3 workflows now **executes successfully**. No run has
  happened since the change: Sales_Poll fires every 4 h and Sensing daily at
  07:00 UTC. Market_Scout is manual-only and was not run, because it triggers
  the full scout pipeline.
- Check with `python scripts/n8n_workflow_health.py`. A workflow is OK only
  when it shows a fresh successful run *and* `server.js` returned
  `{"success": true}`.

**Secrets handling disclosure (control D)**
- `apply_fix.py` wrote the credential JSON (plaintext) to a private temp
  directory for the n8n CLI import, and deleted it in a `finally` block.
  Deletion was confirmed.
- The post-change hash comparison exported the decrypted credential to a temp
  directory, which was then deleted. Deletion was confirmed.
- No secret was printed, logged or committed.
- Future runs should avoid both: compare via the CLI without writing a file,
  or ask first.

**Rollback**
`python n8n_workflows/env_to_credentials_2026-10-22/apply_fix.py --rollback C:\Users\Dell\.n8n\backup_gf_envfix_20261022_123022`
stops n8n by exact PID, restores the three DB files from the backup, and
restarts n8n through the scheduled task. Rolling back returns the workflows to
their pre-change, always-failing state.

## Follow-up (2026-10-22 15:11 UTC): first real run after the fix

`scripts/n8n_workflow_health.py` read the first scheduled run after the
credential change (Sales_Poll, execution 191, 15:00 UTC). The `$env` error is
gone. The run still failed, with a different error: `ECONNREFUSED` to `::1`.
n8n resolves `localhost` to IPv6 first, and `server.js` listens on
`127.0.0.1:3000` only (confirmed with `Get-NetTCPConnection`). The env error
had been masking this one.

**Prepared, not applied.** The three `server.js` calls in this folder now use
`http://127.0.0.1:3000`. Isolated proof, run in a separate n8n user folder with
a fake credential against the real server:
- the exact fixed node reached `server.js` and got `401 unauthenticated`, so no
  business operation ran;
- the same node with `localhost` failed with a connection refusal, like the
  live run.

Applying it means re-importing 3 workflows and restarting n8n with
`apply_fix.py`. That needs owner authorization.

## Webhook authentication (prepared 2026-10-22 ~16:00 UTC, not applied)

**Found.** With n8n exposed through ngrok, three company webhooks accepted any
caller:
- `golden-hunter-notify` and `production-notify` are wired straight to
  Telegram sending. Once a chat id is configured, anyone could message the
  founder through the factory's own bot.
- `scout-trigger` was an orphan node, so it started empty runs only. It was
  also the endpoint `server.js`'s Scout pipeline calls to fetch trends, which
  therefore did nothing.

A GET probe from outside confirmed the exposure, and it also started one empty
Sensing run (execution 192). That run stopped at the Webhook node, and nothing
reached `server.js`.

**Prepared, in this folder and in the code:**
- All three webhook nodes require HTTP Header Auth (`X-GF-Webhook-Secret`,
  credential `GFwebhookSecr01`).
- The Sensing webhook is connected to the trends flow.
- `lib/n8n_notify.js` and `server.js` (`triggerN8nTrends`) send the header when
  `N8N_WEBHOOK_SECRET` is set. Unset means no header, exactly as before.

**Isolated proof**, run on a separate n8n instance with fake credentials on
127.0.0.1:58178:

| Request | Result |
|---|---|
| no header | 403 |
| wrong header | 403 |
| correct header | 200 |

**To apply (owner authorization needed):**
1. Generate a secret into `.env` as `N8N_WEBHOOK_SECRET`.
2. Import credential `GFwebhookSecr01`.
3. Re-import Sensing now. Re-import the two Telegram workflows *together with*
   the chat id, and never configure the chat id before this, or the open
   webhooks become live.
4. Restart `server.js` and `factory_loop.js` so they load the secret.

### Applied 2026-10-22 15:53–15:58 UTC (owner-approved)

- `.env` was backed up to `.env.bak-20261022_165323`, which is gitignored and
  holds secrets. Then a random 48-hex-character `N8N_WEBHOOK_SECRET` was
  appended. The value was never printed.
- n8n was backed up to `~/.n8n/backup_gf_envfix_20261022_165323`. Credential
  `GFwebhookSecr01` was imported. Its plaintext temp file was deleted and
  confirmed gone. Openclaw_Sensing_Engine (with webhook auth and the wired
  webhook) was imported and published, and n8n restarted.
- `server.js` (PID 14608 → 3792) and `factory_loop.js` (PID 18396 → 4160) were
  restarted by exact PID between ticks, and respawned by their supervisors.
  factory_loop reported "nothing was in flight".

**Verified**
- External GET `/webhook/scout-trigger`: no secret returns 403; a wrong
  secret returns 403.
- `GET /health` now reports `sensing_engine` from execution evidence:
  `ok:false`, Sales_Poll=FAILING, Sensing=UNKNOWN. Before the change it read
  `ok:true`.

**Not verified**
- Whether the restarted `server.js` loaded `N8N_WEBHOOK_SECRET`. Its startup
  line reads `injected env (0) from .env`. A clean simulation of the same
  situation reports 1, and the cause of the difference is UNKNOWN. The first
  real Scout run decides it: it should create a Sensing execution in mode
  `webhook`, and a 403 means the secret is missing. Either way nothing that
  worked before is lost, because that call did nothing while the node was
  orphaned.
- The Telegram webhooks are still open but cannot send while there is no chat
  id. Protect them together with the chat id, never after it.

**Rollback**
1. Restore `.env.bak-20261022_165323` over `.env`.
2. Run `python n8n_workflows/env_to_credentials_2026-10-22/apply_fix.py --rollback C:\Users\Dell\.n8n\backup_gf_envfix_20261022_165323`.
3. Restart `server.js` and `factory_loop.js`: stop each by exact PID, and its
   supervisor respawns it.
