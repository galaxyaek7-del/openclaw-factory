# Galaxy Forge — Transaction Ledger

**Date:** 2026-08-08 | ADR-211, Phase 21, Sections 2-3, 6-7. Citation over `channels/ledger.py` (the real, stable, already-tested ledger) — not rebuilt.

---

## Section 2 — Financial Source of Truth

`revenue_operating_system.financial_source_of_truth()` — real map: Paddle sales are authoritative via its live transactions API; Gumroad via its Sales API; affiliate clicks via the internal ledger (but **not** commission amount — Amazon's own postback API would be authoritative for that, and no real credential exists). `finance_data.json` is explicitly marked **NOT AUTHORITATIVE** — a reconciled derived view, never treated as ground truth ahead of a real platform record.

## Section 3 — Revenue Classification

17 named categories (`REVENUE_CLASSIFICATION_TYPES`). `classify_revenue_event()` is a real, deterministic classifier — defaults to `UNKNOWN` for anything it can't confidently place, never guessed toward `SALE`. Live result today: 0 real sale events exist, so the classification report is honestly empty.

## Section 6 — Transaction Ledger Conformance

`transaction_ledger_conformance()` checks the real ledger's actual field coverage against the 17 named fields Section 6 requires:

| Field | Real coverage |
|---|---|
| External Transaction ID | Present (`raw.id`, platform-specific) |
| Platform | Present |
| Timestamp | Present |
| Attribution (country/channel/campaign/partner/segment) | Present when a caller supplies it (ADR-202) — optional, currently unpopulated by any real caller |
| Transaction ID | **Not present as a stored field** — implicit in JSONL line position, never a stored UUID |
| Customer Reference, Verification, Related Order | **Not present** — real, disclosed gaps |

## Section 7 — Idempotency

**A precise, two-layer finding, not a single verdict:**

| Layer | Status |
|---|---|
| `reconcile_ledger_to_finance()` (finance layer) | **IDEMPOTENT** — real, confirmed dedup via `source_ledger_key = f"{platform}:{raw.get('id')}"` |
| `append_event()`/`record_sale()` (raw ledger append) | **NOT IDEMPOTENT** — no dedup guard exists; a retried webhook/API call would append a duplicate raw line |

**Real, deliberate scope decision**: not fixed this round. A dedup guard on `record_sale()` would touch `channels/ledger.py`'s stable, already-tested core — this directive's own "do not rebuild stable commercial infrastructure" rule. Disclosed as a real, safe, well-scoped follow-up instead.

---

*See also: `RECONCILIATION_ENGINE.md`, `FINANCIAL_GOVERNANCE.md`.*
