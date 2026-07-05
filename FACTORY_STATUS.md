# OpenClaw Factory — Status Report

**Last updated:** 2026-07-05
**Governed by:** [CONSTITUTION.md](./CONSTITUTION.md)

## Day 05 Final Summary

**Tasks [2]–[11]: all built, all tested against a live running dashboard.** ✅

| Task | Status |
|---|---|
| [1] Diagnosis | ✅ complete |
| [2] AI Content Engine | ✅ complete |
| [3] Finance Fix | ✅ complete |
| [4] Scout Production Pipeline | ✅ complete (n8n real-trends limitation flagged) |
| [5] Quality Gate | ✅ complete |
| [6] Factory Doctor `/health` | ✅ complete |
| [7] Knowledge Base (this file + `CONSTITUTION.md`) | ✅ complete |
| [8] Self-Healing Factory Loop | ✅ complete |
| [9] `start_factory.bat` | ✅ complete |
| [10] Weekly Auto-Report | ✅ complete |
| [11] n8n ↔ server.js Integration | ⚠️ **complete on the server.js side; one manual step remains in n8n's UI** (see §6, item 1) |

**Bottom line:** the factory can, today, generate a real AI-written book end-to-end, gate it for quality, self-heal its own infrastructure, and report on itself weekly — the only missing wire is a single node inside n8n that no API key can add remotely.

---

## 1. Components built (Tasks [1]–[11])

### [1] Diagnosis
Full audit of `server.js`, `book_generator.py`, the six Groq agents, and the Finance flow. Findings that shaped everything below:
- `/finance` read `finance_data.json` (root) — valid; a separate, unused `data/finance.json` was permanently corrupt (dead file, no code read it).
- `book_generator.py` had zero AI integration — the `cookbook` type returned 12 hardcoded recipes regardless of title/topic.
- Scout's button only called Groq with a generic market-analysis prompt; no connection to n8n or to book production.
- `Factory`, `Research`, `Knowledge`, `Ideas`, `Books` at the repo root were stray empty **files**, not folders (Windows is case-insensitive, so `Books` collided with the real `books/` directory needed later — resolved by renaming it aside to `Books.stray_empty_file.bak`, not deleting it).

### [2] AI Content Engine — `book_generator.py`
- Added `generate_book(title, topic, chapters, audience, price)` — generates real, topic-specific book content via **Groq** (`llama-3.1-8b-instant`), the same model/key the Scout agent already used. No new AI provider introduced.
- Content parsing is lenient by design: the small/fast model doesn't reliably follow a strict format, so the parser recognizes multiple real observed response shapes rather than assuming one.
- Automatic cover (`safe_cover`), with an internal fallback if cover drawing fails for any reason.
- Content-generation fallback (`_fallback_book_content`) if Groq is unreachable or unparseable — production never stops, quality degrades instead.
- Fixed a **pre-existing** encoding bug: Python subprocess stdin/stdout silently used the OS locale codepage instead of UTF-8, corrupting Arabic titles/filenames when spawned from Node — this affected the *old* `/generate-book` path too, not just the new one.
- Old template path (`journal`, `planner`, `cookbook`, ... — no `topic` key) is untouched and still works identically.

### [3] Finance Fix
- `loadFin()` is now defensive: corrupt JSON is quarantined to `finance_data.json.corrupt-<timestamp>.bak` and replaced with clean empty data — `/finance` can no longer 500.
- `saveFin()` is atomic (temp file + rename) — a crash mid-write can't corrupt the file.
- Structured error log: `finance_errors.log`.
- Input validation added to `/finance/add` (platform allow-list, positive numeric amount) and `/finance/delete/:id` (numeric id) — closes a silent-`NaN`-corruption path that existed before.

### [4] Scout Production Pipeline
- New endpoint `POST /api/scout/run`: triggers the n8n Sensing Engine → picks a niche/brief (Groq) → calls `generate_book()` → returns the result.
- New dedicated frontend handler `runScout()` (the other 5 agent buttons still use the original generic `runAgent()`, untouched).
- Every external call (n8n webhook, Groq) has timeout + retry, per the Constitution.
- **Known limitation (flagged, not silently hidden):** the n8n webhook currently responds `"Workflow was started"` immediately (fire-and-forget) rather than waiting for real Google Trends results — no n8n API credentials were available to fix the workflow's Respond node. The pipeline calls n8n for real, and would use real trend data if the webhook ever returns it, but today niche selection runs on Groq alone. See **Next Milestones**.
- Run history logged to `scout_runs.log`.

