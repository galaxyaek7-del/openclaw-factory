# Galaxy Forge — Customer Health Engine

**Date:** 2026-08-08 | ADR-219, Phase 29, Section 6. `customer_success_engine.customer_health_score()` — genuinely new this round.

---

## 5 named states, explainable

`HEALTHY` / `WATCH` / `AT_RISK` / `CRITICAL` / `UNKNOWN`. 10 named components (Activation through Churn Signals) — most honestly `UNKNOWN` at this factory's real data maturity (no per-customer usage/support/satisfaction tracking exists).

## Never hides uncertainty

**Verified by a dedicated regression test**: a customer with no real signal never resolves to `HEALTHY` — the classifier requires at least one real, known component before ever reporting a positive state, and an unactivated real request resolves to `WATCH` or `UNKNOWN`, never a guessed-positive state.

---

*See also: `CUSTOMER_VALUE_ENGINE.md`, `CHURN_ENGINE.md`.*
