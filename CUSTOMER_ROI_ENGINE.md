# Galaxy Forge — Customer ROI Engine

**Date:** 2026-08-08 | ADR-219, Phase 29, Section 34. `customer_success_engine.customer_roi()` — genuinely new this round, reuses `enterprise_transformation_engine.py::roi_evidence_tier()` (Phase 24) directly.

---

## Real, evidence-tiered fields

Customer Investment, Customer Savings, Revenue Impact, Time Saved, Risk Reduced — each tagged via the same real `roi_evidence_tier()` function Phase 24 already established (defaults to `ESTIMATED`, never silently `VERIFIED`).

## Missing inputs are always UNKNOWN, never zero

**Verified by a dedicated regression test**: calling `customer_roi()` with no arguments returns `UNKNOWN` for every field and for the overall `customer_roi` value — never a fabricated $0 or a guessed positive number.

## Real, honest state

0 real customer ROI has ever been computed — 0 real customers exist with real investment/savings data.

---

*See also: `CUSTOMER_PROFITABILITY.md`, `ENTERPRISE_PROBLEM_REGISTRY.md` (Phase 24, ROI Engine precedent).*
