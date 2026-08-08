# Galaxy Forge — Customer Data Model

**Date:** 2026-08-08 | ADR-212, Phase 22, Sections 2-4.

---

## Section 2 — Customer Identity (already real, cited)

`customer_intelligence.customer_identity_view()` reuses `customer_pipeline.py::list_requests_for_account()` verbatim — the real, already-conservative identity resolver: matches by real `account_id` (a logged-in customer) OR normalized `email` (reconciling a guest submission made before an account existed). **Never** merges on weak evidence (name similarity, IP, device fingerprint — none of these are used anywhere in this factory). Unresolvable identity honestly returns `UNKNOWN`/`NO_MATCH`, verified by a dedicated regression test.

## Section 3 — Data Minimization (already real, cited)

`customer_intelligence.data_minimization_report()`: this factory's real intake schema collects exactly `name`/`email`/`description`/`company`/`budget_range` — confirmed by direct search, no unnecessary or sensitive personal information collected anywhere. Already documented in `brand_dna.py`'s `CUSTOMER_JOURNEY_STANDARDS`.

## Section 4 — Customer Profile

`customer_intelligence.customer_profile()` — real fields where they exist (`purchase_history` via the real resolved request list), honest gaps where they don't (`revenue_usd` not yet cross-referenced per customer, `support_interactions` not yet logged per customer). `privacy_classification` defaults to `INTERNAL` per `KNOWLEDGE_ACCESS_CONTROL.md`'s real 4-tier model.

---

*See also: `CUSTOMER_JOURNEY.md`, `CUSTOMER_PRIVACY_POLICY.md`.*
