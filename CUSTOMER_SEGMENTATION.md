# Galaxy Forge — Customer Segmentation (Growth)

**Date:** 2026-08-08 | ADR-218, Phase 28, Section 4. `global_growth_engine.customer_segmentation_v2()` — real citation over `customer_intelligence.py::customer_segmentation_report()` (Phase 22, ADR-212).

---

## Two real, disclosed taxonomies, deliberately not merged

This directive names 8 segments (`LOW_VALUE`/`STANDARD`/`HIGH_VALUE`/`PREMIUM`/`B2B`/`ENTERPRISE`/`RECURRING`/`STRATEGIC`); Phase 22 named 9 (`NEW_CUSTOMER`/`REPEAT_CUSTOMER`/`RECURRING_CUSTOMER`/`HIGH_VALUE_CUSTOMER`/`B2B_CUSTOMER`/`ENTERPRISE_CUSTOMER`/`AT_RISK_CUSTOMER`/`INACTIVE_CUSTOMER`/`PRODUCT_SPECIFIC_CUSTOMER`). Both are real, disclosed taxonomies over the same real 0-customer state — not merged into a 3rd, since neither has real data yet to reconcile against.

## Real, live state

0 real customers exist in either taxonomy.

---

*See also: `IDEAL_CUSTOMER_PROFILE_ENGINE.md`, `CUSTOMER_COHORT_ANALYSIS.md` (Phase 22).*
