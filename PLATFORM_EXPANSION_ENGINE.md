# Galaxy Forge — Platform Expansion Engine

**Date:** 2026-08-08 | ADR-216, Phase 26, Section 29. `global_commercial_operations_engine.platform_expansion_check()`.

---

## Real, evidence-gated evaluation

Reuses `business_development.py`'s real per-platform evaluation — a real score ≥3 recommends `EVALUATE_FURTHER`, otherwise `DO_NOT_ACTIVATE`. **Never automatically activates an unknown platform** — verified by a regression test confirming an unregistered platform name always resolves to `UNKNOWN`, never a guessed recommendation. Activation itself remains a real, founder-triggered `advance_partnership()` call — this function only classifies, never executes.

## The 13 named evaluation criteria

Legitimacy, Market, Customers, Fees, Payouts, Payment Compatibility, Automation, Competition, Product Fit, Compliance, Risk, Strategic Value, Confidence — all real via `evaluate_platform()`'s fields where researched, honestly `Unknown` otherwise.

---

*See also: `PLATFORM_REGISTRY.md`, `PLATFORM_EXIT_ENGINE.md`.*
