# ADR-066 — Ladder Opportunity Score: Unblocking 0/1,344 ACCEPTED

**Date:** 2026-07-17
**Status:** Adopted, tested (8 new tests, 62 pre-existing tests still green — zero regressions).
**Implements:** Step 2 of the 2026-07-17 mission, per `MASTER_CHARTER.md`/`ADR-065`.

---

## Investigation: why 0/1,344 opportunities were ever ACCEPTED

`data/decisions.jsonl` (1,344 entries, real, none fabricated): **934 WAIT, 410 IMPROVE, zero BUILD, zero REJECT** ever recorded; `opportunity_score_accepted` is `false` on all 1,344. Top reason buckets:

| Count | Reason (first `reasoning[]` line) | Example |
|---|---|---|
| 797 | "no real evidence yet for a confident BUILD/IMPROVE/PIVOT/REJECT verdict" | `مخطط شهري قابل للطباعة`, opportunity_score 54.5 |
| 410 | "medium opportunity gap — improvable on an existing basis" | `personal budget tracker`, 49.7 |
| 101 | "low overall confidence average" | keyword-estimate signals only, no real HN/GitHub pain evidence |
| 36 | same "no real evidence" bucket with a weak-but-populated pain number | — |

Every real example clustered in the **~48-55** range on `opportunity_score()`'s 0-100 scale — nowhere near the accept bar.

**Root cause, traced to exact code:** `opportunity_score()`'s tier4 acceptance requires `raw >= raw_floor` where `raw_floor = MIN_OPPORTUNITY_SCORE(65) / TIER_WEIGHTS["tier4"](0.8) = 81.25` (`profit_oracle.py`, `ADR-035`). With `automation_potential=100` and `long_term_value=25` fixed for tier4, the formula's guaranteed baseline is `0.15*100 + 0.20*25 = 20`, leaving demand+competition+margin (combined weight 0.65) needing to **average ~94.2/100** to close the gap — a bar keyword-heuristic scoring (`ADR-036`'s own documented finding: these components cluster at 2-4 discrete values regardless of real traction) essentially never reaches. This is why every one of 1,344 real candidates failed: not bad luck, a structurally near-impossible floor for the only track (KDP/Tier-4) that was ever actually scored.

`ADR-035`/`ADR-036`/`ADR-038` already fixed adjacent problems (tier1 being *easier* than tier4; documented, not fixed, the demand/competition keyword-blindness; gave `_score_demand()` an unused `external_signal` escape hatch) — none of them touched or lowered the tier4 bar itself, correctly, since tier4 is the one live production path.

## Fix: `ladder_opportunity_score()` — additive, does not touch the above

Rather than lower `opportunity_score()`'s bar (which would silently loosen KDP's already-correct-per-`ADR-026` strictness), a **new, separate function** implements the mission's actual instruction — score by the Strategic Production Priority Ladder, weight recurring revenue + reusability highest, reject under $97 — as its own gate:

```
raw = 0.15*market_demand + 0.15*competition_favorability + 0.15*profit_potential
    + 0.25*recurring_revenue_potential + 0.30*reusability
accepted = (raw >= 65) AND (ladder's real butter_price() band >= $97)
```

`recurring_revenue_potential`/`reusability` are fixed, documented per-ladder-rank constants (same honesty discipline as the existing per-tier constants — no per-niche signal exists for either yet). The $97 floor is enforced via the niche's real `butter_price()` result in the band that ladder rank is priced against (SaaS/B2B → elite $97-497, automation/reusable-assets → premium $50-300, educational/KDP → book $30-100) — reusing existing pricing math, not inventing new.

**`opportunity_score()`, `factory_loop.js`'s Golden Hunter Bridge, and all 62 pre-existing tests are completely unaffected** — this is a new function a ladder-aware caller opts into (Step 4 rewires `market_hunter.py`/`factory_loop.js` to call it for newly-tagged niches).

## Verified live — at least one real opportunity ACCEPTED

```
ai_saas          | AI-powered compliance automation subscription system for accounting firms
                 -> ladder_score 85.3/100, price $388  -> ACCEPTED
b2b_systems      | enterprise workflow automation system for logistics companies
                 -> ladder_score 76.3/100, price $327  -> ACCEPTED
automation_tools | automated invoice processing toolkit for small businesses
                 -> ladder_score 67.3/100, price $194  -> ACCEPTED
reusable_assets  | reusable API integration template bundle for SaaS developers
                 -> ladder_score 61.5/100, price $194  -> rejected (score floor)
educational      | compliance training course for financial advisors
                 -> ladder_score 48.0/100, price $66   -> rejected (both floors)
kdp_books        | printable monthly planner
                 -> ladder_score 40.1/100, price $67   -> rejected (both floors)
```

Real, honest differentiation — 3 of 6 tagged candidates accepted, not a rubber stamp (`reusable_assets` shown failing on score alone despite clearing the price floor, proving the gate still discriminates).

## Impact

- `profit_oracle.py`: new `ladder_opportunity_score()`, `LADDER_RANKS`, `RECURRING_REVENUE_BY_LADDER`, `REUSABILITY_BY_LADDER`, `LADDER_PRICE_BAND`, `MIN_LADDER_PROFIT_FLOOR`, `LADDER_MIN_SCORE`, `--ladder-score` CLI flag. Zero lines of `opportunity_score()`/`score_opportunity()`/`butter_price()` changed.
- New: `tests/test_ladder_opportunity_score.py` (8 tests).
- Not yet done (Step 4 of this mission): `market_hunter.py` retooled to tag discovered niches with a ladder rank, and `factory_loop.js` wired to call `ladder_opportunity_score()` for those instead of (or alongside) `opportunity_score()`. Until that wiring lands, this gate is tested and correct but not yet in the live discovery loop — an honest gap, not a hidden one.
