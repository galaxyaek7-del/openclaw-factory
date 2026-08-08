# Galaxy Forge — First Real Dollar Protocol

**Date:** 2026-08-08 | ADR-223, Phase 31, Section 12.

This protocol defines the exact sequence for this factory's first real commercial transaction. **Failure at any step stops the chain honestly** — no step assumes the next one occurred. Every step below cites the real, existing code that implements it; no step describes work that doesn't exist yet.

---

1. **Founder completes external platform activation.**
   Real action: complete Paddle onboarding at `vendors.paddle.com`. See `AUDIT/CEO_VERDICT.md` / `commercial_activation.founder_action_center()`. Nothing past this step can happen until this one completes.

2. **Galaxy Forge verifies the real product.**
   `channels/paddle_arm.py::list_products()` — a live API call confirming the product still exists on the real Paddle account (already live-verified working, Phase 30.5 audit).

3. **Galaxy Forge verifies the real price.**
   Cross-checked against `data/paddle_products.json`'s real, recorded `price_id`/price pair — the same catalog `channels/paddle_webhook.py::validate_event_against_catalog()` uses.

4. **Galaxy Forge verifies checkout availability.**
   `scripts/check_paddle_checkout_status.py::check_and_notify_all()` — real, live, already working. Reports `checkout_ready: false` until step 1 clears; the moment it clears, this same function detects it and notifies the founder via Telegram (already wired into `factory_loop.js`'s tick, ADR from 2026-08-06).

5. **Founder opens the real checkout.**
   The real checkout URL Paddle returns once `create_checkout_transaction()` (`channels/paddle_publisher.py`) succeeds.

6. **A genuine buyer completes payment.**
   Entirely external to this factory — no code path here can substitute for a real buyer's real payment.

7. **Provider confirms payment.**
   Two independent, real confirmation paths, deliberately kept complementary rather than merged into one: (a) `customer_pipeline.py::check_payment_status()`'s existing polling call to Paddle's real `/transactions` endpoint; (b) `channels/paddle_webhook.py::process_paddle_webhook()`'s real, signature-verified event receipt (requires `PADDLE_WEBHOOK_SECRET`, see step 8).

8. **Webhook/event is verified.**
   `channels/paddle_webhook.py::process_paddle_webhook()` — real HMAC-SHA256 signature verification, event-type validation, and catalog cross-check (product/amount/currency). Rejects and logs anything that doesn't verify; never trusts an unverified event's contents.

9. **Order is created exactly once.**
   `channels/paddle_webhook.py`'s real idempotency ledger (`data/paddle_webhook_events.jsonl`, keyed on Paddle's own real `event_id`) guarantees a replayed/duplicate event is rejected before it can reach order creation. The actual order/fulfillment record is created via `customer_pipeline.py`'s existing, already-tested `_fulfill_paid_request()` path — never duplicated by the webhook module itself.

10. **Customer is recorded exactly once.**
    Same real `customer_pipeline.py` request record this factory already uses for every customer-facing flow — matched by `account_id` or email, per its existing real reconciliation logic.

11. **Delivery is recorded.**
    `customer_pipeline.py`'s real `STAGE_ORDER` — a request only reaches `DELIVERED` (and only then can `get_download_path()` serve a file) after real production/QA/packaging stages, never merely because a payment was confirmed.

12. **Revenue is recorded.**
    Via `server.js`'s real, authenticated `POST /finance/add` → `saveFin()`/`recomputeFinTotals()` path — the same real path exercised (in reverse, via `DELETE`) during the Phase 30.5.1 cleanup. Never written directly by the webhook module.

13. **Mission Control updates.**
    `executive-truth-dashboard` and `commercial-activation-status` (this phase) both recompute live on every call — no caching step required for this to become visible.

14. **Payout state is tracked.**
    Honestly `NOT_AVAILABLE` today — no real payout-retrieval endpoint exists for any arm (see `commercial_activation.refund_dispute_chargeback_status()`'s sibling finding). This step will remain a disclosed gap until a real payout endpoint is wired, which requires evidence from an actual first payout to design against.

15. **Audit evidence is preserved.**
    `docs/FIRST_REAL_TRANSACTION_AUDIT.md` — populated only when step 6 has genuinely occurred, per its own template, never before.

---

*See also: `docs/FIRST_REAL_TRANSACTION_AUDIT.md`, `AUDIT/CEO_VERDICT.md`, `commercial_activation.py`.*
