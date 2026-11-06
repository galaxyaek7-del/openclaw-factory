# STABILITY_REPORT.md: Galaxy Forge factory, Phase 1 (inspect and record only)

Date: 2026-11-06 ~17:20 UTC. Nothing was fixed in this phase. Every line below comes from a live check run today; where a check could not be made the label is UNKNOWN.
Key values were never printed: only variable names and yes/no results.

## 1. Verdict in one paragraph
The factory is **running and healthy at the process level**: server, factory loop (under the supervisor) and n8n are up, 0 server crashes since 2026-10-25 (all 148 log lines are the deliberate crash tests), 37 of 37 probed routes answer 200/302/401 with no 5xx and none slower than 5 s, CI on GitHub is green, disk has 133 GB free, the nightly regression gate is 392 Python + 7 Node files green. The real risks are not crashes: they are **single-copy of the work on this machine (100 commits not on any remote)**, **one relay workflow failing**, **one key invalid (Paddle)**, **a bot token that appeared once in a log and should be rotated**, and **an auto-restart-after-reboot that is configured but has never been proven live**.

## 2. Problems ordered by severity

### URGENT (act soon; most need the founder)
| # | Problem | Evidence | Owner |
|---|---|---|---|
| U1 | **Telegram bot token was written once into `factory_loop.log` (25 times) by a crash trace; log was scrubbed (0 left) but the token existed in clear text.** Rotation is the only certain fix. | scrub verified 2026-11-06; token still the same | Founder (rotate in BotFather), then agent reruns `apply_telegram_only.py` |
| U2 | **No off-machine copy of the code history: local `main` is 100 commits ahead of `origin/main`.** Only site files are published (by design: public repo must not carry paid files). A disk failure loses 100 commits and all `data/`. Remote has 1 branch (`main`). | `git rev-list --count origin/main..main` = 100; `ls-remote --heads` = 1 | Agent can propose a private backup path; founder decides where (any off-site storage is outside the workspace) |

### MEDIUM
| # | Problem | Evidence |
|---|---|---|
| M1 | `n8n:03_Production_Notify` is FAILING (1 run, 1 error: connection timed out). Notification relay for production events. | `connection_verifier.py` |
| M2 | **Paddle API key lacks permission** (HTTP 403 on read). Payment gateway for the customer platform cannot be read; waits on the founder's Paddle onboarding. | `connection_verifier.py` |
| M3 | **Auto-restart after reboot configured but never proven live.** `GalaxyForge-Factory-Autostart` (logon trigger, runs `scripts/start_factory_supervised.ps1`, has duplicate guards) last ran 2026-11-05 with result 0; `GalaxyForge-N8N-Autostart` is running; `GalaxyForge-Ngrok-Autostart` last result `0xC000013A` (terminated), state Ready. A real reboot test has not been done: **UNKNOWN**. | Task Scheduler |
| M4 | Working tree carries **1,779 modified/untracked files** unrelated to my commits (generated reports, site pages, manifests). High risk of a mistaken commit; hides real changes. | `git status --short` |
| M5 | Groq rate limit (HTTP 429) appears during bursts (seen twice today in my evaluation scripts). **Already handled**: `groq_chat` retries with a growing delay (`_retry_delay_seconds`); my evaluation scripts have their own spaced retries. Corrected after reading the code. | eval runs 17:12Z |
| M6 | Internet from this host is intermittent (earlier today: 368 of 777 health ticks with a target down; 4-hour outage 03:00-07:00Z). GitHub fetch and n8n relays fail during outages. | health history |
| M7 | Scout (76% task success) and QA (68%) are flagged DEGRADED by the agent KPIs: stale history (old book-prompt era). The fixes made today (Scout v2, matched QA, mission prompt) have **no measured result yet** (needs several daily chains). | `agent_kpis.py` |

