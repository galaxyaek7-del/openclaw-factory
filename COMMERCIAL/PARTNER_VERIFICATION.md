# Galaxy Forge — Partner Verification

**Date:** 2026-08-08 | ADR-226, Phase 33, Section 3. `commission_engine._derive_verification_status()`.

---

## The 6 named statuses

`VERIFIED`, `PARTIALLY_VERIFIED`, `UNVERIFIED`, `STALE`, `BLOCKED_EXTERNAL`, `REJECTED`.

## Mechanical derivation rule

`VERIFIED` requires all 3 real signals at once: a real terms URL (`https://...`), at least one real evidence URL, and a real, non-placeholder commission figure. Missing any one of the three caps the status at `PARTIALLY_VERIFIED` (evidence + commission present, no terms link) or `UNVERIFIED` (evidence alone, or nothing).

**Never marked `VERIFIED` merely because an AI model found a webpage mentioning a program** — this is a mechanical, code-level check (`_derive_verification_status()`), not a judgment call an LLM makes at generation time. Proven by a dedicated adversarial test (`tests/test_commission_adversarial.py::test_fake_partner_never_marked_verified`, `test_hallucinated_partner_with_no_real_terms_never_verified`).

## Current real breakdown (13-opportunity portfolio)

1 `VERIFIED` (Amazon Associates — real terms URL, real evidence, real 5% commission figure). 9 `PARTIALLY_VERIFIED`. 3 `UNVERIFIED`.

## Staleness

`STALE` is derived separately by `commission_engine._freshness_from_last_verified()` — `FRESH` (≤14 days), `AGING` (≤45 days), `STALE` (>45 days), `UNKNOWN` (no timestamp). Applies uniformly to "stale commission" and "expired program" scenarios — this factory's real data model has no separate expiry signal, disclosed honestly rather than inventing a distinct mechanism.

## Conflict handling

`commission_engine.detect_conflicting_terms()` — if two records for the same `partner_id` disagree on `commission_value` or `commission_currency`, the real, mechanical result is `FLAG_CONFLICT`, never a guessed resolution.

## `BLOCKED_EXTERNAL` / `REJECTED`

Not yet exercised by any real record — no partner has been externally blocked or explicitly rejected in this factory's real data yet. The status values exist and are validated (`PARTNER_VERIFICATION_STATUSES`), ready for the first real occurrence.

---

*See also: `COMMERCIAL/COMMISSION_COMMERCE.md`, `AUDIT/COMMISSION_COMMERCE_READINESS.md`.*
