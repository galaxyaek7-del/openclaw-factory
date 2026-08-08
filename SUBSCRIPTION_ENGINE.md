# Galaxy Forge — Subscription Engine

**Date:** 2026-08-08 | ADR-219, Phase 29, Section 17. `customer_success_engine.subscription_tier_template()`.

---

## The 5 named tiers

Free/Trial, Starter, Professional, Business, Enterprise — each with 8 required fields (Customer, Value, Features, Limits, Support, Price, Expected Margin, Upgrade Path).

## Avoids artificial upgrade-forcing restrictions

A real, disclosed principle, not yet exercised — 0 real subscription tiers exist. When a real tier is designed, this document's own rule governs it: feature limits must reflect real cost/value differences, never an arbitrary lock designed only to pressure an upgrade.

---

*See also: `RECURRING_REVENUE_ENGINE.md`, `RENEWAL_ENGINE.md`.*
