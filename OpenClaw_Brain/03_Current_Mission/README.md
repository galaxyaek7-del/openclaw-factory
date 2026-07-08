# 03 — Current Mission (Day 08, 2026-07-09)

*Kept in sync with [FACTORY_STATUS.md](../../FACTORY_STATUS.md) — that file is the source of truth; this is a Brain-native pointer to it, not a duplicate.*

## Where the factory stands right now

**book_engine is the only active track.** Today's mission, concretely: get one Scout-generated book to actually clear both Quality Council gates (Technical + Commercial) and publish — not just get generated. As of Day 08, the factory also actively *discovers* new candidate niches on its own (`market_hunter.py`) rather than only reacting to what n8n/Scout happen to bring it, and now honestly reports on its own health and growth every day — see [Self_Awareness.md](./Self_Awareness.md).

## What shipped this week (Day 06–08)

| Component | Council it belongs to |
|---|---|
| `cover_designer_v2.py` — real 70/20/10 covers, fixed Arabic-shaping bug | Engineering |
| SUBTITLE placeholder fix | Engineering |
| `profit_oracle.py` — Golden Hunter profit scoring | Golden Hunter |
| `OPENCLAW_OS_CONSTITUTION.md` — supreme law installed | — (governs all Councils) |
| `inspectors.py` — Dual Inspection (Technical + Commercial) | Quality |
| Circuit breaker (`REJECTED_NICHES.md`) | Anti-Fragility / Digital Sanitation |
| Value-based pricing fix (Scout prompt + `butter_price()`) | Golden Hunter / Smart Publishing |
| This Brain | Knowledge |
| `market_hunter.py` (Day 08) — Brain-aware candidate discovery | Golden Hunter |

## The mission's real current blocker (as of this writing)

Fixed today: Scout's default pricing ($9.99–$14.99) failed the $30 Butter floor on every book. See [19_Lessons_Learned/The_1299_Pricing_Trap.md](../19_Lessons_Learned/The_1299_Pricing_Trap.md) for the full story — Groq's prompt now asks for value-based premium pricing directly, and `profit_oracle.butter_price()` repriced anything still under $30 (as long as the niche itself wasn't genuinely weak).

**What's still open:** the circuit breaker (`REJECTED_NICHES.md`) still only guards `factory_loop.js`'s autonomous `hunt()` loop and (as of Day 08) `market_hunter.py`'s own discovery — `/api/scout/run` (the button a human or n8n actually triggers) still has no such memory. See [02_Roadmap](../02_Roadmap/).

**Day 08 addition:** `market_hunter.py` now actively discovers new candidate niches (curated categories × seasonality, see [08_Market_Intelligence](../08_Market_Intelligence/)) instead of waiting for n8n or Scout — and consults `REJECTED_NICHES.md`, `QUARANTINE.md`, and the generation log *before* scoring anything, per CONSTITUTION.md §19.

## Traceability anchor

This file is the "Current Mission" link in the Brain's Vision → Constitution → Architecture → Cells → Results → Lessons chain (see [MASTER_INDEX.md](../MASTER_INDEX.md)). Update it every time `FACTORY_STATUS.md` gets a new Day-N summary — don't let the two drift.