### MINOR
| # | Problem | Evidence |
|---|---|---|
| L1 | 10 historical JSON files do not parse (9 old cycle records such as `data/c102_execution_record.json`, one with a UTF-8 BOM, one UTF-16); 4 JSONL files have bad lines (`product_analysis_v57.jsonl` 232, `proposal_pipeline.jsonl` 97, 2 files 1 line each). **No live code reads them** (grep). Not deleted. | integrity scan of 906 files |
| L2 | `data/commission_attribution_log.jsonl` is 108 MB (one legacy day) and `data/attribution_log.jsonl` 24 MB; `factory_loop.log` 9 MB. No rotation. Disk is not at risk (133 GB free). | `ls` |
| L3 | `n8n:01_Market_Scout` is manual-only and never ran (UNKNOWN by design). | verifier |
| L4 | `.env` has no `PORT` (default 3000 applies), no `AFFILIATE_MODE`, no `AMAZON_ASSOCIATE_TAG` (founder item). 33 variables, none empty. | name check |
| L5 | `/health` returns `status: warning` while 9 of 12 checks are ok: the other 3 are `not_applicable` (no database, queue or worker pool by design). The warning is cosmetic, but it hides a real warning if one appears. | `/health` |
| L6 | Backup branches (`backup/pre-13c`, `backup/pre-14`, ...) and `pre-*` branches clutter the local repo (local only, not on the remote). | `git branch -a` |

## 3. Status of every tool and service
| Component | State |
|---|---|
| `server.js` (127.0.0.1:3000) | **RUNS** (pid 18872), `/health` 200 (`warning` cosmetic), 0 real crashes; supervisor present |
| `factory_loop.js` | **RUNS** under supervisor (pid 19676), 148 ticks/24 h, 0 failed steps now (25 `telegram_bind` failures earlier, recovered) |
| `scripts/supervisor.js` | RUNS (2 instances: server and loop) |
| n8n | **RUNS** (autostart task running) |
| n8n `02_Sales_Poll`, `Openclaw_Sensing_Engine`, `04_Telegram_Notify` | OK (the last had 28 historic errors, now succeeding) |
| n8n `03_Production_Notify` | **FAILING** (M1) |
| n8n `01_Market_Scout` | manual-only, never run (UNKNOWN) |
| Gumroad API | **OK**, read of 125 products; writes gated; rolling window 10/10 full until ~17:18Z |
| Groq (LLM) | **OK** (last call ok, ~1.1 s); 429 under bursts (M5) |
| Telegram | **OK** (token valid, chat bound); rotation recommended (U1) |
| Paddle | **BROKEN: 403** (M2, founder onboarding) |
| Metricool (Claude connector) | works inside a session only (FREE plan: no review flow) |
| Pinterest | 14 pins scheduled (verified on profile); board exists |
| X, LinkedIn, Instagram, YouTube, Amazon Associates | NOT CONNECTED (credentials or spend needed: founder) |
| Ngrok autostart | NOT RUNNING (last exit 0xC000013A); not required by the loop (UNKNOWN whether any webhook relies on it) |
| Analytics receiver for the site (141 pages) | NOT BUILT (traffic UNKNOWN) |
| Database | **none by design** (flat JSON/JSONL). Integrity: 896 of 906 files parse; see L1 |
| Public site (GitHub Pages) | deployed, CI success on `cbffbc0` |

## 4. GitHub
- CI on the last pushed commit `cbffbc0` (2026-11-06): **PASS**, 36 of 36 jobs, Pages build success.
- The earlier red CI (`34d009d3`) was a missing `customer_site/catalog.json`; fixed and pushed, cleared.
- Remote branches: only `main`. Local-only branches: backups and `factory/2026-10-29-reconstruction`.
- Unpublished: 100 commits (non-site files, deliberately not pushed). `site_files_differ` = 0: the public site matches local.
- Failed commits on the remote now: none.

