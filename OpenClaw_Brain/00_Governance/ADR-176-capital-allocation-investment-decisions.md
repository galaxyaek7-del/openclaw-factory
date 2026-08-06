# ADR-176 — Capital Allocation Engine: Investment Decisions & Portfolio Balance

**Date:** 2026-08-05
**Status:** Adopted. Extends `enterprise_capital_allocation.py` — no third parallel Capital Allocation Engine.

---

## The directive (verbatim, condensed)

> GALAXY FORGE — CAPITAL ALLOCATION ENGINE
>
> Design and engineer the Capital Allocation Engine — the financial brain of the company, deciding where every hour, dollar, API call, engineer, AI model and system effort should be invested. Evaluate every project on 20 named dimensions (Expected Monthly/Annual Revenue, Time to First Sale, Implementation/Maintenance Cost, Automation Potential, Recurring Revenue Potential, Scalability, CLV, Competitive Advantage, Market Size, Difficulty to Copy, Strategic Importance, Technical/Business/Legal Risk, Customer Trust Impact, Knowledge Asset Value, Compounding Value, Opportunity Cost). Every project gets one decision: INVEST NOW / BUILD LATER / EXPERIMENT / REJECT, with written reasoning. Portfolio thinking, not single-product optimization. Recommend where the next hour/day/week/month should be invested. Self-improve from prior allocation decisions.

## The name itself is the overlap signal

This directive names itself "Capital Allocation Engine" — the exact same name as two already-real, already-shipped modules this session: `capital_allocation_engine.py` (ADR-139, 2026-07-29, a real 14-dimension Investment Score) and `enterprise_capital_allocation.py` (ADR-165, 2026-07-31, extending it to 15 dimensions plus a real 10-resource allocation map, capacity utilization, and a "Projects Overfunded" heuristic). Research found **17 of the 20 newly-named dimensions already directly covered** by those two modules. Building a third, independent "Capital Allocation Engine" would be exactly the duplication this session has declined in every prior round that hit this pattern (Executive Brain, GFOS, GOS, Galaxy Evolution Report, Market Domination Engine — 5 prior rounds, all resolved the same way). Applied that judgment directly here — a 6th consecutive round — without a fresh `AskUserQuestion`.

## The 3 genuinely new dimensions, and why 2 of the "revenue" ones can't be answered the way asked

**Expected Monthly Revenue, Expected Annual Revenue, Time to First Sale** — all three are honestly `NOT_MEASURABLE`, and not merely because of missing data: this factory's real `expected_revenue` field (`capital_allocation_engine.py`) is explicitly documented as **retrospective** — real closed-sale revenue to date, "never a forecast." Deriving "Expected Annual Revenue" by multiplying that figure by 12 would not fill a gap, it would fabricate a forward projection out of a backward-looking number, exactly what this factory's Truth First Constitution (ADR-160) forbids. Time to First Sale has zero real historical duration data anywhere in this factory, the same disclosed-gap class as every other effort-estimate this session has hit.

**Customer Trust Impact** and **Compounding Value** had no prior citation and were built as thin, real functions: `customer_trust_impact()` delegates to `brand_dna.py::validate_customer_facing_text()` (ADR-170) — never a second trust-scoring mechanism. `compounding_value()` is a disclosed, real average of 2 already-real Investment Score dimensions (`knowledge_reuse`, `long_term_asset_value`) — never a 3rd, independent computation; "compounding" is treated as a real property of those two signals together, not a new one.

## The decision output: a real relabeling, not a new decision engine

`capital_decision(niche)` maps `scheduler.py::decide_next_actions()`'s already-real 5 buckets onto the directive's 4 named values: `run_now`/`accelerate` → **INVEST NOW**, `cancel`/`stop` → **REJECT**. **EXPERIMENT** is the one genuinely new distinction — within the real `wait` bucket, a niche whose own real decision-confidence level (already computed by `decision_engine`'s evaluation pipeline) is low or medium is tagged **EXPERIMENT** rather than **BUILD LATER** — a real, disclosed heuristic over an already-real field, never a fabricated split.

## What was built

**`enterprise_capital_allocation.py`** gained:

- `_forward_looking_dimensions()` — the 3 honestly `NOT_MEASURABLE` dimensions above.
- `customer_trust_impact()`, `compounding_value()` — the 2 genuinely new dimensions.
- `capital_decision()` — the real INVEST NOW/BUILD LATER/EXPERIMENT/REJECT relabeling.
- `portfolio_balance()` — real aggregation of ACCEPTED opportunities by `profit_oracle.LADDER_RANKS`'s already-real recurring-vs-one-time character (`ai_saas`/`b2b_systems`/`automation_tools` = recurring, `kdp_books`/`reusable_assets`/`educational` = closer to one-time). "High-risk innovation"/"stable cash-flow"/"long-term strategic asset" are honestly `NOT_MEASURABLE` — no real per-niche risk-maturity signal exists to split them further, disclosed rather than guessed from the same two ladder-derived buckets.
- `resource_optimization_recommendation()` — real citation of `strategic_planning.py::rolling_roadmap()` (ADR-159). "Next hour" has no real signal finer than "Today" anywhere in this factory — both cite the identical real bucket, disclosed rather than invented.
- `self_improvement_sources()` — pure citation of the same 3-4 real learning mechanisms this session has already cited repeatedly (`decision_engine/learning.py::recalibration_report()`, `evolution_queue.py`'s real outcome measurement, `global_opportunity_exchange.py`'s concentration risk, `competitor_discovery.py`/`market_hunter.py`'s real live ingestion) — never a 4th, competing learning loop.
- `build_capital_decisions_report()` — the one real aggregator.

**Mission Control:** `capital-decisions-report` (`SERVICE_REGISTRY`) + one panel in the existing Executive Overview group.

## Validation

`python -m unittest tests.test_enterprise_capital_allocation -v` — 30/30 passing (18 pre-existing + 12 new): the 3 forward-looking dimensions proven `NOT_MEASURABLE`, with a dedicated regression proving `expected_annual_revenue` is never derived from a monthly figure; `capital_decision()` proven against all 5 real scheduler buckets including the real confidence-based EXPERIMENT split (both high- and low-confidence paths); `portfolio_balance()` proven to never fabricate the 3 risk-maturity buckets; `compounding_value()`/`customer_trust_impact()` proven against both real-signal and no-signal cases. Live-verified end-to-end via a disposable server: `GET /api/v1/capital-decisions-report` returns real, honest decisions — every real niche today is REJECT, an accurate reflection of the factory's current real state (0 ACCEPTED opportunities).
