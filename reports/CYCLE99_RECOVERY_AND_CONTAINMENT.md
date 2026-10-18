# Cycle 99: recovery, containment, commercial status (2026-10-18)

Evidence classes: **OBSERVED** (seen directly this cycle), **DERIVED** (computed from observed data), **INFERRED** (reasoned, not tested), **UNKNOWN**.

## 1. The three public n8n demos: contained? **No, HOLD (not authorized)**

| Workflow (id) | Active | Chat trigger | External GET via tunnel | Nodes |
|---|---|---|---|---|
| RE_Broker_Assistant_Demo (`NvUd7vq2Cmc14nay`) | yes | public, auth none | 200 | chatTrigger → agent → Groq `openai/gpt-oss-120b` + memory |
| Umrah_Agency_Assistant_Demo (`RGMC3TXuMWvpXfKf`) | yes | public, auth none | 200 | same |
| Dental_Clinic_Assistant_Demo (`FfICkTFh1tMBIMxy`) | yes | public, auth none | 200 | same |

**What was observed:**
- **OBSERVED: reachable from the internet.** All three chat pages answer 200 through the public tunnel. That check was a page GET only; no message was sent, so no Groq call was made.
- **INFERRED: any visitor can spend the Groq key.** Each message a visitor sends runs the Groq model on the founder's credential. Nothing else is reachable: no tool nodes, no HTTP nodes, no file access.
- **OBSERVED: the editor itself is protected.** The editor API (`/rest/workflows`) answers 401 externally.
- **OBSERVED: recorded use so far.**
  - 38 executions in total, the last on 2026-10-13.
  - The tunnel itself has been running since 2026-10-14.

**Not done:** no deactivation and no workflow edit. The founder has recommended STOP DEMOS but has not authorized it, and no n8n API key exists, so deactivating means either an editor click or a CLI change plus an n8n restart.

## 2. Founder alerts: **UNVERIFIED (no chat id yet)**

**OBSERVED: configuration.**
- `OPENCLAW_TELEGRAM_CHAT_ID` is missing; `TELEGRAM_BOT_TOKEN` is present.
- The direct path therefore skips every message.
- The n8n relay acknowledges with 200 but cannot send: workflow 04 reads `$env`, which is blocked.

**Code (`lib/founder_alert.js`):**
- tries the direct path first;
- reports an n8n 200 as `unconfirmed`, never as delivered.

## 3. Financial data integrity

| Writer | Behaviour | Status |
|---|---|---|
| `server.js` saveFin | Atomic temp-file + rename. Skips the write if nothing changed. | OBSERVED, safe |
| `channels/ledger.py` reconcile | Atomic `os.replace`. Finance is derived from the append-only `sales_ledger.jsonl`. | OBSERVED, safe |
| `factory_loop.js` `healFinance()` | **Root cause found.** `/health` marks finance not-ok on any read error, including a transient Windows lock, not only on corrupt JSON. healFinance then wrote an empty file over the real one, keeping only a `.bak`. | **Fixed, commit `7f26b4d`:** re-checks first. Parses → untouched. Unreadable → skipped. Only real corruption is quarantined, with an atomic write. 5 temp-file tests. |
| `scripts/security_resilience_audit.js` (parallel session, gitignored) | **Root cause of the "6-hour overwrite".** At its end it wrote its start-of-run snapshot back over `finance_data.json`, `config/reality.json` and `sales_ledger.jsonl`. A real sale recorded during the run would be erased. | **Fixed locally:** the ledger is never rewritten. A JSON file is restored only when `lastUpdated` is the only change; anything else is kept and reported HIGH. Verified in a temp sandbox: 3/3 cases. Original kept in `backups/rejected_parallel_changes_2026-10-17/`. The script stays rejected and gitignored. |

`lib/contact_tracker.js` was not modified. It is append-only and dedupes by contact id, but it belongs to an unreviewed auto-reply system and stores customer names in a file git does not ignore.

The real `finance_data.json` and `sales_ledger.jsonl` were compared byte-for-byte before and after every test run in this cycle: **unchanged**.

## 4. Paddle 429 → `/api/sales/poll` 504

