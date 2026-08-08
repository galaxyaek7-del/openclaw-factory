# Galaxy Forge — Commission Economics

**Date:** 2026-08-08 | ADR-226, Phase 33, Sections 4-5. `commission_engine.score_commission_opportunity()` + `commission_economics()`.

---

## Scoring — 13 named dimensions, never one-sided

`CUSTOMER_PROBLEM_STRENGTH`, `CUSTOMER_WILLINGNESS_TO_PAY`, `COMMISSION_VALUE`, `RECURRING_POTENTIAL`, `MARKET_SIZE`, `COMPETITION`, `CUSTOMER_ACQUISITION_DIFFICULTY`, `PARTNER_RELIABILITY`, `TRACKING_RELIABILITY`, `PAYOUT_RELIABILITY`, `GEOGRAPHIC_ACCESS`, `LEGAL_RISK`, `DATA_FRESHNESS`.

**Commission value alone never dominates** — verified by a dedicated regression test (`test_high_commission_alone_does_not_dominate`) that a large commission figure with every other dimension `UNKNOWN` still reports most dimensions as `UNKNOWN`, never inflating an overall impression of quality. No single collapsed score is ever computed — the directive's own explicit rule.

## Economics — confidence-tagged, never fabricated

`commission_economics()` requires 3 real inputs to compute anything: a parseable, real commission rate, a real expected deal value, and a real expected conversion rate. Missing any one → `economic_status: "INCOMPLETE"`, never a guessed number.

**Conversion-rate basis is always explicit**: `OBSERVED`, `ESTIMATED`, `SIMULATED`, or `UNKNOWN` — an invalid/unrecognized basis defaults to `UNKNOWN`, never silently accepted as `OBSERVED`. This factory has **0 real observed conversion rates today** — every commission_economics() call this round used `ESTIMATED` or `SIMULATED`, never `OBSERVED`, honestly.

## Formula

```
EXPECTED_GROSS_COMMISSION = expected_deal_value × parsed_commission_rate × expected_conversion_rate
EXPECTED_ACQUISITION_COST = ai_cost + outreach_cost
EXPECTED_NET_CONTRIBUTION = EXPECTED_GROSS_COMMISSION − EXPECTED_ACQUISITION_COST − platform_cost
```

Verified by a dedicated arithmetic test (`test_correct_arithmetic`): $1,000 deal × 10% × 0.1 conversion − $1 AI cost = $9.00 net, exactly.

## Commission-value parsing discipline

Only a directly regex-extractable percentage (e.g. `"10%"`) is used. A real but non-numeric commission description (e.g. `"contact sales for pricing"`, or a multi-tier description with no single clear rate) stays `INCOMPLETE` rather than guessed at — proven by `test_unparseable_commission_stays_incomplete`.

---

*See also: `COMMERCIAL/COMMISSION_COMMERCE.md`, `COMMERCIAL/PARTNER_VERIFICATION.md`.*
