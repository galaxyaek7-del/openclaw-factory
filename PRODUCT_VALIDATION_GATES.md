# Galaxy Forge — Product Validation Gates

**Date:** 2026-08-08 | ADR-213, Phase 23, Section 15. `product_innovation_engine.validation_gate_status()` — real relabeling over `profit_oracle.py::ladder_opportunity_score()`'s already-real 9 hard gates, never a second scoring computation (verified by a dedicated regression test).

---

## The 6 named gates, mapped to real profit_oracle.py fields

| Gate | Real field cited | What it actually checks |
|---|---|---|
| GATE 1 — Problem Validation | `pain_severity` | Real customer-pain evidence exists and clears a severity floor |
| GATE 2 — Customer Validation | `pain_severity` (same) | This factory has no separate "customer cares" signal beyond real pain evidence |
| GATE 3 — Economic Validation | `high_profit_margin` | Real margin ≥50 AND the ladder's real $97 price floor |
| GATE 4 — Competitive Validation | `low_or_moderate_competition` | Real competition favorability ≥60 AND difficult-to-copy |
| GATE 5 — Solution Validation | `ai_significant_advantage` | Real, net-positive AI-leverage signal — can Galaxy Forge actually do this better |
| GATE 6 — Commercial Validation | `strong_proof_of_payment` | Real, cited spend evidence exists — the single strictest gate in this factory (ADR-121) |

## Live result for a real evaluated candidate

`AI-Powered Compliance Automation System for Accounting Firms`: **3 of 6 gates pass.** Failing: PROBLEM_VALIDATION, CUSTOMER_VALIDATION, COMMERCIAL_VALIDATION — no real recorded pain evidence or Proof of Payment for this specific candidate yet. This is the correct, honest state of a real candidate that has not yet cleared this factory's evidence bar — not a system fault.

## Only then: MVP

`mvp_spec_template()` deliberately does not auto-generate a spec — a real MVP spec must be filled from a niche where `overall_accepted=True`, never fabricated ahead of evidence.

---

*See also: `MVP_ENGINE.md`, `PRODUCT_KILL_CRITERIA.md`.*
