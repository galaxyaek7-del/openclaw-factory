# PROGRESS.md: Galaxy Forge (OpenClaw Factory)

Started 2026-11-05. Read this first in every new session and continue from "Next".
Rules of this file: facts marked OBSERVED were checked this session; nothing is guessed.

## 0. Founder directive of 2026-11-05 (top priority, overrides the plan below)

Goal: **the first real paying customer**. The factory serves only this. No new arms, no new ideas, simplest solution always. Stop if C: free space drops under 3 GB.
- **Only Claude Code works on this project. OpenCode is stopped** (its database was slimmed and the old one deleted; the 44 session exports are kept).
- **Phase 1 (stabilise)**: (1) database task finished (T10); (2) new-product production frozen by `GF_FREEZE_NEW_PRODUCTS=true`, details in section 3 task T11; (3) this note; (4) autostart F2 prepared, see T12; (5) Telegram F5 steps written for the founder, see T13.
- **Phase 2 (demo)**: a chat assistant for Algerian Umrah agencies (Arabic, Algerian Darija, French; hands a ready-to-book customer to the agency owner), shown from a phone; fictional agency data labelled as an example; one-page pitch AR/FR, three DZD price proposals (founder decides), top 10 objections with answers. Reuse earlier work (real-estate broker assistant, traveller assistant, auto-reply) before building.
- Red lines still hold: no deletion without backup, no payment/subscription, nothing published to the public or sent to real customers, no secrets exposed.

## 1. Current state (OBSERVED 2026-11-05)

- Server `server.js`: up (health 200), under `scripts/supervisor.js`. Restarted this session.
- Loop `factory_loop.js`: it was DEAD from 2026-11-01 23:58Z to 2026-11-05 07:39Z (3.3 days,
  nothing supervised it). Restarted this session under the supervisor. It recovered cleanly.
- Products: 116 in the registry, 111 `PUBLIC_LISTING_VERIFIED` on Gumroad, 4 `UPLOAD_COMPLETED`,
  1 `READY_FOR_AUTHORIZATION`. Sales: 0. Revenue: $0 (`config/reality.json`: published_books [],
  commercial_proof UNKNOWN). `FIRST_SALE_VERIFIED` = 0.
- Production, QA, publishing (after per-product approval), sales polling, backups all run in the
  loop. The binding constraint is demand reaching the products, not production
  (`docs/factory/COMPANY_OPERATING_PLAN_2026-11.md`).
- Doctrine gate `scripts/check_doctrine.py`: all layers OK (54 tests).
- Daily protection check: FAIL on `local_backup` (fixed this session: backup `local-2026-11-05`
  written, restore-checked) and `payable_withdrawn` (2 held listings still published).

## 2. Faults found

| # | Fault | Severity | Owner |
|---|---|---|---|
| F1 | Disk C: was 1.2 GB free because of the 141 GB `opencode.db`. FIXED 2026-11-05: slim copy in use, old files deleted with the founder's approval ("احذف القديم"); 142.5 GB free, `disk_space` check PASS. Keep an eye on growth: the new OpenCode database will grow again through the `event` table (backlog B40). | FIXED |
| F2 | Loop had no restart after a crash/log-off (3.3 days dead). No autostart task for server/loop (B37). | HIGH | restarted by agent; autostart install = founder (`scripts/install_factory_autostart.ps1`; persistence was refused to the agent before) |
| F3 | n8n unreachable ("fetch failed"); the sensing workflows do not run. Watchdog exists but n8n is still down. | HIGH | agent |
| F4 | Any caller of `gumroad_publisher.create_product()` could create a paid listing with no approval or gate evidence once the live switch was on (B4). | HIGH | agent: FIXED, see task T3 |
| F5 | Telegram not configured (`TELEGRAM_BOT_TOKEN`/`OPENCLAW_TELEGRAM_CHAT_ID`): no alert reaches the founder, so a dead loop is silent. | MEDIUM | founder (secrets, red line) |
| F6 | 2 held listings (`/l/iaiyt`, `/l/wteork`) and `/l/owtmpe` still take money at "$0+"; the API cannot unpublish. | HIGH | founder (Gumroad dashboard) |
| F7 | `NEEDS_ATTENTION.md`: top golden opportunity unchanged for 2680 h; no candidate passes the Proof of Payment gate (ADR-121). By design, not a bug. | INFO | founder evidence |
| F8 | 1,868 uncommitted paths (data ledgers, reports, books manifests). Commits must be selective. | MEDIUM | agent |
| F10 | The central Quality Gate in `distributor.py` was opt-in (only when a caller configured it) although the 2026-10-17 founder directive and `tests/test_exp_c81_utm_regression.py` say mandatory: a real publish on any arm skipped it. | HIGH | agent: FIXED in 2fb75161. Callers of real `distribute()`: `src/publish/auto_publisher.py` (Gumroad) and `x_queue.py` (X, spend-blocked anyway); both now stop without gate evidence |
| F9 | Demand: no board for Pinterest, no analytics receiver, no social credentials (B6, B18, B26). | HIGH for revenue | founder |

