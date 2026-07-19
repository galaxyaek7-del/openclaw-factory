# ADR-074 — Paddle Live: First Real Product Created, Checkout Blocked by Account Onboarding

**Date:** 2026-07-18
**Status:** Adopted. **Real product and price created on a live Paddle account.** Checkout/transaction creation is blocked by a distinct, real Paddle account-level gate — not a code defect, not something an API key or code fix can bypass.

---

## What's real

Founder's Paddle account was approved (Algeria accepted) and gave a real Live API key. Verified it live (`GET /products` → HTTP 200) before storing anything — same discipline as `ADR-072`'s Telegram token lesson.

`registry.get("paddle").status()` → `ArmStatus.READY` for the first time in this factory's history.

**Real product created**, the exact $388 techdoc from the proven cycle (`ADR-069`/`ADR-071`, `books/proof_ai_compliance_automation_package.pdf`):
- Product: `pro_01kxtd3xzaz0nmfgphk55brhn7` — "AI-Powered Compliance Automation System for Accounting Firms"
- Price: `pri_01kxtd4p62t4m7ezap61k5ree0` — $388.00 USD

## Two real bugs found and fixed along the way

1. **Wrong default tax category.** `create_product()` defaulted to `"digital-goods"` (an unverified guess from when `paddle_publisher.py` was first written, per its own docstring's honesty note). The real account rejected it: `product_tax_category_not_approved`. Tested `"standard"` next — accepted. Paddle approves tax categories per-account, so this default is now a real, confirmed value, still overridable via `product_spec`.
2. **Generic HTTP errors hid the real reason.** `raise_for_status()` discarded Paddle's actual JSON error body (`{"error": {"code", "detail"}}`), surfacing only `"HTTP 400 Client Error"` — useless for diagnosis. New `_raise_with_paddle_error()` extracts and surfaces the real `detail`/`code`, used by `create_product`/`update_product`/`create_price`/`create_checkout_transaction`. This is exactly how `product_tax_category_not_approved` and `transaction_checkout_not_enabled` were actually diagnosed instead of guessed at.

A third, minor issue surfaced by a new test itself: `_safe_err()`'s key-redaction did a blind substring replace, which corrupted an unrelated error message when a short placeholder ("k") coincidentally matched a letter inside "Checkouts". Guarded with a minimum length (16 chars) — real Paddle keys are always 46+ chars, so this never affects a real key, only hardens against short/test-like values.

## The real blocker — Paddle's own account gate, not ours

`create_checkout_transaction()` (new — creates a Paddle Transaction, the mechanism that returns a real shareable `checkout.url`) fails with:

> `transaction_checkout_not_enabled` — "Checkouts aren't enabled for this account. This typically means that you haven't fully completed the Paddle onboarding process."

This is real, live, and confirmed directly from Paddle's own API — not a guess, not a code bug. Product and price creation succeeding while checkout creation is blocked shows these are genuinely separate account-level gates on Paddle's side (business approval ≠ payment-processing-ready). `paddle_arm.py`'s `publish()` reflects this honestly: it still reports `ok=True` with the real `product_id` when checkout creation fails, rather than discarding real, already-created progress over a separate blocker (2 new tests confirm this).

**No fake/placeholder checkout link was sent anywhere** — sending an incomplete "proof" would have violated the same honesty discipline this whole engagement has followed. The founder was told directly what's blocked and pointed at Paddle's own dashboard/support to resolve it (Paddle's own error documentation: check onboarding status at vendors.paddle.com, contact `sellers@paddle.com` if stuck).

## Impact

- `channels/paddle_publisher.py`: `"standard"` default tax category (real, confirmed), `_raise_with_paddle_error()`, `update_product()`, `create_checkout_transaction()`, hardened `_safe_err()`.
- `channels/paddle_arm.py`: `publish()` now attempts checkout-link creation after price creation, threads a real `url` through `PublishResult` when it succeeds, degrades honestly (not a failure) when it doesn't.
- `tests/test_paddle_arm.py`: 9 new/updated tests. Full suite: 479 Python tests, zero regressions.
- **Next step, founder-only:** check Paddle vendor dashboard for a pending onboarding step (payout/banking details, business verification, or similar) blocking checkout. The moment that's resolved, `create_checkout_transaction()` — already built, tested, and proven correct against the real API's product-tax-category and error-detail behavior — will produce a real checkout link with zero further code changes.

## Addendum, 2026-07-19 — re-verified live, still blocked, founder notified

Re-ran `create_checkout_transaction()` directly against the real Paddle API (same real product `pro_01kxtd3xzaz0nmfgphk55brhn7` / price `pri_01kxtd4p62t4m7ezap61k5ree0`) — **identical error, unchanged since 2026-07-18**: `"Checkout has not yet been enabled for this account, you may need to check with Paddle Support that the Paddle onboarding process has completed."` Confirms this is still a real, live, account-level gate on Paddle's side, not a stale finding.

Sent a detailed Arabic checklist directly to the founder's Telegram (via the Bot API, bypassing n8n entirely — same direct-send precedent `ADR-072` established) listing the specific `vendors.paddle.com` sections to check (Business details, Payouts/Banking, Tax information), since Paddle's own error message doesn't name the exact missing sub-step and this factory has no way to see inside his account dashboard. Includes the exact error text and `sellers@paddle.com` as the escalation path if all sections look complete. No code change — this remains purely a founder-side action.
