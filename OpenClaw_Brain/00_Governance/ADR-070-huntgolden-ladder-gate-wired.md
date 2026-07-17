# ADR-070 — Wiring the Ladder Gate into the Automatic Golden Hunter Tick

**Date:** 2026-07-17
**Status:** Adopted, tested (470 Python tests unchanged/green + 51 in `test_factory_loop_golden.js`, zero regressions), **verified live**.
**Closes the gap:** `ADR-069` disclosed that `factory_loop.js`'s automatic 10-minute tick (`huntGolden()`) still read `golden_opportunities.json` via the old, ladder-unaware `score_opportunity()`, so the newly-accepted AI SaaS/B2B opportunities never actually became the tick's top pick. This ADR wires it.

---

## The fix, in three pieces

**1. `profit_oracle.run_oracle()`** — new `_read_opportunities_with_ladder()` (a *separate* reader from `_read_opportunities()`, which `real_world_mode/signal_intake.py` already depends on returning plain niche strings — extending it in place would have broken that real consumer for no benefit). Extracts the `ladder=<rank>` tag `market_hunter.py`'s `_append_to_opportunities()` already writes into `OPPORTUNITIES.md`'s reason text. For every niche carrying a recognized ladder tag, `run_oracle()` now *also* computes `ladder_opportunity_score()` and merges `ladder`/`ladder_score`/`ladder_accepted`/`ladder_price` into that niche's result — `score_opportunity()` still runs for every niche unchanged, so nothing about the existing human report or any pre-ladder consumer changes.

**Sort order changed**: every `ladder_accepted=True` result now sorts before every other result (ranked among themselves by `ladder_score`), falling back to the original `profit_score`-descending order otherwise. A file with zero ladder-tagged entries sorts exactly as before.

**2. `factory_loop.js`'s `pickTopGoldenOpportunity()`** — now prefers `ladder_accepted===true` entries (highest `ladder_score` among them) over anything else, regardless of `profit_score`. This is the concrete fix for the real, confirmed case: the AI compliance-automation niche scores `profit_score=69` under the old scorer while an old KDP printable scores `71` — without this change, the KDP niche would still win the pick even with the new gate in place downstream. Entries with no ladder fields (every pre-ladder `golden_opportunities.json`, every existing test fixture) fall through to the exact original behavior.

**3. `factory_loop.js`'s `huntGolden()`** — new `getLadderOpportunityScore(niche, ladder)` (same spawn pattern as `getOpportunityScore()`, calls `profit_oracle.py --ladder-score`, returns the identical `{ok, score, accepted, reason, components}` shape). When the picked opportunity carries a `ladder` tag, the gate now calls this instead of the old `getOpportunityScore(niche, {tier:'tier4'})` — every downstream consumer (skip-detail logging, `notifyGoldenHunterAccepted()`) is unchanged since the shape is identical. Opportunities with no ladder tag keep using the original gate.

## Verified live — the actual next tick's top pick

Re-ran `python market_hunter.py --run` (regenerates `golden_opportunities.json` through the now-ladder-aware `run_oracle()`), then ran the real `huntGolden(true)` function directly (no mocking):

```
{
  "action": "skipped",
  "detail": "[dry-run] كان سيُنتَج: \"AI-powered compliance automation subscription system
             for accounting firms\" (score 69, GOOD) — FACTORY_AUTO_PRODUCE غير مفعَّل"
}
```

**The top pick is the real AI SaaS opportunity (ladder_score 85.3, $388) — not an old KDP niche.** ("dry-run"/"skipped" here means only `FACTORY_AUTO_PRODUCE` is off in this shell, the same safe default every tick uses; it is not a rejection — the opportunity cleared the ladder gate and would have been produced with that flag set.) `golden_opportunities.json`'s real top 5 entries after this run: `ai_saas` (85.3) → `ai_saas` (79.6) → `b2b_systems` (76.3) → `b2b_systems` (76.3) → next non-ladder entry — confirmed via direct inspection of the regenerated file.

The real `data/golden_hunter_events.jsonl` also now shows the notify call correctly reporting `"N8N_TELEGRAM_WEBHOOK_URL not configured"` (not the old, wrongly-hardcoded `"N8N_PRODUCTION_WEBHOOK_URL"` string from before `ADR-069`'s `envVarName` fix) — end-to-end evidence the whole chain from `ADR-065` through this ADR is now internally consistent.

## Impact

- `profit_oracle.py`: `_read_opportunities_with_ladder()` (new), `run_oracle()` (ladder-aware scoring + sort).
- `factory_loop.js`: `pickTopGoldenOpportunity()` (ladder preference), `getLadderOpportunityScore()` (new), `huntGolden()`'s gate branches on `top.ladder`.
- New tests: 7 in `tests/test_factory_loop_golden.js` (ladder-preference cases + real `getLadderOpportunityScore()` subprocess calls, suite now 51 total, up from 44). Python suite unaffected in count (470, all still green) — this fix has no new dedicated Python-side tests beyond the existing `profit_oracle`/`ladder_opportunity_score` suites already covering the underlying functions it composes.
- Still not done (unchanged from `ADR-069`): pricing/content-type dispatch for a ladder-tagged production still goes through `briefFromGoldenOpportunity()`'s original book-band pricing and `generate_book()`'s AI-generated-book path when `FACTORY_AUTO_PRODUCE=true` — not yet routed to `generate_product_package()`'s techdoc pricing/section-skeleton. This ADR fixes *which opportunity gets selected and gated*; producing it in the right format/price band once selected is a separate, still-open next step.