- **Root cause (OBSERVED, 2026-10-18):**
  - Paddle answers 429 (a Cloudflare HTML page) with `Retry-After: 30`.
  - The retries were unbounded, about 61 s in total.
  - The route kills the script at 45 s, so the Gumroad result was lost as well.
- **Fix (`b9e7973`):**
  - a 20 s total budget for the Paddle sales read;
  - each attempt's timeout is capped to the time remaining.
- **Local measurements:**
  - script: 61 s → about 1 s;
  - `POST /api/sales/poll` contract test (needs a session or the internal token, never neither): passes in 5.3 s.
- **Tests (`9f59ae6`):**
  - the budget stops a 30 s Retry-After;
  - the per-attempt timeout is capped;
  - a short Retry-After still retries;
  - with no budget, the original behaviour is unchanged;
  - network failures retry within the budget;
  - a 429 surfaces as a truthful `RuntimeError`;
  - a Gumroad sale is recorded while Paddle returns 429.
- **Results:** `test_paddle_arm` 50/50, `test_sales_poll` 9/9.
- **Not verified in production.** There is no deployed endpoint. Paddle itself is still rate-limiting us (UNKNOWN why).

## 5. Release: 7 local commits on `main`, not pushed

| Hash | Content |
|---|---|
| 3bffa02 | Reports only (parallel session): B12 draft guide, re-upload reconciliation |
| 641ee2d | Site: 3 cards removed from products.html, one stale link removed |
| 19cb415 | n8n exposure audit, tests, review |
| b0269c6 | lib/founder_alert.js, plus 2 call sites in factory_loop.js |
| b9e7973 | Paddle retry budget, Paddle tests, .gitignore for 2 rejected files |
| 7f26b4d | healFinance re-check, plus test |
| 9f59ae6 | More Paddle and sales-poll tests |

**Checks on these commits:**
- 17 files changed.
- Secret scan: the only hit is the detection regex itself.
- No data files, `.env`, customer records or financial records are included.
- `factory_loop.js` carries only these hunks. The parallel session's 77 uncommitted lines are excluded.

**Pushing deploys** the `customer_site` changes on GitHub Pages (INFERRED from the site's canonical URLs).

## 6. B12-001

- **OBSERVED:** the artifact sha256 matches the packet (`aee8fc0b…092d`, 8,922 B).
- **OBSERVED, read-only Gumroad query:** no listing with this name exists among 79 listings (76 published).
- **OBSERVED:** the site page says "$14.99 (planned)", "DRAFT, not yet listed".
- **Shortest path to a first sale:**
  1. The founder creates the unpublished draft by hand (`DRAFT_NOW_CYCLE95.md`).
  2. Review.
  3. `APPROVE B12-001 PUBLISH`, then the founder publishes by hand.
  4. Read the public page.
  5. Read sales.
- **A sale counts only** when a completed Gumroad sale is seen through a read of the API.

## 7. Tests (OBSERVED, 2026-10-18)

The CI-equivalent run uses a clean `git archive HEAD` extract, so the parallel session's uncommitted files are excluded.

- **Python, 8 CI groups (`scripts/run_python_group.py --pattern …`): 5,233 tests.** 3 problems in the extract:
  - `test_audit_requirements` and `test_snapshot` need a `.git` directory. In the real repo: 4/4 and 9/9 OK.
  - `test_phase4_integration.test_governance_unchanged` pins the sha256 of `server.js` from an earlier sprint. This branch does not touch `server.js`, which is identical to `origin/main`, so the failure is pre-existing there and not caused by these commits.
- **JS, every CI `run_js_group.js` step: 461 pass.**
  - `test_restore_file_from_git.js` needs `.git`; in the real repo it passes 8/8.
- **Targeted tests:**
  - `test_paddle_arm` 50/50;
  - `test_sales_poll` 9/9;
  - `test_n8n_exposure_audit` 10/10;
  - founder alerts + heal finance + n8n notify + pending retries + attribution: 48/48.
- **Working-tree only (not CI): 11 failures in `test_backup_*`.** These are untracked tests from the parallel session. They pin hashes of the live `finance_data.json`, `sales_ledger.jsonl` and `reality.json`, which legitimately change.
