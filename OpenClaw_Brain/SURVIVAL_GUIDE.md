# 🆘 Galaxy Forge Survival Guide

> Per OPENCLAW_OS_CONSTITUTION.md's Supreme Law — *"System before individuals. Everything is replaceable except the constitutional system."* — and its Anti-Fragility principle. This document proves that law in practice: everything below can be done with a browser, a terminal, and the free tools listed in §4. **No AI assistant, including Claude, is required for the factory to run, be understood, or be extended.** If Claude Code is ever unavailable, expensive, or replaced, this file — plus [MASTER_INDEX.md](./MASTER_INDEX.md) — is what lets a human or a different AI pick the factory up cold.

---

## 1. How to start the factory

### The one-command way

```
start_factory.bat
```

Double-click it, or run it from a terminal in `C:\openclaw-dasgboard`. It does exactly this (read the file — it's 12 lines, not a black box):

```bat
@echo off
cd C:\openclaw-dasgboard
start "n8n" cmd /c "cd /d C:\Users\%USERNAME%\AppData\Roaming\npm && npx n8n start"
timeout /t 5
start "Dashboard" node server.js
timeout /t 3
start "Factory Loop" node factory_loop.js
echo Dashboard: http://localhost:3000
echo n8n: http://localhost:5678
pause
```

It opens **three separate windows**, in order, with a short delay between each (n8n takes a few seconds to bind its port before the dashboard should start):

| Window | What it is | If you close it |
|---|---|---|
| n8n | The Sensing layer (trend intake) — see [10_Automation](./10_Automation/) | Dashboard keeps working; Scout falls back to Groq-only briefs |
| Dashboard | `server.js` — the Brain, port 3000, http://localhost:3000 | Nothing works — this is the core process |
| Factory Loop | `factory_loop.js` — self-healing + HUNT + Golden Hunter, every 10 min | No automatic healing/hunting; manual generation via the dashboard still works |

### Starting things manually (if the .bat file itself is ever broken or missing)

```powershell
# Terminal 1 — n8n (optional; the factory degrades gracefully without it)
n8n start

# Terminal 2 — the dashboard (required)
cd C:\openclaw-dasgboard
node server.js

# Terminal 3 — the self-healing loop (optional but recommended)
cd C:\openclaw-dasgboard
node factory_loop.js
```

Confirm it's alive: open **http://localhost:3000/health** in a browser, or:

```bash
curl http://localhost:3000/health
```

`"status": "healthy"` means everything is fine. `"degraded"` or individual `checks.*.ok: false` entries tell you exactly what's wrong — see §6.

---

## 2. How each cell works

Every cell below is a **standalone script or endpoint** — nothing requires Claude Code to run, inspect, or re-run.

### Scout — discovers and writes one book (`server.js`, `POST /api/scout/run`)

```bash
curl -X POST http://localhost:3000/api/scout/run -H "Content-Type: application/json" -d "{}"
```

What it does: triggers n8n (fire-and-forget), asks Groq for one book niche + price (value-based pricing, see [09_Prompt_Library](./09_Prompt_Library/)), generates the actual PDF+cover, and runs it through Dual Inspection. The response's `book.published` field tells you if it's actually cleared to sell — `book.success` alone does **not** mean that (see [19_Lessons_Learned/The_Success_True_Bug.md](./19_Lessons_Learned/The_Success_True_Bug.md)).

### profit_oracle — scores any niche 0–100 (`profit_oracle.py`)

```bash
python profit_oracle.py --run     # scores every entry in OPPORTUNITIES.md, writes GOLDEN_OPPORTUNITIES.md
python profit_oracle.py           # demo: 3 sample niches, one of each verdict (GOLDEN/GOOD/SKIP)
```

Or from Python directly: `from profit_oracle import score_opportunity, butter_price`.

### market_hunter — the Golden Hunter, discovers NEW candidates (`market_hunter.py`)

```bash
python market_hunter.py --run     # scans curated categories, brain-checks, scores, appends golden ones to OPPORTUNITIES.md
python market_hunter.py           # demo: 1 GOLDEN + 1 SKIP + 1 Brain-blocked sample
```

Runs automatically once per calendar day inside `factory_loop.js` — you don't have to run it by hand unless you want a result *right now*.

### inspectors — the Quality Council gate (`inspectors.py`)

Not usually run by hand — `book_generator.py`'s `generate_book()` calls it automatically at the end of every generation. To inspect a specific PDF/cover pair manually:

```bash
python -c "
from inspectors import final_inspection
r = final_inspection({'pdf_path': 'books/YOUR_BOOK.pdf', 'cover_path': 'books/covers/YOUR_COVER.png',
                       'title': '...', 'niche': '...', 'price': 39})
print(r['passed'], r['published'])
"
```

### Dashboard endpoints — the read-only windows into all of the above

| Endpoint | Shows |
|---|---|
| `GET /health` | Overall status of every component |
| `GET /oracle` | Top 5 GOLDEN opportunities |
| `GET /hunter` | Today's Golden Hunter catch |
| `GET /inspections` | Last 10 Dual Inspection results |
| `GET /brain` | The Knowledge Brain's folder map (`?q=<keyword>` to search it) |
| `GET /good-morning` | One combined daily briefing (health + top opportunities + last night's actions + next dollar actions) |
| `GET /factory-loop/status` | `factory_loop.js`'s last tick |

---

## 3. How to read GOLDEN_OPPORTUNITIES.md and approve products

Open [`GOLDEN_OPPORTUNITIES.md`](../GOLDEN_OPPORTUNITIES.md) (repo root) directly — it's plain Markdown, readable in any text editor or browser. Each row:

| Column | Meaning |
|---|---|
| النتيجة (score) | 0–100, from `profit_oracle` — see [08_Market_Intelligence](./08_Market_Intelligence/) for what's real data vs. estimate |
| الحكم (verdict) | 🏆 GOLDEN (80+, marked "يحتاج موافقة Galaxy") / ✅ GOOD (60–79) / ⛔ SKIP (<60, not listed here at all) |
| 🧈 (butter rating) | Visual shorthand for the same score, 1–5 butter emoji |
| السعر (price) | `profit_oracle`'s own rough estimate — **not** the guaranteed-$30+ number. For that, check `market_hunter_runs.log` or `GET /hunter`'s `recommended_butter_price` field |

**There is no automated approval button.** "Approval by Galaxy" today means: read the niche and score above, decide by eye whether it's worth actually generating, then either click **Scout** on the dashboard, or run `market_hunter.py --run` to (re)discover it, or call `/generate-book` directly with a title/topic/price of your choosing. The book that comes out will independently pass or fail Dual Inspection (`book.published` in the response) regardless of what GOLDEN_OPPORTUNITIES.md said — the score is a *recommendation to try*, not a guarantee of what will actually publish.

**Before approving anything, check it hasn't already failed:** open [`QUARANTINE.md`](../QUARANTINE.md) and [`REJECTED_NICHES.md`](../REJECTED_NICHES.md) (repo root; the latter may not exist yet if nothing has ever been rejected) — a niche appearing there recently means it already failed for a documented reason, and retrying it without changing anything will likely fail the same way again.

---

## 4. What this factory depends on (all free)

| Tool | What it's for | Where to get it | Cost |
|---|---|---|---|
| **Node.js** (confirmed v24.16.0 in this environment) | Runs `server.js`, `factory_loop.js`, `knowledge_brain.js` | [nodejs.org](https://nodejs.org) | Free |
| **Python** (confirmed 3.14.6) | Runs `book_generator.py`, `profit_oracle.py`, `inspectors.py`, `market_hunter.py` | [python.org](https://python.org) | Free |
| **Groq API** | The only AI model this factory calls (`llama-3.1-8b-instant`) — Scout's briefs, all 6 agents, book content | [console.groq.com](https://console.groq.com) → API key → put it in `.env` as `GROQ_KEY=...` | Free tier available |
| **n8n** | The Sensing layer (optional — factory degrades gracefully without it) | `npm install -g n8n`, confirmed installed at `n8n@2.25.7` globally | Free, self-hosted |

### Node package dependencies (`package.json`)

`express`, `cors`, `dotenv`, `groq-sdk`, `pdfkit` — install with `npm install` in the repo root.

### Python package dependencies — ⚠️ a real, undocumented gap found while writing this guide

[CLAUDE.md](../CLAUDE.md) only documents `pip install reportlab`. In practice, this factory also requires (confirmed installed in this environment, but never written down anywhere until now):

```bash
pip install reportlab pypdf Pillow arabic_reshaper python-bidi
```

| Package | Used by | What breaks without it (guarded, not a crash) |
|---|---|---|
| `reportlab` | `book_generator.py` | No PDF generation at all |
| `pypdf` | `inspectors.py` | PDF integrity checks skipped, technical inspection fails closed |
| `Pillow` | `cover_designer_v2.py`, `inspectors.py` | No 70/20/10 covers; falls back to a plain vector cover |
| `arabic_reshaper` + `python-bidi` | `cover_designer_v2.py` | Arabic cover text renders disconnected and in the wrong direction (a real bug this project hit once — see [19_Lessons_Learned](./19_Lessons_Learned/)) |

`niche_validator_v2.py` additionally wants `beautifulsoup4` for its optional manual Amazon-research mode — everything else works without it.

---

## 5. How another AI assistant (not Claude) can pick this up

1. **Read [MASTER_INDEX.md](./MASTER_INDEX.md) first.** It's the home page — folder map + the intended reading order (Vision → Constitution → Architecture → Cells → Councils → Current Mission → Daily Logs → Lessons Learned).
2. **Read [19_Lessons_Learned](./19_Lessons_Learned/) before writing any code.** Per CONSTITUTION.md §18: search the Brain before building. Three real, expensive mistakes are documented there in enough detail to not repeat them.
3. **Check [05_Living_Cells](./05_Living_Cells/) before touching an existing component.** It honestly scores what's solid vs. what has a known gap (e.g., the circuit breaker not covering `/api/scout/run` yet) — cheaper to read than to rediscover by breaking something.
4. **Use `knowledge_brain.js` to search, don't just skim folders:**
   ```bash
   node knowledge_brain.js search "pricing"
   node knowledge_brain.js map
   ```
   Or via the dashboard: `GET /brain?q=<keyword>`.
5. **Follow the two-constitution hierarchy** ([00_Constitution](./00_Constitution/)): `OPENCLAW_OS_CONSTITUTION.md` is supreme law (never touch it lightly); `CONSTITUTION.md` is the engineering standard that implements it — when adding a genuinely new principle, verify the current count first (`grep "^## [0-9]" CONSTITUTION.md`) and add it at the real next number, never a guessed one, recording why in its Amendment History table (this has happened for §16, §17, §18 — see the table itself for the exact pattern).
6. **Never fabricate a data source.** This factory has no live Google Trends, no live Etsy/Amazon scraping, no automated publishing. Every score is either real data (clearly labeled) or a documented heuristic (also clearly labeled). Keep it that way — see [08_Market_Intelligence](./08_Market_Intelligence/) for the exact real-vs-estimated breakdown to imitate.

---

## 6. Emergency procedures (there is no support line — this is what to actually do)

This is a one-person, self-hosted project. There is no vendor to call. These are the real, working responses to the failure modes this factory has actually had.

### First move, always: `GET /health`

```bash
curl http://localhost:3000/health
```

Read `checks.*` — each failing check names exactly what's wrong (finance, book_generator, sensing_engine, books_folder).

### "The dashboard won't respond at all"

`server.js` isn't running or crashed. Check the terminal window it was started in for an error. Restart it: `node server.js`. If it crashes immediately on start, check `.env` exists and has `GROQ_KEY=...` — a missing `.env` doesn't crash the server, but a malformed one might.

### "`finance_data.json` looks corrupted / `/finance` errors"

Self-heals automatically within 10 minutes if `factory_loop.js` is running (quarantines the corrupt file with a `.loop-corrupt-<timestamp>.bak` suffix, replaces it with clean empty data). To force it immediately, just restart `factory_loop.js`, or manually replace the file with `{"sales": [], "totalKDP": 0, "totalEtsy": 0, "totalGumroad": 0}`.

### "Books keep getting rejected and I don't know why"

Read `QUARANTINE.md` (repo root) — every rejection is logged there with the exact reason (`butter_price`, `not_duplicate`, `profit_score`, technical failures). This is not a bug to "fix" by lowering a threshold — see [19_Lessons_Learned/The_1299_Pricing_Trap.md](./19_Lessons_Learned/The_1299_Pricing_Trap.md): raise the value, don't lower the floor.

### "A niche keeps getting regenerated over and over"

Check `REJECTED_NICHES.md` (repo root) — if it's rejected, it should already have a 7-day cooldown via `factory_loop.js`'s circuit breaker. If it's happening via `/api/scout/run` specifically (not the autonomous loop), this is a known, still-open gap — see [19_Lessons_Learned/The_Circuit_Breaker_Discovery.md](./19_Lessons_Learned/The_Circuit_Breaker_Discovery.md).

### "I changed code and now something's broken"

- `backups/` (repo root) has timestamped copies of every file before a significant change this session made — check there first for a known-good version.
- `git log --oneline` and `git diff HEAD~1` show exactly what changed and when. `git checkout -- <file>` reverts a single file to its last committed state.
- Every Python file can be syntax-checked in isolation without running anything: `python -c "import ast; ast.parse(open('FILE.py', encoding='utf-8').read())"`. Every Node file: `node -c FILE.js`.

### "Groq is down / rate-limited / out of free quota"

Every AI call in this factory degrades gracefully rather than crashing: Scout falls back to a fixed brief (`fallbackScoutBrief()`), book content generation falls back to template content (`_fallback_book_content()`). The factory keeps producing *something* — lower quality, clearly marked `ai_used: false` — rather than stopping.

### "n8n won't start / is unreachable"

The factory is designed to not need it. `/health`'s `sensing_engine` check will show degraded, but Scout still works via Groq directly, and `market_hunter.py` doesn't touch n8n at all.

### "None of the above covers it"

Read [19_Lessons_Learned](./19_Lessons_Learned/) in full — three real incidents are documented with their root cause and fix, and the general lesson underneath: **the fix is almost always found by running the actual end-to-end path and reading real output, not by reading code in the abstract.** Reproduce the failure the same way, and the fix is usually one file away.
