# n8n engineering review — Cycle 95 (2026-10-17)

**Status:** review and design only. Nothing on the live n8n instance was changed: no import, no activation, no credential, no restart, no tunnel change.

**Evidence:**
- `python scripts/n8n_exposure_audit.py --db <copy of ~/.n8n/database.sqlite>`. The audit only ever reads a copy of the database, opened `mode=ro&immutable=1`.
- `tests/test_n8n_exposure_audit.py`: 10 tests, using fixtures only.

## 1. What we found (OBSERVED)

### 1a. No factory alert currently reaches the founder

This is the most serious finding. There are two alert paths, and both are broken.

| Path | Used by | Status | Evidence |
|---|---|---|---|
| Direct Telegram (`lib/telegram_direct.js`, `channels/telegram_direct.py`) | critical errors, resilience incidents, supervisor crash alerts | **Skipped on every call** | `OPENCLAW_TELEGRAM_CHAT_ID` is absent from `.env` and from the Process, User and Machine environments. `TELEGRAM_BOT_TOKEN` is present. The sender returns `"not configured"` without sending. |
| n8n relay (`lib/n8n_notify.js` → `04_Telegram_Notify` / `03_Production_Notify`) | **new sale detected**, Golden Hunter accepted, factory stopped/recovered, retry-queue status | **Acknowledged, then fails inside n8n** | Both workflows read `$env.TELEGRAM_BOT_TOKEN`, which is blocked by default (ENV_ACCESS_DENIED). |

The n8n webhooks reply HTTP 200 as soon as they receive a request, before the workflow runs. The factory therefore logs `succeeded` for messages that were never delivered.

A recorded instance:
- On 2026-10-10 at 19:37:11, `factory_loop` logged `recovery_notify … succeeded, status 200`.
- In the same second, n8n recorded two `04_Telegram_Notify` executions with status `error`.

**Consequence:** a first real sale would currently produce **no** alert.

### 1b. Public entry points on the active instance

The tunnel forwards the whole n8n port (editor plus webhooks) to the internet. It has been running since 2026-10-14. Its URL is deliberately not recorded in this repo.

| Active workflow | Entry point | Severity | Risk |
|---|---|---|---|
| RE_Broker / Umrah_Agency / Dental_Clinic `_Assistant_Demo` | public hosted chat (`public: true`, no auth) → Groq agent `openai/gpt-oss-120b` | HIGH | Anyone with the URL spends the founder's Groq quota. An unsupervised LLM speaks for the company. Last used 2026-10-13 (38 executions in total). |
| `03_Production_Notify` | `POST /webhook/production-notify`, no auth | HIGH | Once its Telegram send works, anyone could push fake "product ready" alerts to the founder. |
| `04_Telegram_Notify` | `POST /webhook/golden-hunter-notify`, no auth | HIGH | Same as above, but for fake sale, accept or recovery alerts. |
| `Openclaw_Sensing_Engine` | `GET /webhook/scout-trigger`, no auth | HIGH (low impact) | An **orphan** node: connected to nothing, so it only registers a public URL. |

No inline secrets were found in any definition or in the database (INLINE_SECRET: 0).

### 1c. Design-level faults
- **`$env` in 5 active nodes** (01, 02, 03, 04, Sensing): 46 of 51 recorded errors are ENV_ACCESS_DENIED. The Cycle 97 README has the details.
- **GF-OPS set (5 workflows):** all of them depend on `executeCommand`, which n8n 2.x disables. The parallel session has already marked them `SUPERSEDED_BY_FACTORY_LOOP_TICK`, which is the correct outcome. They must not be revived by setting `NODES_EXCLUDE=[]`.

## 2. Engineering principles (proposed standard)

1. **n8n is a transport, never a decision centre.** The factory (`factory_loop.js` / `server.js`) decides, schedules and records; n8n may only fetch, relay or notify.
2. **Alerts must not depend on n8n.** Founder alerts go out on the direct Telegram path, which has a real delivery receipt (`message_id`). n8n can be a secondary path at most, because a 200 from a webhook is an acknowledgement, not a delivery.
3. **Every webhook is authenticated.** Use Header Auth with an n8n credential, or don't have the webhook. Remove a webhook that has no consumer.
4. **No `$env`, no `executeCommand`, no inline secrets.** Secrets live in n8n credentials only. Local jobs run in the `factory_loop` tick, not in shell nodes.
5. **Public exposure is opt-in per path.** The tunnel should forward `/webhook/*` only, or nothing. The editor must never be public.
6. **No public LLM endpoints** without auth, rate limiting and an owner. Demos are run on demand and switched off afterwards.
7. **Gate:** `scripts/n8n_exposure_audit.py` must report `active_high = 0` before any n8n change is called done.

## 3. Proposed fix, in order (each step needs the founder's action or authorization)

| # | Action | Who | Effect | Rollback |
|---|---|---|---|---|
| 1 | Add `OPENCLAW_TELEGRAM_CHAT_ID=<your chat id>` to `.env`, then restart `server.js` and `factory_loop` by exact PID (through the supervisor) | **founder** (we do not edit `.env`) | Restores every direct alert. Verify with one test message from `lib/telegram_direct.js`. | Remove the line. |
| 2 | **Code done (Cycle 95):** `lib/founder_alert.js` makes `notifyFactoryRecoveryEvent` / `notifyGoldenHunterAccepted` try direct Telegram first, falling back to n8n only when direct fails, and reports an n8n 200 as `unconfirmed`. Takes effect on the next `factory_loop` restart, and **only delivers once step 1 is done**. The founder can then unset the two `N8N_*_WEBHOOK_URL` vars and deactivate 03/04 | Claude (code + tests); founder (restart, env, deactivation) | Sale/recovery alerts get a real delivery receipt; no duplicate (n8n is skipped when direct succeeds) | Revert the commit |
| 3 | Deactivate the 3 `*_Assistant_Demo` workflows, or give each chat basic auth | founder authorization | Closes the public Groq spend and reputation risk. | Re-activate. |
| 4 | Restrict the tunnel to `/webhook/*`, or stop it (exact PID). The editor must never be exposed. | founder authorization | Removes the public editor surface. | Restart the tunnel. |
| 5 | Remove the orphan `scout-trigger` webhook from `Openclaw_Sensing_Engine` | founder authorization (it is a live edit) | One less public URL. | Re-import the backup. |
| 6 | Apply the Cycle 97 Header Auth credential fix to 01/02/Sensing (`n8n_workflows/cycle97_credential_fix/`) | founder (creates the credential in the UI, authorizes the restart) | Ends the ENV_ACCESS_DENIED errors on the read-only pollers. | Restore the DB backup. |
| 7 | Re-run `python scripts/n8n_exposure_audit.py --db <fresh copy>` | Claude | Expect `active_high: 0` and `direct_telegram_ready: true`. | — |

**Order matters.** Step 1 comes first: it has no dependency on n8n at all, and it restores alerting today.

## 4. What we will not do
- Set `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` or `NODES_EXCLUDE=[]`. Both are process-wide security relaxations.
- Add auth to 03/04 but keep them as the alert path. That would still not give a delivery receipt.
- Edit `.env`, the n8n database, credentials or the tunnel without explicit, action-specific authorization.
