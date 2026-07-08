# 03 — Current Mission (Day 07, 2026-07-08)

*Kept in sync with [FACTORY_STATUS.md](../../FACTORY_STATUS.md) — that file is the source of truth; this is a Brain-native pointer to it, not a duplicate.*

## Where the factory stands right now

**book_engine is the only active track.** Today's mission, concretely: get one Scout-generated book to actually clear both Quality Council gates (Technical + Commercial) and publish — not just get generated.

## What shipped this week (Day 06–07)

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

## The mission's real current blocker (as of this writing)

Fixed today: Scout's default pricing ($9.99–$14.99) failed the $30 Butter floor on every book. See [19_Lessons_Learned/The_1299_Pricing_Trap.md](../19_Lessons_Learned/The_1299_Pricing_Trap.md) for the full story — Groq's prompt now asks for value-based premium pricing directly, and `profit_oracle.butter_price()` repriced anything still under $30 (as long as the niche itself wasn't genuinely weak).

**What's still open:** the circuit breaker (`REJECTED_NICHES.md`) only guards `factory_loop.js`'s autonomous `hunt()` loop — `/api/scout/run` (the button a human or n8n actually triggers) has no such memory yet. See [02_Roadmap](../02_Roadmap/).

## Traceability anchor

This file is the "Current Mission" link in the Brain's Vision → Constitution → Architecture → Cells → Results → Lessons chain (see [MASTER_INDEX.md](../MASTER_INDEX.md)). Update it every time `FACTORY_STATUS.md` gets a new Day-N summary — don't let the two drift.
