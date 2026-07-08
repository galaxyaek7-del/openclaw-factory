# 15 — Finance

## Data structure (`finance_data.json`, repo root)

```json
{"sales": [...], "totalKDP": 0, "totalEtsy": 0, "totalGumroad": 0}
```

Read/written synchronously by `server.js`. Self-healing: `factory_loop.js`'s `healFinance()` quarantines a corrupted `finance_data.json` (renames it with a `.loop-corrupt-<timestamp>.bak` suffix) and replaces it with clean empty data, rather than crashing or losing the whole file.

## Real current numbers

**$0.00 total revenue recorded, across every platform, to date.** This is the single most important fact this Knowledge Base can state plainly: the factory has generated real books, but has not yet sold one. Every quality/pricing gate this project has built (Butter Principle, Dual Inspection) exists to make the *next* book worth actually trying to sell — not to celebrate generation volume for its own sake.

## The `finance` agent

`AGENT_PROMPTS.finance` (see [09_Prompt_Library](../09_Prompt_Library/)) gives pricing-strategy and margin analysis on request (KDP 35%/70% royalty comparison, break-even calculation) — advisory content only, not connected to real sales data or `finance_data.json`.

## Related

- [19_Lessons_Learned/The_1299_Pricing_Trap.md](../19_Lessons_Learned/The_1299_Pricing_Trap.md) — the pricing fix that's supposed to make the first real dollar possible
