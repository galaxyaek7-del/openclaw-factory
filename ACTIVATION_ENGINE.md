# Galaxy Forge — Activation Engine

**Date:** 2026-08-08 | ADR-219, Phase 29, Section 4. `customer_success_engine.activation_view()` — reuses `global_growth_engine.py::growth_journey_view()` (Phase 28) directly.

---

## Real, per-request activation check

A real request is considered activated once its real pipeline stage reaches `ACTIVATION`/`SUCCESS`/`RETENTION`/`EXPANSION`/`REFERRAL` (via the real growth-journey mapping, Phase 28). `TIME_TO_VALUE` is honestly `UNKNOWN` — no real timestamp-delta tracking exists between purchase and first value yet.

## Detects customers who purchased but never activated

Real, mechanical: any request stuck before `ACTIVATION` in the real `STAGE_ORDER` is, by construction, a real non-activated purchase — no separate detection logic needed beyond the existing real stage tracking.

---

*See also: `ONBOARDING_ENGINE.md`, `CUSTOMER_JOURNEY.md` (Phase 22/28).*