### [5] Quality Gate — `book_generator.py`
- `quality_gate(niche, theme)` runs **before** any Groq call or PDF generation and can block production entirely.
- **Check 1 — niche not empty.**
- **Check 2 — Amazon competition < 50,000 results**, reusing `niche_validator_v2.py`'s `CRITERIA["max_competition"]` constant directly (no duplicated threshold) and its saved reports in `niche_reports/`. That tool is deliberately offline (manually-saved HTML, no live scraping) — with no matching saved report for a niche, this check is explicitly **skipped**, not silently passed or failed, since Scout-picked niches won't have prior research yet.
- **Check 3 — cover template exists**, i.e. the requested theme is a recognized key in `THEMES`.
- `niche_validator_v2` import is guarded against both `ImportError` and `SystemExit` (it calls `sys.exit(1)` if `bs4` is missing) so an optional dependency can never crash book generation.

### [6] Factory Doctor — `/health`
- Read-only `GET /health` endpoint, added before Express's static catch-all.
- Checks: `sensing_engine` (n8n reachable at `localhost:5678` — root path only, never the Scout webhook, so health checks have zero side effects), `book_generator` (file exists), `finance`, `books_folder` (PDF count).
- **Deviation flagged:** the task named `data/finance.json`; that file is the dead leftover from [1] that no code reads. The check targets the real file, `finance_data.json`, instead — checking the dead file would report "corrupt" forever regardless of actual system health.
- Overall status = `critical` if `book_generator` is down (nothing can be produced), `degraded` if any other check fails (all are self-healing or have a working fallback), else `healthy`.

### [7] Knowledge Base — `CONSTITUTION.md` & this file
- `CONSTITUTION.md`: the 15 engineering principles adopted as the highest-authority standard for this repo, plus the "Architecture: Sensing ↔ Brain" amendment added in [11].
- `FACTORY_STATUS.md` (this file): living record of what's built, what's tested, and what's honestly still missing — updated after every task, not just at the end.