## 5. Links and API keys
| Key / link | Status |
|---|---|
| `GROQ_KEY` | valid (live call ok) |
| `GUMROAD_ACCESS_TOKEN` | valid (125 products read) |
| Telegram bot token + `OPENCLAW_TELEGRAM_CHAT_ID` | valid; rotation advised (U1) |
| `MISSION_CONTROL_PASSWORD`, `INTERNAL_SERVICE_TOKEN`, `FACTORY_LIVE_PUBLISH`, `N8N_PRODUCTION_WEBHOOK_URL` | present (validity of the first two not separately probed: UNKNOWN) |
| Paddle key | present but **lacks permission (403)** |
| `AMAZON_ASSOCIATE_TAG`, X credit/keys, YouTube OAuth, Etsy | **missing / not configured** |
| Tracked-secret scan (git grep for key-shaped strings) | **clean** (1 hit = a comment in the scanner's own source) |
| Public product links (117 listings) | listing-health guard today: 0 findings (corrupted text, price 0, duplicates, covers) |
| Sampled pin links/images (5 of batch 3) | all HTTP 200 |

## 6. Disk and data
- C: 133.0 GB free of 237.4 GB (56% free). No pressure. (A 127 GB `opencode.db` was a known earlier cause of fill; OpenCode is stopped.)
- Largest factory files: `commission_attribution_log.jsonl` 108 MB, `attribution_log.jsonl` 24 MB, `decisions.jsonl` 17 MB.
- Database: none. JSON/JSONL integrity 896/906 parse (L1). Daily local data backup exists but is **on the same disk** (U2).

## 7. Tests
- Nightly regression gate (2026-11-06 15:02Z): Python 392 passed, 0 failed (32 files); Node 7 of 7 files. Files added since (research chain daily, bundle builder, KPI window, scout/mission) are green when run individually but not yet in a nightly record.
- The full test suite is deliberately not run at once (memory use).

## 8. What Phase 2 should do (proposed order, per your order: infrastructure first)
1. **Infrastructure:** (a) prove auto-restart: dry-run the autostart script and review its guards; do a controlled process-kill restart test of the supervisor; (b) make `/health` distinguish `not_applicable` from a real warning; (c) log rotation for the 3 large files (copy-then-truncate, no deletion of history); (d) quarantine-annotate the 10 unreadable historical files (move nothing; list them in an index so no code trips on them); (e) confirm `.env` completeness (add `PORT` explicitly; no values in code).
2. **Notifications:** retry/repair `03_Production_Notify` (credential or timeout), then rerun the relay self-check.
3. **Resilience:** Groq 429 backoff in the chain steps; off-machine backup proposal for the founder to approve (U2).
4. **Then** the remaining groups of your list (the message was cut after the first group; send the rest).

## 9. Phase 2 results (infrastructure group), 2026-11-06 evening
| Item | Result |
|---|---|
| server.js without errors | **OK**: 0 real crashes since 2026-10-25, `/health` 200, supervisor present (no change needed) |
| All routes answer correctly | **OK**: 37 of 37 probed GET routes return 200/302/401, none 5xx, none over 5 s (routes with params or heavy/side-effect names were deliberately not probed) |
| Database healthy | **No database by design.** New `scripts/data_integrity_check.py` + `config/data_integrity_known.json`: 8 historical unparseable files and 4 JSONL with old bad lines are baselined; any NEW corruption fails the doctor round and nightly gate. Nothing deleted |
| .env complete, no values in code | **OK**: 33 variables, none empty, tracked-secret scan clean; explicit `PORT=3000` added; `AMAZON_ASSOCIATE_TAG` stays a founder item |
| Autostart after reboot | **Partly proven**: dry-run of `start_factory_supervised.ps1` correctly refuses to start second copies. A real reboot was NOT done (it would restart the founder's machine): still UNKNOWN end to end |
| Publish follow-ups | **Fixed a real gap found today**: a product published mid-day (B17-001 at 17:26Z) would have waited until tomorrow for its tool page, IndexNow and listing check (once-a-day gates). `publish_approved_daily` now re-opens them; test added |
| n8n relays 03/04 | Added Retry on Fail (3 tries, 3 s) to the Telegram nodes and applied live (DB backup `backup_gf_envfix_20261106_182923`, rollback command in the apply script). Live check: unauthenticated 403, authenticated 200. `03_Production_Notify` still shows its old 12:54 error until its next real event: not yet proven by a successful run |
| Still open | U1 token rotation (founder), U2 off-machine backup (founder decision), M2 Paddle 403 (founder), M3 real reboot test, M4 working-tree drift, M6 intermittent internet |
