# OpenClaw Factory — Status Report

**Last updated:** 2026-07-09
**Governed by:** [CONSTITUTION.md](./CONSTITUTION.md), supreme law: [OPENCLAW_OS_CONSTITUTION.md](./OPENCLAW_OS_CONSTITUTION.md)

## Day 08 Complete

**Theme: the factory learned to find its own opportunities, remember everything, survive without Claude, and honestly judge itself.** Five new capabilities, taking Day 06–07's quality/pricing gates and turning them into a self-sustaining loop.

| Component | What it does |
|---|---|
| Value-based pricing fix (`scoutBriefPrompt()` + `profit_oracle.butter_price()`) | Groq now prices for value directly (verified live: suggested $49 unprompted); anything still under $30 gets repriced to a defensible $30–100, unless the niche itself is genuinely weak (SKIP-tier) |
| `OpenClaw_Brain/` (Knowledge Brain, 20 files across 20 folders + `MASTER_INDEX.md`) | The factory's permanent memory — architecture, living cells, councils, market intelligence, and 3 documented Lessons Learned — CONSTITUTION.md §18 |
| `knowledge_brain.js` + `GET /brain` | Real keyword search across the whole Brain, no fabricated "AI search" — plain substring scan, honest about it |
| `market_hunter.py` (Golden Hunter) | Discovers new candidate niches from curated categories × seasonality, **consults the Knowledge Brain first** (rejected niches, quarantine history, duplicates) before ever scoring anything — CONSTITUTION.md §19. Runs daily via `factory_loop.js`, exposed via `GET /hunter` |
| `SURVIVAL_GUIDE.md` | How to run the entire factory without Claude Code — start it, run every cell by hand, read opportunities, emergency procedures. Found and documented a real gap: `CLAUDE.md`'s install instructions were missing `pypdf`/`Pillow`/`arabic_reshaper`/`python-bidi` |
| `self_awareness.js` (Self-Awareness Engine) | Answers "how am I doing, truthfully?" daily — vital signs, growth vs. yesterday (`GROWTH_LOG.md`), honest self-diagnosis, one verdict paragraph. No code path forces a positive verdict — CONSTITUTION.md §20. `GET /awareness`, folded into `GET /good-morning` |

**Verified live today (2026-07-09), via `node self_awareness.js`, not a synthetic scenario:**

> اليوم المصنع سليم. أصبح أذكى مقارنة بالأمس لأن تحسّن أبرز في ملفات المعرفة (+1). أقوى خلية: Dashboard/Health (100%). أضعف خلية: Butter Compliance (15%). أكبر فرصة: 20 فرصة مسجَّلة في GOLDEN_OPPORTUNITIES.md بانتظار مراجعة Galaxy. التركيز التالي الموصى به: معالجة Butter compliance (15% فقط من آخر 20 فحص اجتاز حد $30).

Translated: **healthy, smarter than yesterday** (+1 knowledge file), **strongest cell: Dashboard/Health (100%)**, **weakest cell: Butter Compliance (15% — only 3 of the last 20 Dual Inspection runs actually cleared the $30 floor)**, 20 golden opportunities awaiting Galaxy's review, next recommended focus: closing that Butter-compliance gap.

**Read honestly, not as a contradiction:** the pricing fix (this same day) demonstrably works going forward (Groq suggesting $49 live) — the 15% figure reflects the *last 20 inspections on file*, most of which predate the fix (test runs and pre-fix Scout calls at $9.99–$14.99). The Self-Awareness Engine doesn't know that context automatically; it reports the raw number and lets a human read the reason. That gap between "the fix works" and "the trailing metric hasn't caught up yet" is itself worth watching over the next few real Scout runs.

**Known, still-open gap, surfaced again by Self-Awareness's own compliance check (§19):** the circuit breaker still doesn't cover `/api/scout/run` — see [OpenClaw_Brain/19_Lessons_Learned/The_Circuit_Breaker_Discovery.md](./OpenClaw_Brain/19_Lessons_Learned/The_Circuit_Breaker_Discovery.md).

---

## Day 06–07 Summary

**Theme: the factory learned to judge its own work before publishing it.** Four new capabilities layered on top of Day 05's pipeline, plus the supreme constitution that names why they exist.

| Component | What it does |
|---|---|
| `cover_designer_v2.py` | Real 70/20/10-rule covers (Pillow), fixed a genuine Arabic-shaping bug (`arabic_reshaper`+`python-bidi`) that earlier covers silently had |
| SUBTITLE placeholder fix | `book_generator.py` no longer leaks a literal `"SUBTITLE"` tag as real content when Groq echoes its own prompt tag |
| `profit_oracle.py` | Scores any niche 0–100 across Demand/Competition/Margin/Execution-fit *before* a single AI token or PDF page is spent on it — CONSTITUTION.md §16, The Butter Principle |
| `OPENCLAW_OS_CONSTITUTION.md` | Installed as the supreme governing law above `CONSTITUTION.md` — Mission, Councils, Anti-Fragility, Golden Hunter, etc. |
| `inspectors.py` (Dual Inspection) | Two independent gates — **Technical Inspector** (cover/PDF/Arabic/placeholder, real pixel + `pypdf` checks, not self-reported metadata) and **Commercial Auditor** (profit score, $30 Butter price, duplicates, prior rejections) — CONSTITUTION.md §17, this repo's concrete Quality Council. Wired automatically into the end of every `generate_book()`. |
| Circuit breaker (`REJECTED_NICHES.md`) | `factory_loop.js`'s HUNT no longer retries a niche Dual Inspection already rejected within 7 days — Anti-Fragility: rejections become durable memory, not repeated Groq spend |

