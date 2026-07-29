# ADR-131 — Galaxy Forge Customer Platform V1 (Rounds 1-6)

**Date:** 2026-07-29
**Status:** Adopted.

---

## The directive

The founder re-sent a comprehensive "Galaxy Forge Client Experience V1" directive: a 20-item customer-facing platform (accounts, onboarding, quoting, contracts, payment, production, QA, delivery, invoices, history, reviews, support) plus a Mission Control "executive cockpit," on top of the real pipeline Phase 1/2 Round 1 already shipped (ADR-129/ADR-130).

Before building, the real gap was audited against the 20-item list. Already real: public site, catalog, onboarding, AI clarification, automatic quotation, proposal approve/reject, a real Paddle payment-verification attempt, order tracking, basic support ticketing, a Mission Control pipeline panel. Genuinely missing: secure client accounts (item 5 — today's "auth" was a request-ID-as-URL-token), contract generation (11), invoice center (17), delivery/download center (15/16), customer history (19), feedback/reviews (20).

Also re-confirmed live before starting: Paddle's account-onboarding gate is still open (`transaction_checkout_not_enabled`), and zero real customer requests had ever been submitted. The founder's explicit direction: build the remaining pieces now, wired to real pipeline state, honestly empty/pending until real orders exist — never fabricate production, delivery, payment, or reviews.

## The honesty-critical finding that reshaped Round 4

The working assumption going in — "only `book_generator.py` is a real production engine, so the 4 non-book catalog products need a manual-fulfillment fallback" — was checked against the real `books/_generation_log.jsonl` before writing any routing logic, and turned out to be wrong: **all 5 live catalog products, including the 4 non-fiction "system" niches (compliance automation, customer support automation, workflow automation, inventory management), already have a real, `published: true` generation record**, produced via `book_generator.py`'s `techdoc` product type. Only a genuinely bespoke, non-catalog request has no automated production trigger.

Real design that follows from this (`customer_pipeline.py`'s `_fulfill_paid_request()`): a catalog-matched PAID request reuses its already-produced, already-Dual-Inspected artifact directly — never re-fabricating a second inspection that would tell us nothing new. A non-catalog request honestly routes to a new `PENDING_FOUNDER_FULFILLMENT` side-state, same disclosure class as the pre-existing `PENDING_CUSTOM_PRODUCT_SETUP`.

## What was built, by round

**Round 1 — Secure client accounts.** `lib/customer_auth.js`: password hashing via Node's built-in `crypto.scrypt`, session signing via `crypto.createHmac` — same rigor as Mission Control's `mc_session`, zero new npm dependencies, but a deliberately separate secret/cookie (a customer session must never forge a founder session or vice versa). `POST /api/customer/signup|login|logout`, `GET /api/customer/session`, `customer_site/login.html`. Guest (no-login) submission is unchanged; a logged-in visitor's `account_id` is stamped onto their request for later history matching. Found and fixed in passing: `customer_requests.jsonl`/`support_tickets.jsonl`/`consultation_log.jsonl`/`customer_pipeline_state.json` hold real customer PII and had never been added to `.gitignore` since ADR-129/130 — fixed before any real customer data exists.

**Round 2 — Contract generation + acceptance.** `contract_generator.py`: deterministic text, zero LLM-generated narrative (same doctrine as the Business Dossier arc), reusing `trust/*.html`'s own "Draft — ..." honest-placeholder convention for the one field genuinely not yet knowable (governing law/jurisdiction). Approval now requires a typed-name e-signature (no e-signature integration exists — this is the honest real equivalent) before payment verification is attempted. No new pipeline stage — kept as a sub-object of the existing `PROPOSED`→`APPROVED` transition.

**Round 3 — Payment completion + invoice center.** `_attempt_payment_verification()` was discarding the full Paddle transaction object right after extracting `checkout_url` — fixed to persist it. New `check_payment_status()`/`check_all_awaiting_payments()` confirm `AWAITING_PAYMENT`→`PAID` against Paddle's real transaction list and generate a real invoice (`invoice_generator.py`) from the locked contract price. Never fabricates a completion — an unreachable API or a still-pending status leaves the record exactly where it was. New Mission Control action `check-customer-payments`.

**Round 4 — Honest production/QA/delivery/download.** See the finding above. `_fulfill_paid_request()` reuses a real published artifact when one exists, or routes to `PENDING_FOUNDER_FULFILLMENT` when none does; `fulfill_manually()` lets the founder attach a real deliverable (local path or URL) to complete a bespoke order. New gated download route (`GET /api/customer/requests/:id/download`) resolves the real local file path server-side only (`get_download_path()`) — it never appears in any client-visible JSON response, and `books/` is never served as a public static directory.

**Round 5 — Customer history + feedback/reviews.** `list_requests_for_account()` matches by `account_id` OR email (reconciling a guest submission made before an account existed). Genuinely greenfield review system (confirmed zero prior groundwork anywhere in the repo): one review per request, only once `DELIVERED`/`FOLLOWED_UP`, append-only (`data/customer_reviews.jsonl`). `index.html`'s "What customers say" section reads a real summary — honest "No reviews yet" empty state, never a placeholder testimonial. `DELIVERED`→`FOLLOWED_UP` is a manual, founder-triggered action (no scheduler exists in this factory).

**Round 6 — Mission Control executive cockpit.** Four new panels added to the existing `mission_control_executive_v1.html` card grid (already had 60s auto-refresh and a `customer-pipeline` panel precedent — no new dashboard file): Customer Accounts, Production & Fulfillment Queue, Invoices, Customer Reviews. All four are pure passthrough over already-real Round 1-5 state.

## Validation

**141 new/updated tests** across `tests/test_customer_pipeline.py` (62), `tests/test_dashboard_data.js` (39, net of the pre-existing baseline), and the new `tests/test_customer_auth.js` (11) — all network-touching calls (Paddle, Telegram) injected/mocked. Full regression re-run clean after the final commit: the pre-existing `tests/test_api_contract.js` (29 tests, ~3 min real-server-boot suite) and `tests/test_mission_control_api.py` (87 tests) both pass with zero regressions from the new dispatch entries.

Every round was also smoke-tested live against a running server (signup → login → submit-while-logged-in → contract shown → approve-with-signature → `AWAITING_PAYMENT`; Mission Control panels and actions hit through the real authenticated `/api/v1/` surface) and `data/customer_*` files were diffed before/after every test run to confirm no bleed into real data.

## What's still deliberately not built / open

- **Paddle's account-onboarding gate is still the real blocker**, unchanged by this arc. Every `PAID`-and-later code path (Round 3 onward) is real but stays functionally unexercised against a live account until the founder clears `vendors.paddle.com`.
- Real customer-facing email/SMS notification remains 0% built (same disclosed gap as ADR-130) — the pull-based status/history pages are the real substitute today.
- `mission_control.html` (the older tabbed dashboard) did not get the Round 6 panels — cockpit work concentrated in `mission_control_executive_v1.html`, the newer surface with the auto-refresh/reuse precedent.
