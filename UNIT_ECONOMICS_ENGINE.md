# Galaxy Forge — Unit Economics Engine

**Date:** 2026-08-08 | ADR-210, Phase 20, Sections 4-5. `global_commercial_scale.unit_economics_report()` — reuses `economics.py::net_profit()` verbatim, never a second fee calculator.

---

## Section 4 — Unit Economics, real result for the current catalog (10 products)

| Field | Real coverage |
|---|---|
| Gross Revenue | Real (`pricing_usd` per product) |
| Platform Fees | Real for 5 modeled tiers (`kdp_ebook`/`kdp_paperback`/`gumroad_digital`/`premium`/`elite`) — the live Paddle channel's real fee is **not yet modeled**, disclosed honestly per product |
| Payment Fees | Folded into the platform-fee model above where applicable; no separate real payment-processor fee tracked |
| Affiliate Commissions | `UNKNOWN` — 0 real affiliate sales have ever occurred |
| Customer Acquisition Cost | `UNKNOWN` — no real paid-acquisition spend tracked anywhere |
| AI Cost | Real company-wide total exists (`data/ai_cost_log.jsonl`) but is **not attributed per-product** |
| Infrastructure Cost | `UNKNOWN` |
| Support Cost | `UNKNOWN` |
| Refund Cost | Real — `$0` (product_master_catalog.py's own real `refunds_usd`, confirmed 0 real refunds ever) |
| Contribution Margin | Real where the platform-fee model applies, `UNKNOWN` otherwise |
| Net Revenue | Real `$0` for every product with 0 real sales; `UNKNOWN` beyond gross for the 0 products with a real sale |
| Lifetime Value | `NOT_MEASURABLE` — 0 real repeat customers exist |

**Never invented**: no cost field above is estimated or assumed — every `UNKNOWN` reflects a real, confirmed absence of tracking, not a placeholder waiting to be filled with a plausible number.

## Section 5 — Scale Economics (citation, not duplicated)

| Metric | Real source |
|---|---|
| Revenue per AI cost / per product / per platform / per customer | `capital_efficiency.py::capital_efficiency_report()` (Phase 16, ADR-206) — reused directly, not recomputed |
| Revenue per market | `UNKNOWN` — no real per-market revenue split exists (0 real international sales) |
| Revenue per acquisition channel | `commercial_acquisition.py::customer_acquisition_report()` — real per-channel structure, `INSUFFICIENT_DATA`/`NO_REAL_SOURCE` for CAC/LTV per channel (no web analytics wired) |
| Revenue per unit of human effort | `UNKNOWN` — no real time-tracking exists |
| Automation savings | `UNKNOWN` — no real baseline "manual cost" exists to compare against |
| Scaling cost / Expected marginal return | Not computable — would require the Unit Economics fields above, most of which are honestly `UNKNOWN` |

**"The objective is not maximum revenue, it is maximum sustainable economic value"** — honored literally: this document reports real gaps rather than filling them with a number that would make the objective look closer than it is.

---

*See also: `GLOBAL_SCALE_ENGINE.md`, `capital_efficiency.py`.*
