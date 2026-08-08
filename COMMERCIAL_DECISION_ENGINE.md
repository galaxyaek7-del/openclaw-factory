# Galaxy Forge — Commercial Decision Engine

**Date:** 2026-08-08 | ADR-217, Phase 27, Sections 2-3.

---

## What this round found before writing any code

Near-total overlap with `goos.py::rank_build_candidates()`/`evaluate_dimensions()` (real global opportunity ranking), `capital_allocation_engine.py::opportunity_cost()` (real resource-allocation citation), `product_innovation_engine.py`'s real 6 validation gates (Phase 23). This module's real job: relabel these onto the directive's decision shape.

## Section 2 — Decision Engine (real citation over 12 named categories)

Products/Platforms/Markets/Channels/Partners/Affiliates/Prices/Campaigns/Offers/Subscriptions/Licensing/Enterprise — every category already has a real, dedicated real classifier this session: `product_allocation()`, `platform_allocation()`, `market_allocation()`, `channel_optimization()`, `partner_allocation()`, `price_optimization_status()`, `golden_hunter_roi_preacceptance()`. Never a fabricated Expected Revenue/Net Revenue/Cost — every field cites a real function or reports `UNKNOWN`.

## Section 3 — Commercial Opportunity Score (11 named, explainable)

`commercial_opportunity_score(niche)` — real citation over `goos.py::evaluate_dimensions()`'s 20 real dimensions + `product_innovation_engine.py`'s 6 real validation gates. **Never a single unexplained score** — verified by a dedicated regression test confirming no bare `score` key is ever returned, only decomposed `components`.

---

*See also: `REVENUE_OPTIMIZATION_ENGINE.md`, `COMMERCIAL_QUEUE_ENGINE.md`.*
