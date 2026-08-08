# Galaxy Forge — Commission Ledger

**Date:** 2026-08-08 | ADR-226, Phase 33, Sections 10-11. `commission_ledger.py`.

---

## Schema

`commission_id`, `partner_id`, `opportunity_id`, `customer_id`, `lead_id`, `deal_id`, `external_transaction_id`, `commission_status`, `gross_commission`, `fees`, `net_commission`, `currency`, `created_at`, `confirmed_at`, `paid_at`, `reversed_at`, `evidence`, `source`, `environment`.

## The 8 named commission statuses

`EXPECTED`, `PENDING`, `CONFIRMED`, `PAID`, `REVERSED`, `REFUNDED`, `DISPUTED`, `UNKNOWN`.

## The hard anti-fabrication rule

`record_commission()` is a real Python function that **raises `AntiFabricationError`** — not a documented convention, an actual exception — under 2 conditions:

1. `environment="REAL"` with no `evidence` supplied.
2. `environment="REAL"` and `commission_status` is `CONFIRMED` or `PAID` with no `external_transaction_id`.

Verified by a dedicated regression test (`test_real_without_evidence_never_writes_to_disk`) that no record reaches disk when the guard fires — the rejection happens *before* the file write, not as a post-hoc cleanup.

`TEST` and `SIMULATION` records never require evidence, since they carry no real financial claim by definition.

## Real commercial revenue rule

`real_commission_summary()` counts only `environment="REAL"` **and** `commission_status` in (`CONFIRMED`, `PAID`) toward real commercial revenue. A `REAL` record at `EXPECTED`/`PENDING` exists in the ledger (a real, honest intermediate state) but is explicitly excluded from the revenue total — matching the directive's own rule that only confirmed/paid commissions become real commercial revenue.

## REAL / TEST / SIMULATION never blended

Every summary reports the three counts separately. Verified by test that a `SIMULATION` or `TEST` record of any size never moves the `real_confirmed_or_paid_commission_usd` figure.

## Current real state

0 real commission records exist. `data/commission_ledger.jsonl` holds only what this document's own test suite writes to isolated temp paths — the real default path is empty.

---

*See also: `COMMERCIAL/COMMISSION_COMMERCE.md`, `AUDIT/COMMISSION_COMMERCE_READINESS.md`.*
