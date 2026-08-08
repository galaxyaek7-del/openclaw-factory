# Galaxy Forge — Retention Engine

**Date:** 2026-08-08 | ADR-212, Phase 22, Sections 14, 25-27. `customer_intelligence.retention_engine_recommendations()` + `upsell_recommendation()` + `retention_experiments_status()`.

---

## Section 14 — Retention Actions (real taxonomy, no dark patterns)

10 named actions (`RETENTION_ACTIONS`): `IMPROVE_PRODUCT`, `IMPROVE_ONBOARDING`, `PROVIDE_EDUCATION`, `OFFER_SUPPORT`, `FIX_PROBLEM`, `IMPROVE_DOCUMENTATION`, `OFFER_RELEVANT_UPGRADE`, `OFFER_RELEVANT_RELATED_PRODUCT`, `REQUEST_FEEDBACK`, `DO_NOTHING`. **Confirmed by a dedicated regression test**: no action hides cancellation, obstructs a refund, or fabricates urgency/scarcity. 0 real customers exist to generate a real recommendation for — never populated with a fabricated example.

## Sections 25-26 — Upsell / Cross-Sell

`upsell_recommendation(customer_need, product_relevance_evidence, expected_value)` — **`DO_NOT_RECOMMEND` is the hardcoded default** whenever either `customer_need` or `product_relevance_evidence` is missing, verified by 2 dedicated regression tests. Customer trust outranks short-term revenue by construction, not by policy statement alone.

## Section 27 — Retention Experiments (already real, cited)

`retention_experiments_status()` reuses `commercial_experiments.py` directly — the real, generic, already-built experiment engine (hypothesis/baseline/change/metric/duration/result/confidence), never a second experiment system built specifically for retention.

---

## Phase 28 update (2026-08-08, ADR-218) — Section 23's real reuse

`global_growth_engine.py::retention_recommendations_v2()` reuses `retention_engine_recommendations()` above verbatim — no 2nd retention-action taxonomy was built. **Never uses manipulative retention tactics** — already enforced by the same real, tested exclusion this document's Section 14 established (no dark pattern exists in `RETENTION_ACTIONS`).

---

*See also: `CUSTOMER_TRUST_ENGINE.md`, `CHURN_INTELLIGENCE.md`, `CHURN_ENGINE.md` (Phase 28).*
