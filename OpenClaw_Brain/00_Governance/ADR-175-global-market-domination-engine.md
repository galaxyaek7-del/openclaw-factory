# ADR-175 — Global Market Domination Engine

**Date:** 2026-08-05
**Status:** Adopted. A real consolidation over already-real discovery/evaluation systems; 6 of 8 named regions honestly not built.

---

## The directive (verbatim, condensed)

> GALAXY FORGE — GLOBAL MARKET DOMINATION ENGINE
>
> Engineer a permanent intelligence system capable of continuously discovering the highest-value digital business opportunities across the entire world — North America, South America, Europe, Middle East, Africa, Asia, Oceania, Global online markets. Prioritize B2B, professional tools, AI-powered software, premium digital assets, business automation, decision systems, enterprise workflows, knowledge systems, professional education, high-value subscriptions. For every opportunity estimate: problem severity, willingness to pay, competition level, difficulty of copying, scalability, recurring revenue potential, global demand, automation potential, strategic importance, long-term asset value.

## The real conflict, not re-raised a 4th time

Real, per-country/regional market intelligence has already been asked for — and declined the same way — at least 3 times this session: **GCID** (ADR-148, zero code), the **Global Affiliate Commerce Engine** (ADR-152, zero code), and `growth_stages.py`'s Stage 4 condition (permanently unmet by founder policy, not data). The founder's own standing decision (2026-07-23, restated identically each time): zero real local-market data connector exists for any country beyond this factory's global/English-language sources, re-triggered only at (a) the first real dollar, or (b) a real local connector becoming available. Neither has happened — confirmed again by direct search this round. Applying that standing, 3x-confirmed policy directly here (the same judgment already applied to `GOS`, ADR-172, and the `Galaxy Evolution Report`, ADR-173, both minutes-to-hours earlier the same session): no fourth `AskUserQuestion` for a question already answered three times.

## The genuine coincidence: this directive's 10 evaluation dimensions are GOOS's, verbatim

`goos.py` (ADR-171, built earlier the same session) already names 10 of its own 20 real evaluation dimensions almost word-for-word identically to this directive's list: `real_customer_pain`, `willingness_to_pay`, `competition_level`, `difficulty_of_copying`, `scalability`, `recurring_revenue_potential`, `global_demand`, `automation_potential`, `strategic_fit` (strategic importance), `long_term_asset_value`. This round reuses `goos.evaluate_dimensions()` verbatim — no second evaluation engine.

## What was found real and global today

`market_domination_engine.py::global_source_status()` cites `multi_source_intelligence.registry`'s real connector registry, live-confirmed: **8 of 11 registered connectors are real and query-capable** — `amazon`, `arxiv`, `etsy`, `github`, `gumroad`, `hacker_news`, `public_search`, `stack_overflow`. This is a real, previously-undercited asset: broader than the "only HN + GitHub" figure cited in some earlier CLAUDE.md sections (which described a narrower, customer-pain-evidence-specific claim). `reddit`/`product_hunt`/`google_trends` remain honestly `unavailable`.

`profit_oracle.py::LADDER_RANKS` (`["ai_saas", "b2b_systems", "automation_tools", "reusable_assets", "educational", "kdp_books"]`) already encodes exactly the directive's own priority order (AI software/B2B/automation ranked above templates/education/books) — reused verbatim as the real ranking key, never a new priority scheme invented.

## What was built

**`market_domination_engine.py`** (new, root):

- `REGIONAL_COVERAGE` — all 8 named regions, honestly tagged: `global_online_markets` REAL (the 8 real connectors above), `north_america` PARTIAL (those same sources are US-hosted/English-default but not exclusive), the other 6 `NOT_MEASURABLE`, each citing the real 2026-07-23 standing deferral.
- `global_source_status()` — real citation of `multi_source_intelligence.registry.get_connectors()`.
- `high_value_candidates()` — real candidate discovery across **all 6 real ladders** (not automation-only), ranked by `profit_oracle.LADDER_RANKS`'s real priority order.
- `evaluate_candidate()` — delegates to `goos.evaluate_dimensions()` verbatim.
- `build_market_domination_dashboard()` — the one real aggregator, computing candidates and source status exactly once each.

**`automation_opportunity_scanner.py`** (ADR-164) gained a genuinely additive, backward-compatible change: `_seed_candidates()`/`_historical_candidates()` now accept an optional `ladders` parameter (`None` = no filter, i.e. every real ladder). `scan_candidates()` (the existing automation-only caller) now explicitly passes `ladders=_AUTOMATION_LADDERS`, preserving its exact original behavior — verified: all 17 pre-existing ADR-164 tests still pass unmodified. This is real reuse, not a duplicate discovery mechanism sitting beside the original.

**Mission Control:** `market-domination-dashboard` (`SERVICE_REGISTRY`) + one panel in the existing Executive Overview group.

## What is explicitly NOT built

- No real per-country/regional data connector for any of the 6 `NOT_MEASURABLE` regions — the founder's own standing, 3x-reconfirmed policy.
- No fabricated "global coverage" percentage blending real and non-existent regional signal into one number.
- No new evaluation engine — every dimension delegates to `goos.py`.
- No new candidate-discovery mechanism — `automation_opportunity_scanner.py`'s real functions are extended, not duplicated.
- Never triggers a new live evaluation cycle (same passive-only discipline as ADR-164, proven by a mocked `run_hunt()`-never-called test).

## Validation

`python -m unittest tests.test_market_domination_engine -v` — 12/12 passing: all 8 regions present and honestly tagged (each `NOT_MEASURABLE` reason independently citing the real 2026-07-23 deferral, not relying on a sibling entry for context); the real connector total (11) and the 3 honestly-`unavailable` sources proven; candidates proven ranked by real ladder priority and never scoped to automation-only; `evaluate_candidate()` proven to delegate to `goos.evaluate_dimensions()` via a call-count assertion; the dashboard proven to compute candidates/sources exactly once each. `python -m unittest tests.test_automation_revenue_engine -v` — 17/17 still passing after the `ladders` parameter addition, confirming zero regression to ADR-164's own behavior. Live-verified end-to-end via a disposable server: `GET /api/v1/market-domination-dashboard` returns real, ranked, GOOS-evaluated candidates with honest regional disclosure.
