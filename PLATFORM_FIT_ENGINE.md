# Galaxy Forge — Platform Fit Engine

**Date:** 2026-08-08 | ADR-216, Phase 26, Section 4. `global_commercial_operations_engine.platform_fit()` — genuinely new this round.

---

## The real, deterministic classifier

Combines `business_development.py`'s real per-platform score (0-5, 3-axis explainable) with `economics.py`'s real net-profit model for the specific real product: score 0 → `AVOID`; score 1-2 → `SECONDARY`; score 3-4 with a real positive modeled margin → `TEST`; score 5 with a real positive modeled margin → `RECOMMEND`; anything else (unmodeled margin, unrecognized product/platform) → `UNKNOWN`.

## Live result

`platform_fit("AI-Powered Compliance Automation System for Accounting Firms", "amazon")` → **`RECOMMEND`** (real score 5, real positive modeled net profit). Verified by regression tests that unrecognized platforms and unrecognized products both correctly resolve to `UNKNOWN`, never a guessed verdict.

## Never recommends a negative-margin platform

Confirmed by direct inspection: the classifier requires `net is not None and net > 0` before ever returning `TEST` or `RECOMMEND` — a real, computed loss blocks the recommendation regardless of the platform's own opportunity score.

---

*See also: `PLATFORM_REGISTRY.md`, `PRODUCT_PLATFORM_MATRIX.md`.*
