# Galaxy Forge — Financial Integrity Test

**Date:** 2026-08-08 | ADR-221, Phase 30.5, Section 24. `enterprise_sales_engine.py::delivery_profitability()`, 5 real test cases run this round.

---

## Formula under test

Revenue − Platform Fees − Payment Fees − Commissions − Refunds − Delivery Costs − AI Costs − Infrastructure − Acquisition Cost = Net Contribution

`delivery_profitability()` implements the delivery-cost side of this chain (7 named cost categories) against real contract revenue.

## 5 real test cases run this round

| Case | Input | Result | Verdict |
|---|---|---|---|
| 1 | $100,000 revenue, $47,500 total real costs | $52,500 contribution, 52.5% margin | Correct |
| 2 | $0 revenue, $10,000 cost | -$10,000 contribution, margin `UNKNOWN` (not a fabricated 0% or a crash) | Correct |
| 3 | $50,000 revenue, $60,000 cost | -$10,000 contribution, -20% margin | Correct — a large-looking deal correctly flagged unprofitable |
| 4 | $100,000 revenue, $0 cost | $100,000 contribution, 100% margin | Correct |
| 5 | **-$5,000 revenue** (an impossible/invalid input), $1,000 cost | **DEFECT FOUND**: originally computed `margin_pct: 1.2` (a positive-looking 120% margin from two negative numbers) | **BROKEN, then FIXED this round** |

## The defect and its fix

Case 5 exposed a real, silent input-validation gap: negative revenue divided by negative contribution produces a positive ratio that reads as a plausible, even attractive, margin — exactly the "impossible value silently passing validation" this section was designed to catch. **Fixed** in `enterprise_sales_engine.py::delivery_profitability()`: `contract_revenue < 0` now returns `margin_pct: "INVALID_NEGATIVE_REVENUE"` instead of computing a ratio. A regression test (`test_negative_revenue_never_produces_a_fabricated_positive_margin`) was added and verified passing (43/43 in the Phase 30 suite).

## Scope note

This test targeted the one real, isolated contribution-calculation function this factory has (`delivery_profitability()`, built in Phase 30). The broader formula's other terms (platform fees, payment fees, commissions, refunds, AI costs, infrastructure, acquisition cost) are each real, separately-computed elsewhere in the codebase (`global_commercial_operations_engine.py`'s fee/commission/refund functions, `data/ai_cost_log.jsonl`) but have not been chained into one single end-to-end formula test this round — a **disclosed scope limitation**, not a claim of full-chain verification.

---

*See also: `TRUTH_MATRIX.md`, `AUDIT/PHASE_30_AUDIT.md`.*
