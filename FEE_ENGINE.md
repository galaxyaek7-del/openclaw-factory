# Galaxy Forge — Fee Engine

**Date:** 2026-08-08 | ADR-216, Phase 26, Section 13. `global_commercial_operations_engine.fee_engine()` — reuses `global_commercial_scale.py::unit_economics_report()` (Phase 20, ADR-210) directly.

---

## The 10 named fee types

Platform, Payment, Transaction, Subscription, Listing, Advertising, Partner, Conversion, FX, Other — `economics.py::net_profit()` already computes the real platform-fee component for the 5 modeled tiers; every other fee type is honestly `UNKNOWN` (no real tracking exists).

## Gross → Net → Contribution

`UNIT_ECONOMICS_ENGINE.md` (Phase 20) already established this exact real calculation chain. **Never reports gross sales as profit** — verified throughout this session's every financial module (Phases 20/21/26 all share the same discipline).

---

*See also: `COMMISSION_ENGINE.md`, `UNIT_ECONOMICS_ENGINE.md` (Phase 20).*
