# 05 — Living Cells

Each cell scored honestly against OPENCLAW_OS_CONSTITUTION.md's Living Cell checklist (see [04_Architecture](../04_Architecture/)) — including where a cell falls short, not just where it succeeds.

## market_hunter (`market_hunter.py` — the Golden Hunter, Day 08)

| Property | Status | Note |
|---|---|---|
| Independent | ✅ | Standalone script; `factory_loop.js` spawns it as a subprocess, no dashboard dependency |
| Reusable | ✅ | `hunt_market()`/`_generate_candidates()` aren't hardcoded to one category list |
| Scalable | ⚠️ Unproven | Curated candidate pool is small (10 seeds); untested at a larger candidate volume |
| Secure | ✅ | No secrets, no network calls |
| Observable | ✅ | `market_hunter_runs.log` (every run) + appends to `OPPORTUNITIES.md` with clear attribution |
| Documented | ✅ | This entry + [08_Market_Intelligence](../08_Market_Intelligence/) + module docstring |
| Recoverable | ✅ | Guards `profit_oracle`/`inspectors` imports; a missing Brain check degrades to "not found" rather than crashing |

**The one property this cell exists specifically to strengthen:** it's the first component to consult *three* separate rejection/duplicate memories (`REJECTED_NICHES.md`, `QUARANTINE.md`, generation-log duplicates) before doing any work — the concrete implementation of CONSTITUTION.md §19's "always consult the Knowledge Brain first."

## Scout (`server.js` — `/api/scout/run`, `scoutBriefPrompt()`)

| Property | Status | Note |
|---|---|---|
| Independent | ⚠️ Partial | Runs inside `server.js`, not its own process — a Scout bug can affect the dashboard |
| Reusable | ✅ | `scoutBriefPrompt()`/`parseScoutBrief()` are generic, not hardcoded to one niche type |
| Scalable | ⚠️ Unproven | Never load-tested; single Groq call per run |
| Secure | ✅ | Guarded Groq key check, falls back to `fallbackScoutBrief()` if missing |
| Observable | ✅ | Logs every run to `scout_runs.log` (JSONL) |
| Documented | ✅ | This entry + inline comments in `server.js` |
| Recoverable | ✅ | Falls back to a fixed brief if Groq fails or returns unparseable text |

## profit_oracle (`profit_oracle.py`)

| Property | Status | Note |
|---|---|---|
| Independent | ✅ | Standalone script, importable or CLI-runnable, no reportlab dependency |
| Reusable | ✅ | `score_opportunity(niche)` and `butter_price(niche)` take any niche string |
| Scalable | ✅ | Pure computation, no I/O bottleneck |
| Secure | ✅ | No secrets, no network calls (deliberately — see honesty notes in the file's docstring) |
| Observable | ✅ | Writes `GOLDEN_OPPORTUNITIES.md` + `golden_opportunities.json` every `--run` |
| Documented | ✅ | Extensive inline docstrings explaining which signals are real vs. heuristic |
| Recoverable | ✅ | Guards `niche_validator_v2` import; degrades to heuristic scoring if unavailable |

## inspectors (`inspectors.py` — Quality Council)

| Property | Status | Note |
|---|---|---|
| Independent | ✅ | Standalone module; `book_generator.py` guards its import |
| Reusable | ✅ | `inspect_technical()`/`audit_commercial()` take any pdf/cover/niche/price |
| Scalable | ⚠️ Unproven | Pixel-scanning a 1600×2560 cover per book — fine at today's volume, untested at scale |
| Secure | ✅ | No secrets; reads only local files it's given |
| Observable | ✅ | `inspections.log` (every run) + `QUARANTINE.md` (failures) + `alerts.json` (critical failures) |
| Documented | ✅ | This entry + module docstring explicitly distinguishing real checks from documented estimates |
| Recoverable | ✅ | "Fail closed" by design — an inspection exception is treated as a rejection, never a silent approval |

## Circuit Breaker (`factory_loop.js` — `REJECTED_NICHES.md`)

| Property | Status | Note |
|---|---|---|
| Independent | ✅ | Lives inside `factory_loop.js`, its own process, separate from the dashboard |
| Reusable | ⚠️ **Partial — a known, real gap** | Only wired into `hunt()`'s `triggerGenerateBook()`; `/api/scout/run` doesn't share this memory. See [19_Lessons_Learned/The_Circuit_Breaker_Discovery.md](../19_Lessons_Learned/The_Circuit_Breaker_Discovery.md) |
| Scalable | ✅ | O(n) file scan, fine at current rejection volume |
| Secure | ✅ | No secrets |
| Observable | ✅ | `REJECTED_NICHES.md` + every skip logged to `factory_loop.log` |
| Documented | ✅ | This entry + inline comments explaining the root cause it fixes |
| Recoverable | ✅ | Missing `REJECTED_NICHES.md` degrades to "nothing rejected yet," never a crash |

## What this table is for

Anyone (human or a future agent reading this Brain) deciding "should I build on top of X" should check this table first — the ⚠️ rows are exactly the places where doing so requires extra care or where fixing the gap is the more valuable next task.
