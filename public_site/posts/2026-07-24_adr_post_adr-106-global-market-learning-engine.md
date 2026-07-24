# Building a Global Market Learning Engine (Market Memory + Commercial Evolution)

We've started building a system that learns from every sale, failure, visitor, refund, and opportunity in OpenClaw. The system will capture 17 commercial dimensions for each event, track 10 minimum regions and a China-specific intelligence domain, produce a monthly Commercial Evolution report, and generate autonomous recommendations.

Our approach is guided by the founder's explicit constraint: "No synthetic data. No assumptions. Only verified commercial evidence."

Before we began building, we identified three areas to address:

1. **Sequencing**: Fix the existing `poll_sales.py` script to link real sales to niches.
2. **Market Memory scope**: Focus on real capture schema and read-only wiring into the 7 named systems, with evidence-gated recommendations that output nothing until real thresholds are met.
3. **10 regions + China Specialization**: As per ADR-103, defer this expansion ask until we have real local data connectors and sales.

We discovered the following:

- A real sale→niche matcher already existed (`decision_engine/feedback.py::sync_outcomes()`).
- Paddle's real API provides commercial dimensions like price, time, country-via-billing-address, and refund-via-adjustments-API.
- However, we found a gap: the factory's highest-value live channel (Paddle) has no real profit formula configured.

**What was built:**

1. We fixed the existing `sync_outcomes()` function to call `market_evidence.record_evidence(niche, "closed_sale", ...)` when a matched sale exists.
2. We created `market_memory.py` (the real Market Memory layer) with the following features:
- Capture schema for product, platform, selling price, time, season, purchase frequency, and product family.
- Real only when a fee model is configured: profit.
- No real source anywhere in this factory, always {value: None, reason: ...}: bundle, customer country, customer language, traffic source, acquisition channel, device, conversion, refund, customer feedback.
- niche_commercial_profile(niche) with real aggregate and honestly empty until real sales exist.
- monthly_evolution_report(), gated on MIN_SAMPLES = 3.
- recommend_actions(), evidence-gated autonomous recommendations with only two real types today.

We've also wired the Market Memory into the 7 named systems using existing consumers.

**Current State vs. Known Gaps:**

* We have a working Market Memory layer and a monthly evolution report.
* We have limited evidence-gated recommendations with two real types today.
* We still have gaps in commercial dimensions (bundle, customer country, customer language, traffic source, acquisition channel, device, conversion, refund, customer feedback).
* We still need to address the deficiency in Paddle's profit formula configuration.

We'll continue to build and improve our Global Market Learning Engine, staying true to the founder's constraint of only using verified commercial evidence.