## 3. Plan (priority order)

| Task | What | Status |
|---|---|---|
| T1 | Restart server + loop under supervisor; write backup | DONE (not committed: runtime state only) |
| T2 | CLAUDE.md under 10,000 chars, details to `docs/claude_md/`, backup `CLAUDE.backup.md` | DONE |
| T3 | B4: central publication clearance in `create_product()` (founder approval or Quality Gate decision), arm + distributor wiring, tests | DONE, commit 2fb75161. Wider run: 1,377 tests, 4 failures; 1 was real (see F10, fixed), 3 are not from this work (see section 4) |
| T4 | F3: bring n8n back (logon task `GalaxyForge-N8N-Autostart`), verify with `scripts/n8n_workflow_health.py` | DONE: n8n up (200) 2026-11-05 08:08Z. Its last exit was 0xC000013A (console closed). Workflows `02_Sales_Poll` and `Openclaw_Sensing_Engine` still show STALE/FAILING from the days the server was down: re-check after their next scheduled run |
| T5 | F8: commit hygiene, commit only own files per task | ongoing |
| T6 | Re-run protection check; confirm only founder-owned items remain | DONE 2026-11-05: 4 PASS; FAIL `disk_space` (1.3 GB, clears when the founder approves deleting `opencode.db.old`) and `payable_withdrawn` (founder, Gumroad dashboard) |
| T7 | Next engineering backlog items that are not founder-blocked (B7, B9, B11) | B11 DONE (index rule in `docs/factory/README.md`, no per-file headers: the loop rewrites several root docs). B7 skipped: 4 of its 5 pages are for held/withdrawn/duplicate items, and measurement (B6) is the real bottleneck. B9 DONE: `cohort_contract.py` converts each cohort product to the batch-14 manifest shape (`{id, slug, title, price_cents, files{role: path, bytes, sha256}, qa}`) and runs adapter QA (hashes, bundle contents, workbook/docx open, thin-guide limits); wired into the 4 cohort `build.py` (`<cohort>/contracts/<id>.json`, outside the zipped folder; `--qa` now fails on a contract failure). Proof: regenerated B10+B11 in a scratch copy with and without the change: identical manifests, READMEs, zip contents and workbook values, except `bundle_bytes` which also differs between two runs of the old code (zip timestamps). P10 and SHOP also build and pass. 22 tests. Not done: `book_generator.py` and `scripts/build_tool_workbook.py` are still outside the contract. `cohort_GF_PREMIUM_10_2026_09/build.py` and the SHOPIFY one are untracked files in git; patched on disk, not committed |
| T9 | Diagnose the 3 failing tests in section 4 | DONE: the 2 visual QA tests had a stale fixture (3-colour cover vs the committed adapter's `cover_has_imagery` check, which is right); fixed in the untracked `tests/test_visual_qa.py`, 18 pass, left uncommitted because the file is untracked. The `profit_oracle` text test fails because of someone else's uncommitted D8 fail-closed change in `profit_oracle.py` (`_score_margin(niche, platform=...)`): update that test when that change is committed |
| T10 | OpenCode DB shrink (founder directive): cache cleanup 1.63 GB (approved); 44 main sessions exported and verified to `C:\Users\Dell\opencode_exports` (437 MB, MANIFEST.json); slim copy without the `event` table built (6.9 GB; row counts and text lengths of all other tables identical; integrity ok; OpenCode lists the sessions) and swapped in; original kept as `opencode.db.old` | DONE: `opencode.db.old` and its wal/shm deleted on the founder's approval; 44 session exports kept in `opencode_exports` |
| T11 | Freeze new products (founder directive) | DONE 2026-11-05: flag `GF_FREEZE_NEW_PRODUCTS=true` in `.env` (untracked). Gates: `factory_loop.js` (`triggerGenerateBook` incl. the two heal paths, Golden Hunter auto-produce, `runAgentProductChain`, live distribution) and `scripts/publish_approved_daily.py` (wins over `GF_AUTO_PUBLISH_APPROVED=true`, runs nothing). Loop restarted by exact PID (new PID under the supervisor) so it reads the flag. Existing listings, site pages, sales polling, backups, reports keep running. 3 new tests + 30 existing pass. Unset the flag to resume. Manual `/generate-book` from the dashboard and manual `publish_batch14.py` are not blocked: they need a human |
| T12 | F2 autostart | INSTALLED 2026-11-05 by the agent on the founder's explicit order ("ثبت التشغيل التلقائي انت"): task `GalaxyForge-Factory-Autostart`, state Ready, runs at logon +1 min. Test: started the task by hand with server and loop up: exit 0, no duplicate process, health 200. NOT tested by a real reboot/logon. Found and fixed a real fault in `scripts/start_factory_supervised.ps1`: its "server already running" guard used `Get-NetTCPConnection -State Listen`, which returns nothing for a live listener here, so at logon with a server up it would have started a second server (EADDRINUSE crash-loop under the supervisor). Now a real TCP connect to 127.0.0.1:3000. Dry run with both processes up: "server: already running", "factory_loop: already running". Install: `powershell -ExecutionPolicy Bypass -File scripts\install_factory_autostart.ps1` (task `GalaxyForge-Factory-Autostart`, logon +1 min; undo with `Unregister-ScheduledTask`). Not tested by a real logon |
| T13 | F5 Telegram steps | DONE (written): `docs/factory/TELEGRAM_SETUP.md`. State observed: token set, bot `OpenClaw_Abdelkader_bot`, 0 updates, `OPENCLAW_TELEGRAM_CHAT_ID` missing. The founder does the 7 steps by hand (secrets are his); the direct Python path needs only token + chat id, n8n's `$env` block does not matter for it |
| T14 | Phase 2: Umrah-agency assistant demo (founder directive) | DONE 2026-11-05 (SIMULATION data). Reuse check: the only related earlier work was the Arabic teacher auto-reply (`lib/response_intents.js`, `response_router.js`); no real-estate or traveller assistant exists in the repo. Kept its rules (first message discloses it is automated; answers only from supplied facts; negotiation, complaints and unknown always go to the human) but built a new small engine, because the old one is Arabic-only and single-product. `services/umrah_assistant/`: `engine.js` (deterministic, no LLM/network/API key; AR, Algerian Darija in Arabic script and in Latin letters, French; booking flow package, persons, name, phone, then a lead card; refuses to negotiate, to argue complaints, to answer ritual rulings), `agency_example.json` (fictional agency, DZD prices), `demo.template.html` + `build_demo.js` give the single-file phone demo `demo/index.html` (WhatsApp-like, owner-view lead card, autoplay `?demo=fr|dz|zz`). 21 tests pass (classification of 60 messages in 3 languages, "no invented number" check, booking, negotiation, complaint, phone formats). Checked in headless Edge: renders, a full Darija scenario ends with the correct lead card. Not tried on the founder's phone. Founder-only docs kept OUT of the public repo (untracked, on disk): `docs/umrah_demo/DEMO_GUIDE.md`, `PRICING_PROPOSALS.md` (3 DZD options, recommendation B 9,000 DZD/month, NOT MEASURED), `OBJECTIONS.md` (10 with answers). One-pager AR/FR: `docs/umrah_demo/ONE_PAGER.pdf/.html` (1 page, placeholders for his contact and pilot terms). Gaps, in Truth First terms: WhatsApp link NOT CONNECTED; public chat link NOT BUILT; delivery of lead cards to the owner NOT BUILT (can use the Telegram setup, F5); agency data intake form NOT BUILT; privacy policy UNKNOWN |
| T15 | Phase 3: demo for a real prospect (the cheapest step that helps the first sale; no public link, no sending, nothing speculative) | DONE 2026-11-05. `services/umrah_assistant/validate_agency.js` (required fields, positive integer DZD prices, deposit < price, ISO dates, departures point at real package ids, bilingual lists, placeholder detection, typo-guard warnings, REAL file may not still say "example"), `agency_template.json` (blank, full of REMPLIR: refused by the validator), `build_demo.js --agency <file> --out <dir>` (validates first, refuses on errors, banner switches to an honest "trial version for your agency, not connected to WhatsApp yet" when `_status` is REAL), `agencies/` (own `.gitignore`: real customer data is never committed). 16 new tests (37 with the assistant's); the engine answers with the prospect's own numbers (tested), agency text cannot break out of the page script (tested), the committed example demo is checked against its sources. Procedure for the founder added to the untracked `docs/umrah_demo/DEMO_GUIDE.md`. NOT built on purpose (golden rule, no first dollar and no agency has said yes): public chat link, Telegram delivery of lead cards, intake form, database. Build them when an agency accepts the trial; the public link needs the founder's approval |
| T8 | Founder list: refresh `docs/factory/FOUNDER_ACTIONS.md` with F1, F2, F5, F6, F9 | DONE, commit 974b80f3 (section 0) |
| T16 | Verify the freeze and n8n (follow-ups, no new build) | DONE 2026-11-05. factory_loop.log shows 16 daily-step skips with "new products frozen (GF_FREEZE_NEW_PRODUCTS=true)" after the restart: the freeze is OBSERVED working live. n8n: `02_Sales_Poll` success at 11:00Z and `Openclaw_Sensing_Engine` success at 08:12Z, both FRESH; `01_Market_Scout` is MANUAL_ONLY (no runs, UNKNOWN). Disk free 133.9 GB. Still WAITING FOR REAL DATA: autostart by real reboot, demo on the founder phone, Telegram chat id (F5), unpublishing of the 3 "$0+" listings (F6). |

## 4. Stuck ("عالق") and failures not from this work

No stuck task. Three tests fail on the current tree and are unrelated to publishing; not fixed yet, listed so they are not forgotten (task T9):
- `tests/test_d16_d19.py::TestD19DocumentationOnly::test_d8_still_verified` (expects the text `ECONOMICS.net_profit(price, "gumroad_digital", config)` in `profit_oracle.py`)
- `tests/test_visual_qa.py::TestVisualRealEvidence::test_good_cover_produces_evidence_backed_pass` and `TestGate1CannotPromoteNotAvailable::test_clean_visual_pass_does_contribute_to_pass` (verdict is REVIEW, test expects PASS)

## 5. Decisions and why

- Restarted the loop with the existing supervisor, not a new mechanism: it is tested
  (`tests/test_supervisor.js`) and gives crash-loop guarding.
- B4 enforced inside `create_product()` itself, with no override argument, so no caller can
  skip it. Two accepted clearances only: per-product founder approval (exact title, price,
  description, bundle hash) or an allowed central Quality Gate decision.
- Not touching F1/F5/F6: deleting data, secrets and live listing changes are red lines.

## 6. Next

Founder: unpublish the 3 "$0+" listings (F6), Telegram secrets (F5), autostart (F2). Agent: re-check n8n `02_Sales_Poll` and `Openclaw_Sensing_Engine` after their next scheduled run.