**Real bug found and fixed along the way:** `server.js`'s `/generate-book` was silently dropping the `published`/`inspection` fields from its response — the actual root cause of a 5-hour, ~10-minute-interval retry storm `factory_loop.js` ran against a single rejected niche before this session started. Fixed as a prerequisite for the circuit breaker to be possible at all.

**Verified today via a real, live `/api/scout/run` call (not a synthetic test):** Scout picked a real Groq-generated niche ("الإبداع الفوري: كيف تحول ردود أفعالك إلى فرص ذهبية") → `profit_oracle` scored it 62/100 (GOOD) → the book generated cleanly and **Technical Inspector passed all 13 checks** → **Commercial Auditor blocked it on `butter_price: $12.99 < $30`** → correctly quarantined, not published.

**⚠️ Architectural gap found during that same test, not yet fixed:** the circuit breaker only guards `factory_loop.js`'s own `hunt()` loop. `/api/scout/run` (the button a human or n8n actually triggers) calls `book_generator.py` through a separate path and never writes to `REJECTED_NICHES.md` — so repeated manual/n8n-triggered Scout runs on a similarly-priced niche are **not yet** protected by the breaker, only the autonomous loop is. Candidate fix: move the rejection-recording into `book_generator.py` or `/generate-book` itself, so every caller shares one memory.

**The real blocker underneath all of it:** Scout's Groq-suggested prices cluster at $9.99–$14.99. The Butter Principle's $30 floor is a hard, correct gate — but as configured today, it means **most Scout-generated books will never publish automatically** until either Scout's pricing prompt is changed to aim at $30+, or a human deliberately overrides price per book. This isn't a bug in the gate; it's the gate doing exactly its job against the current defaults.

---

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
2. ~~**Human review step ("Galaxy")**~~ — **partially superseded by Day 06–07's Dual Inspection**: every book now passes an automated Technical + Commercial gate before it could ever reach a human. This is *not* the same thing as a human review queue, though — there is still no UI/endpoint for Galaxy to eyeball a book before it publishes; today "review" only happens automatically (inspectors.py) or not at all.
3. ~~**Structured `knowledge_base.json`**~~ — **substantially done in Day 08**: `OpenClaw_Brain/` is the real, structured knowledge base (20 files, `MASTER_INDEX.md`, searchable via `knowledge_brain.js`/`GET /brain`). `books/_generation_log.jsonl`/`scout_runs.log` remain flat logs, but `QUARANTINE.md`/`REJECTED_NICHES.md` now actively *inform* future decisions (market_hunter/HUNT both consult them before proposing a niche), not just record them.
4. ~~**Scheduled self-healing daemon**~~ — **done in [8]**: `factory_loop.js` polls `/health` every 10 minutes and takes automatic corrective action (finance repair, missing-book regeneration); start it via `start_factory.bat` or `node factory_loop.js`.
5. **Automated test suite** — all testing this session was manual/live verification against the running server. No `npm test`/`pytest` regression suite exists yet (Constitution §12).
6. **Other product tracks** — per `CLAUDE.md`'s 3-layer architecture, only `book_engine` (Layer 2) is active; `template_engine`, `art_engine`, `app_engine`, `service_engine`, `trade_engine` are not started (consistent with the golden rule: no new product line before the current one proves profitable).
7. **Circuit breaker still doesn't cover `/api/scout/run`** (Day 06–07 finding, still open) — `REJECTED_NICHES.md` is only written to by `factory_loop.js`'s own `hunt()` and `market_hunter.py`; the Scout button's direct path to `book_generator.py` never records a rejection there. Needs the recording logic moved to a shared point (`book_generator.py` or `/generate-book`) so every caller benefits. As of Day 08, `self_awareness.js`'s Constitution-compliance check (§19) surfaces this gap automatically every day, so it can't be silently forgotten.
8. ~~**Scout price vs. Butter Principle mismatch**~~ — **fixed**: `scoutBriefPrompt()` now asks for value-based premium pricing (verified live: Groq suggested $49 unprompted), and `profit_oracle.butter_price()` catches anything still under $30 for a genuinely non-weak niche. Self-Awareness's own live verdict (2026-07-09) shows the *trailing* butter-compliance metric still at 15% — expected, since most of the last 20 inspections on file predate this fix; worth re-checking after a handful of fresh Scout runs.

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

   > **n8n:** open workflow → add HTTP Request node →
   > POST http://localhost:3000/api/trends →
   > Body: `{{ $json }}` → Save → Test

2. **Run `start_factory.bat` and test the full pipeline live.**
   Everything in this file has been tested piece-by-piece and in cross-task regression (§2), but never all three processes (n8n + `server.js` + `factory_loop.js`) started together from the actual `.bat` file in one shot. Do this once item 1 is done, then click **Scout** on the dashboard and confirm a book appears in `books/` and (once the n8n node is live) an entry lands in `OPPORTUNITIES.md`.

3. **Fix the price mismatch so a book can actually publish.** Superseded by Day 06–07: Quality Gate approval is no longer the last step before a book counts as done — Dual Inspection (§17) is, and it verified live today (see Day 06–07 Summary) that Scout's real Groq-suggested price ($12.99) fails the $30 Butter floor even when everything else — niche score, cover, PDF integrity — passes cleanly. The next real dollar requires one of: (a) change Scout's pricing prompt/logic to target $30+, or (b) add a manual price-override step before generation so a human can deliberately price a promising niche at Butter level. Until one of these ships, `published: true` will keep being the rare case, not the default.