# Galaxy Forge — Customer Profitability

**Date:** 2026-08-08 | ADR-219, Phase 29, Sections 21-22. `customer_success_engine.customer_profitability()` + `customer_segment_profitability()` — genuinely new this round.

---

## Section 21 — Customer Profitability (real, explicit subtraction chain)

Revenue − Fees − Commission − Refunds − Support Cost − Delivery Cost − AI Cost − Infrastructure Cost (− Acquisition Cost where known) = Customer Contribution.

**High revenue is never treated as automatically high-profit** — verified by 3 dedicated regression tests: a real subtraction chain can and does produce a negative contribution from real inputs, and every cost defaults to a real, explicit `0`/`UNKNOWN`, never silently omitted.

## Section 22 — Segment Profitability

6 named segments (Consumer/Professional/B2B/Enterprise/Subscription/Strategic) — real, ready comparison framework; 0 real customers exist in any segment to populate it with real numbers.

---

*See also: `CUSTOMER_ROI_ENGINE.md`, `CUSTOMER_VALUE_ENGINE.md`.*
