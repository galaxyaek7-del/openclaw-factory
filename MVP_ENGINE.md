# Galaxy Forge — MVP Engine

**Date:** 2026-08-08 | ADR-213, Phase 23, Sections 16-18. `product_innovation_engine.mvp_spec_template()` + `commercial_validation_signal()`.

---

## Section 16 — MVP Spec (real schema, never auto-filled)

9 required fields: Core Problem, Core User, Core Workflow, Core Outcome, Minimum Features, Excluded Features, Success Metric, Failure Metric, Stop Condition. **Deliberately not auto-generated** — an MVP spec must be filled from a real, validated opportunity (`validation_gate_status()` showing `overall_accepted=True`) by a human/AI Council member reasoning over real evidence, never fabricated ahead of that gate.

## Section 17 — Customer Validation Methods

The 11 named legitimate methods (interviews, surveys, prototype feedback, landing pages, pre-orders, pilots, B2B discovery, demo requests, letters of intent, paid pilots, usage evidence) have **0 real infrastructure** in this factory today beyond real Proof-of-Payment evidence gathering (`market_evidence.py::record_evidence()`). No fabricated customer, testimonial, or demand signal exists anywhere — confirmed by direct search across every module touched this session.

## Section 18 — Commercial Validation (real, structural separation)

`commercial_validation_signal(niche)` keeps 4 categories structurally distinct:

| Category | Real source |
|---|---|
| INTEREST | `market_evidence.get_willingness_to_pay_signal()` |
| INTENT | `NO_REAL_SIGNAL` — no real pre-order/demo tracking exists |
| COMMITMENT | `NO_REAL_SIGNAL` — no real letter-of-intent tracking exists |
| PAYMENT | `market_evidence.get_payment_evidence()` — the only category counted as direct evidence |

**Only PAYMENT is direct evidence of willingness to pay** — verified by a dedicated regression test confirming the other 3 categories never carry the same `real_events` structure PAYMENT does.

---

*See also: `PRODUCT_VALIDATION_GATES.md`, `PRODUCT_EXPERIMENT_ENGINE.md`.*