### [8] Self-Healing Factory Loop — `factory_loop.js`
- Runs as its own process (never the dashboard's), ticking every 10 minutes: DIAGNOSE (`/health`) → HEAL (finance, empty `books/`, n8n warning) → HUNT (regenerate a missing book for a recent gate-passed niche) → LOG (`factory_loop.log`).
- `/generate-book` was extended to accept `topic`/`chapters`/`audience`/`price` (routing to the AI engine) so HEAL/HUNT can trigger *real* niche-specific generation through the same endpoint the task named — old callers without `topic` are unaffected.
- `GET /factory-loop/status` on the dashboard shows the last 10 entries plus a `likelyRunning` heuristic (log-recency based — there's no PID handle to confirm the process is alive for real).
- **Deviations flagged (see code comments):** "rebuild finance.json from scout_runs.log" isn't semantically possible (that log has no sales data) — it resets to clean empty data instead, same as the Finance fix's own self-heal. "Highest traffic niche" has no real metric yet (n8n doesn't return real trend volume) — most-recent gate-passed niche among the *literal* last 3 log entries is used instead.

### [9] `start_factory.bat`
- Launches `server.js` and `factory_loop.js` as separate windows with a 3-second stagger.
- **Updated in [11]** to also launch n8n first (see below).

### [10] Weekly Auto-Report — `factory_loop.js`
- Every tick that lands on a Sunday, if this week's report doesn't exist yet, generates `reports/WEEK_YYYY-MM-DD.md` (dated archive) and `FACTORY_WEEKLY_REPORT.md` (always-latest copy): factory health, books produced, opportunities discovered (from `OPPORTUNITIES.md` — populated by [11]), revenue, self-healing actions taken, and rule-based next-week recommendations.
- Appends a summary row to this file's **§5 Weekly Reports** table after each report — see that table for the live history.
- Manual trigger for testing: `node factory_loop.js --weekly-report [--force]`.

### [11] n8n ↔ server.js Integration — `POST /api/trends`
- **⚠️ Only half of this task could be completed.** Step 1 asked to add an HTTP Request node *inside* the n8n Sensing Engine workflow — that requires editing the workflow through n8n's own UI or its authenticated REST API. n8n's API returned `401 Unauthorized` when checked (no API key available in this environment; see [4]'s known limitation). **This must be done manually** — exact instructions are in the task's completion notes below.
- **What *is* built and working:** `POST /api/trends` on the dashboard — receives a trend item (accepts several possible field names: `niche`, `trend`, `topic`, `title`, `keyword`, `query`, `name`, since the real n8n item shape is unknown without workflow access; also accepts a JSON array for batch delivery), runs it through the *same* `quality_gate()` used by book generation (via a new `book_generator.py --quality-gate` CLI hook — no logic duplicated into JS), and appends anything that passes to `OPPORTUNITIES.md` with a timestamp. Always responds `200 OK` — a rejected trend or unrecognized payload is normal business logic, never a delivery failure for n8n to retry over.
- This is also what finally gives Task [10]'s weekly report real data for its "Opportunities discovered" section — `OPPORTUNITIES.md` didn't exist before this task.
- `CONSTITUTION.md` now codifies the contract: *"n8n is the Sensing layer. server.js is the Brain. They communicate only via HTTP POST /api/trends."*
- **`start_factory.bat` correction:** the task's literal script did `cd C:\n8n && npx n8n start` — that directory doesn't exist on this machine. n8n is installed globally (`npm list -g` → `n8n@2.25.7`, `n8n.cmd` directly on PATH), so the corrected launcher is just `n8n start`, no `cd` needed.

---

## 2. Test results summary

| Task | Scenarios tested | Result |
|---|---|---|
| [2] | Direct AI generation, CLI `--json` path, path-traversal attempt, empty-title validation, missing-key fallback, old template regression | 6/6 pass |
| [3] | Happy path add/delete, invalid platform/amount/id rejection, simulated corrupt-JSON self-heal, structured log, unrelated-endpoint regression | 13/13 pass |
| [4] | 7 live end-to-end Scout runs (4 real niches generated), 4 real observed Groq response shapes unit-tested, encoding fix verified on disk, old `/generate-book` + Finance + other agents regression | all pass |
| [5] | Direct `quality_gate()` unit tests (empty niche, unknown theme, pass, saved-report low/high competition), full `generate_book()` integration (gate blocks with no PDF written; gate passes normally), CLI path, old template regression, live Scout run | 8/8 + regression pass |
| [6] | Healthy baseline, simulated finance corruption, simulated missing `book_generator.py` (critical), simulated n8n-unreachable (degraded) — all via safe, reversible test conditions, never touching the user's real n8n process | 5/5 pass |
| [8] | Baseline tick, `/factory-loop/status` (fresh + populated + stale-heuristic), HEAL finance/books-empty, HUNT (eligible-in-last-3 and NOT-eligible scoping-bug regression), dashboard-unreachable safety net, `AbortController` timeout refactor | 10+/10+ pass across two review passes |
| [10] | Forced report generation (`--weekly-report`), `--force` re-run replaces (not duplicates) its own table row, Sunday/Monday/repeat-Sunday scheduling gate (simulated dates), `OPPORTUNITIES.md` present + absent, wired into a normal `--once` tick | pass |
| [11] | `--quality-gate` CLI hook (empty niche/valid niche/unknown theme), `/api/trends` with 6 field-name variants, no-usable-field payload, batch array, whitespace-only trend, empty body — all real HTTP calls | 8/8 pass |
| — | **Full cross-task regression** re-run after [8]'s review fixes: 26 live scenarios across [2],[3],[4],[5],[6],[8],[9] in one pass | 26/26 pass, zero regressions |
| — | Regression re-run after [11]: dashboard, `/health`, Finance, another agent, old `/generate-book`, `factory_loop.js --once` | all pass |

Every code change in [2]–[11] has a timestamped restore point in `backups/` and was verified against a real, running dashboard — not just read for correctness.

---

## 3. Current factory capability (end to end)

```
[Scout button] → n8n triggered (fire-and-forget today)
              → Groq picks a niche + brief
              → Quality Gate (niche / competition / cover)
              → Groq generates real book content
              → PDF assembled → books/
              → logged (scout_runs.log, books/_generation_log.jsonl)
              → shown in the dashboard's activity log + recent books list
```
Finance and the other 5 agents (Builder, Design, QA, Publisher, Finance-agent) are unaffected by any of the above and continue to work as before.

Running alongside this (separate process, `factory_loop.js`): a heartbeat every 10 minutes that checks `/health`, repairs what it can (corrupt finance data, an empty `books/` folder), and — every Sunday — writes a weekly report to `reports/WEEK_YYYY-MM-DD.md` (see Task [10]).

A second, independent intake path (Task [11]): n8n → `POST /api/trends` → Quality Gate → `OPPORTUNITIES.md`. This is separate from the Scout button's own n8n trigger in `/api/scout/run` — one *pulls* (Scout asks n8n to run, then picks a niche via Groq), the other *pushes* (n8n decides on its own schedule to notify server.js of a trend). The push side's sender (the n8n workflow node) still needs manual setup — see Next Milestones.

---

## 4. Next milestones

1. **Real n8n trends — receiving end done in [11], sending end still manual.** `POST /api/trends` exists and works (see [11]). What's missing is the n8n side: an HTTP Request node at the end of the Sensing Engine workflow that actually calls it. This needs to be added by hand in the n8n UI (no API key available to do it remotely) — exact steps:
   1. Open the Sensing Engine workflow at http://localhost:5678
   2. Add a node → search "HTTP Request" → drag it to the end of the workflow, after the last node
   3. Set **Method**: `POST`
   4. Set **URL**: `http://localhost:3000/api/trends`
   5. Set **Body Content Type**: JSON, **Body**: an expression, `{{ $json }}` (sends whatever the previous node's output item is)
   6. Save and activate the workflow
   Once that node exists, every trend the workflow discovers will automatically flow through Quality Gate into `OPPORTUNITIES.md` — no further server-side change needed. `/api/trends` also still doesn't receive real Google Trends *volume* numbers (the "highest traffic" gap from [4]/[8]) — it only receives whatever fields the workflow's last node happens to output, so once the node is added, check `trends_received.log` to see the real shape and confirm `extractNiche()` in `server.js` picks up the right field (it already tries `niche`, `trend`, `topic`, `title`, `keyword`, `query`, `name`).
2. **Human review step ("Galaxy")** — the original brief called for sending a generated book for human review before publishing. Not yet built: no review queue/endpoint exists; Scout currently goes straight from generation to `books/`.
3. **Structured `knowledge_base.json`** — today's `books/_generation_log.jsonl` and `scout_runs.log` are flat append-only logs. A real knowledge base (niche win/loss history, reasons, reusable scoring) to actively *inform* future Scout decisions — not just record them — is not built yet.
4. ~~**Scheduled self-healing daemon**~~ — **done in [8]**: `factory_loop.js` polls `/health` every 10 minutes and takes automatic corrective action (finance repair, missing-book regeneration); start it via `start_factory.bat` or `node factory_loop.js`.
5. **Automated test suite** — all testing this session was manual/live verification against the running server. No `npm test`/`pytest` regression suite exists yet (Constitution §12).
6. **Other product tracks** — per `CLAUDE.md`'s 3-layer architecture, only `book_engine` (Layer 2) is active; `template_engine`, `art_engine`, `app_engine`, `service_engine`, `trade_engine` are not started (consistent with the golden rule: no new product line before the current one proves profitable).

## 5. Weekly Reports

تقارير أسبوعية تلقائية من `factory_loop.js` (Task [10]) — صف جديد يُضاف تلقائياً بعد كل تقرير.

| التاريخ | كتب | إيرادات | إصلاحات ذاتية | التقرير |
|---|---|---|---|---|
| 2026-07-05 | 3 | $0.00 | 0 | [WEEK_2026-07-05.md](./reports/WEEK_2026-07-05.md) |

---

## 6. Next Dollar Actions

The three concrete things standing between today's build and the next dollar:

1. **Add the HTTP Request node to the n8n Sensing Engine workflow → `POST http://localhost:3000/api/trends`.**
   This is the one step in [11] that couldn't be done remotely (no n8n API key). Full step-by-step is in §4 item 1 above. Until this node exists, `/api/trends` is built and tested but has nothing feeding it — `OPPORTUNITIES.md` stays empty.

2. **Run `start_factory.bat` and test the full pipeline live.**
   Everything in this file has been tested piece-by-piece and in cross-task regression (§2), but never all three processes (n8n + `server.js` + `factory_loop.js`) started together from the actual `.bat` file in one shot. Do this once item 1 is done, then click **Scout** on the dashboard and confirm a book appears in `books/` and (once the n8n node is live) an entry lands in `OPPORTUNITIES.md`.

3. **Generate Book #3 after Quality Gate approval by Galaxy.**
   Note on numbering: `books/` already holds 3 real AI-generated PDFs from today's testing (see §2/§3), so this isn't literally the third book ever — read it as *the next book produced through the full reviewed flow*. Also worth knowing: there is **no automated "Galaxy" review queue yet** (§4 item 2 — not built). Today, "approval by Galaxy" means the Chairman reviewing the Scout-picked niche/brief by eye before triggering generation, not a system gate. Recommended flow right now: click Scout → read the niche it picked and the Quality Gate result in the activity log → if it looks right, let `generate_book()` run (it already will have); if not, delete the PDF from `books/` and click Scout again for a fresh pick.