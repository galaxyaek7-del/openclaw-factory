# Phase 31 — Current State Inspection (before any changes)

**Date:** 2026-08-08 | ADR-223, Phase 31, Section 1. Read directly from code, not assumed from prior audits.

---

**Paddle integration** (`channels/paddle_arm.py`, 184 lines): real, complete `BaseArm` implementation. `status()` → credential-presence check only. `publish()` → real product/price creation with real dedup-by-`source_id` protection (Unified Recovery System §5) and a real pre-write snapshot. `create_checkout_transaction()` is a real, separate 3rd step that can fail independently of product/price creation — this is exactly where the account-level `transaction_checkout_not_enabled` gate lives. `get_sales()`/`list_products()`/`update_product()`/`retrieve_fees()` are all real, wired to real Paddle endpoints.

**Paddle product registry** (`data/paddle_products.json`): 6 real product/price ID pairs, prices $97-$388, all real, live-created.

**Checkout state**: `scripts/check_paddle_checkout_status.py` (ADR-085/086) re-attempts `create_checkout_transaction()` for each real price on demand — real, working, currently reporting `checkout_ready: false` for all 6 (live-verified again this round).

**Webhook architecture**: **no inbound payment webhook receiver exists anywhere in this repo.** Every "webhook" reference found (`grep -rl webhook`) is an *outbound* n8n notification call, not an inbound Paddle event receiver. No `PADDLE_WEBHOOK_SECRET` or signature-verification code exists. This is the real, primary gap Section 6 asks to close.

**Order/payment confirmation (existing, real, different mechanism)**: `customer_pipeline.py::check_payment_status()`/`check_all_awaiting_payments()` — a real, working *polling* mechanism (calls Paddle's `get_transactions()` and matches against real transaction data), not webhook-driven. This already exists and works; it is not replaced by this phase's webhook work, only complemented.

**Delivery**: real, already correctly gated — `customer_pipeline.py`'s `STAGE_ORDER` (`PAID→PRODUCTION→QUALITY_INSPECTION→PACKAGING→DELIVERED→FOLLOWED_UP`) and `get_download_path()` refuse to serve a download unless `stage == "DELIVERED"`.

**Finance layer**: `finance_data.json` — real, currently `sales: []`, all totals $0 (cleaned in Phase 30.5.1). `GET/POST/DELETE /finance/*` routes real and auth-gated.

**Commercial readiness (existing)**: `commercial_readiness.py` (ADR-181) already computes a 6-dimension (technical/commercial/marketing/legal/financial/global) company-wide score — a different concept from this phase's per-platform pipeline checklist (Section 4). Reused where overlapping, not duplicated.

**Mission Control**: `executive-truth-dashboard` (this session, Phase 30.5) is the newest real commercial-reality panel. No existing panel enumerates per-platform pipeline stage status (credential/catalog/checkout/webhook/delivery/finance/payout) side by side — a real gap Section 10 asks to close.

**Golden Hunter**: confirmed still 411+ hours stale (unchanged since Phase 30.5.1, as instructed). No architectural staleness-status field or controlled refresh function exists yet beyond the real, existing `skipped: stale` log line.

**Tests**: 20 tests added in Phase 30.5/30.5.1 all still passing (re-confirmed). No webhook, idempotency, or state-machine tests exist yet.

**Recent commits**: `8f75c46` (finance cleanup), `fb3956d`/`b39b73e` (Phase 30.5 audit), `bbebfca`/`5b90ac3` (Phase 30 enterprise sales engine).

---

*See also: `AUDIT/EXTERNAL_DEPENDENCIES.md`, `AUDIT/COMMERCIAL_REALITY.md`.*
