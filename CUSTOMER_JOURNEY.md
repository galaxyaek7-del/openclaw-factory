# Galaxy Forge — Customer Journey

**Date:** 2026-08-08 | ADR-212, Phase 22, Sections 5-8. `customer_intelligence.customer_journey_view()` — real translation of `customer_pipeline.py`'s real 11-stage `STAGE_ORDER` onto the directive's 12 named journey stages, never a second progress-tracking system.

---

## The real mapping

| Real pipeline stage | Named journey stage |
|---|---|
| NEW | INTEREST |
| QUALIFIED, PROPOSED | PRODUCT_VIEW |
| APPROVED, AWAITING_PAYMENT | CHECKOUT |
| PAID, PRODUCTION, QUALITY_INSPECTION | PURCHASE |
| PACKAGING, DELIVERED | DELIVERY |
| FOLLOWED_UP | FEEDBACK |

**Unmapped, honestly `UNKNOWN`**: `DISCOVERY` (no real pre-intake tracking exists), `FIRST_USE`/`SUPPORT`/`REPEAT_PURCHASE`/`SUBSCRIPTION_RENEWAL`/`RETENTION` (no real per-request signal exists for any of these today). Never inferred — disclosed as unmeasured.

## Section 6-7 — Purchase / Non-Purchase Reasons

`purchase_reason_report()`: 0 real purchases → every one of the 13 named reason categories reports 0, never a fabricated inference. `non_purchase_reason_report()`: 0 real checkout-abandonment tracking exists (no web analytics wired, same gap `CUSTOMER_ACQUISITION_INTELLIGENCE.md` already disclosed) → every category reports `NO_REAL_SIGNAL`. **Silence is never treated as rejection**, per the directive's own explicit rule.

## Section 8 — Customer Problem Mining (already real, cited)

`customer_intelligence.customer_problem_mining_report()` reuses `customer_pipeline.py::customer_problem_cost_trend()` directly.

---

## Phase 28 update (2026-08-08, ADR-218) — Section 5's 10-stage growth journey

The "GLOBAL GROWTH & CUSTOMER ACQUISITION ENGINE" directive names a genuinely different 10-stage vocabulary (`AWARENESS → INTEREST → CONSIDERATION → INTENT → PURCHASE → ACTIVATION → SUCCESS → RETENTION → EXPANSION → REFERRAL`) from Phase 22's own 12-stage journey above. `global_growth_engine.py::growth_journey_view()` is a **2nd, distinct real relabeling** of the same real `customer_pipeline.py::STAGE_ORDER` — deliberately not merged with the mapping above, since forcing one vocabulary onto the other would misrepresent which directive actually named which stage. `AWARENESS` and `EXPANSION` are honestly unmapped in the new relabeling — no real pre-intake or post-delivery signal exists for either.

---

*See also: `CUSTOMER_DATA_MODEL.md`, `RETENTION_ENGINE.md`, `GLOBAL_GROWTH_ENGINE.md` (Phase 28).*
