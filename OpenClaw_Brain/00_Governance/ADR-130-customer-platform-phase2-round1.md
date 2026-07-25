# ADR-130 — Galaxy Forge Customer Platform, Phase 2 Round 1

**Date:** 2026-07-25
**Status:** Adopted.

---

## The directive

The founder re-sent the same Customer Platform mission verbatim (ADR-129's directive) without picking one of the two unblocking paths ADR-129 offered (clear the Paddle onboarding gate, or build the request-to-niche translation layer). Read as: continue building everything that CAN run on 100% real data without either blocker — which turned out to be more than ADR-129 assumed.

## What was actually blocked vs. what wasn't

ADR-129 deferred six modules as blocked on either a completed sale or Paddle checkout. Re-examining each against the real, already-built engines in this factory:

- **Qualification, Opportunity Evaluation, Price Generation, Proposal, Customer Approval** — none of these need a completed sale or working checkout. They need the SAME real evidence gate (`decision_engine.evaluate_and_decide`) and SAME real pricing engine (`profit_oracle.butter_price`) every internally-discovered opportunity already goes through. Not blocked — just not built yet.
- **Payment Verification** — genuinely blocked on Paddle's account gate, but the REAL attempt (not a fabricated stand-in) can still be built and will report the real block honestly, same as `scripts/check_paddle_checkout_status.py` already does elsewhere.
- **Customer Dashboard / Order Tracking** — ADR-129 assumed these needed a completed order to show anything real. Wrong: they can show the REAL state of a REAL request as it moves through Qualification → Proposal → Approval → Payment Verification, even if it never reaches Delivery today. A dashboard showing "your request was rejected, here's why" or "waiting on Paddle" is real and honest — it just isn't a happy-path success story.
- **AI Consultation** — not blocked by Paddle at all. Needs a public-safe Groq call, same real infrastructure `/api/agent/:name` already uses internally, with the same finding-2.1 discipline (fixed prompt, capped cost, rate-limited) applied to a public route instead of an authenticated one.
- **Support Center** — not blocked by anything. A ticket-intake form is the exact same shape as the Request-a-Product form already built in ADR-129.

Still genuinely deferred this round: **Production, Quality Inspection, Packaging, Secure Delivery, automated Follow-up, and direct customer-facing notifications (email/SMS)**. Every one of them requires Payment Verification to actually succeed first, and Paddle's account gate means no real request can reach that state today. Building them against a trigger that cannot fire would mean testing them only against a mock, never a real live signal — genuinely honoring "do not build placeholders" means not building these yet, not building fake versions of them.

## What was built

**`customer_pipeline.py`** (new) — the real state machine. Every request's mutable pipeline state lives in `data/customer_pipeline_state.json`, keyed by `request_id`, separate from the append-only `data/customer_requests.jsonl` intake ledger (same ledger-vs-state split as `decisions.jsonl` vs `factory_state.json`). Every stage transition is saved immediately, making `advance_request()` / `approve_request()` / `reject_request()` / `retry_payment_verification()` idempotent and resumable — a crash mid-pipeline loses no work and never re-runs (or re-charges) a completed stage.

Stage flow: `NEW` → (real Qualification + Opportunity Evaluation via `decision_engine.evaluate_and_decide`, tier1) → `QUALIFIED` → (real Price Generation via `profit_oracle.butter_price`, premium band) → `PROPOSED` → (customer's own real approve/reject action) → `APPROVED` → (real Payment Verification attempt via `channels.paddle_publisher.create_checkout_transaction`, matched against `data/paddle_products.json` within $1) → `AWAITING_PAYMENT` (real checkout URL) / `PAYMENT_BLOCKED_PADDLE_ONBOARDING` / `PENDING_CUSTOM_PRODUCT_SETUP`.

Side states, all real and honestly distinct from a plain reject: `REJECTED_AT_QUALIFICATION`, `PENDING_FOUNDER_REVIEW` (the real gate returned WAIT/IMPROVE — same "needs a human call" outcome an internal opportunity can land in), `RESEARCH_REQUIRED` (evidence too thin to honestly finalize — ADR-127's "Unknown must never automatically behave like False" applied to customer requests too), `REJECTED_BY_CUSTOMER`, `FAILED` (any real exception, captured not swallowed).

**Every workflow exposes the exact 6 fields the directive requires**: Status (`stage`), Progress (position in `STAGE_ORDER`, which honestly includes the not-yet-wired tail so the denominator reflects the real full pipeline length), Logs (`stage_history`), Failures (`error`), Recovery (a real, stage-specific hint — e.g. "founder action required at vendors.paddle.com" — not a generic "something went wrong"), Estimated completion (honestly `null` — zero real completions exist yet to derive a real number from, no fabricated ETA).

**Fail-safe visibility for the new automation.** Intake now fires `advance_request()` as a fire-and-forget background trigger immediately after a request is saved (no scheduler needed — this factory has none, CLAUDE.md — a one-shot spawn at the moment that matters, same "automatic means zero further code changes" convention as `check-paddle-checkout-status`). If that spawn is ever killed or crashes, the request stays safely in `NEW` (state is only written after a real stage completes) — but a silently-stuck `NEW` request would otherwise be invisible, so `list_pipeline_overview()` now flags any request still `NEW` after 10 real minutes as needing founder attention, rather than trusting the fire-and-forget trigger blindly.

**Mission Control** (`mission_control_api.py`, `server.js`, `mission_control_executive_v1.html`): two new endpoints (`customer_pipeline_status` read, `advance_customer_pipeline` batch-sweep action, async like `rerun-market-analysis` since each `NEW` request runs a real live Groq call), one new panel reusing the exact same generic `kv` rendering `evidence-network`/`evidence-coverage` already use (ADR-128's own "reuse before build" precedent) — no new UI component.

**Customer-facing (`customer_site/`):**
- `status.html` (new) — the real Customer Dashboard / Order Tracking module. Reads `?id=<request_id>` (the request_id itself is the bearer token — 64 bits of entropy, server-generated, same trust model as any unlisted status link). Renders real stage, a status-colored progress indicator (a side-state like REJECTED gets a red bar, not a misleadingly "complete-looking" orange one — a real bug found and fixed during live verification, see below), the real proposal with Approve/Decline buttons, the real Paddle checkout link once one exists, and the real activity log. Auto-polls every 10s while a request is in a transient stage.
- AI Consultation widget (in `index.html`, above the request form) — `POST /api/customer/consultation`: public, a FIXED system prompt (never user-controllable, unlike the vulnerability class Phase 1 Security Audit finding 2.1 fixed for the internal agent routes), a 500-char input cap, a 220-token output cap, its own tighter rate limit (8/10min/IP — real Groq spend per call), every exchange logged to `data/consultation_log.jsonl`. A "Use this in my request →" button copies the AI's suggestion straight into the request form's description field.
- Support Center section (in `index.html`) — `POST /api/customer/support-ticket`: same validation/honeypot/rate-limit/Telegram-notify shape as the Request-a-Product route, persisted to its own real ledger (`data/support_tickets.jsonl`) since a support ticket and a sales request are different real workflows.

**Direct customer notifications remain honestly NOT built.** Every real stage transition notifies the founder via the same real Telegram channel already used elsewhere (`channels.telegram_direct`, called directly from `customer_pipeline.py` — no Express dependency, same pattern as `check_paddle_checkout_status.py`). Real customer-facing email/SMS notification is 0% built (matches this factory's own pre-existing "email 0% built" finding) — the real substitute today is the pull-based status page above, which the customer can check anytime rather than waiting for a push. Disclosed here rather than simulated.

## Real bugs found and fixed during live verification

Every claim below was confirmed by actually running the real code, not by code review alone — the standing discipline this session runs under.

1. **Test setup double-remove bug.** `tests/test_customer_pipeline.py`'s `setUp()` called `os.remove()` on a path the shared `_temp_path()` helper had already removed — every one of the 20 new tests failed on setup before a single assertion ran. Fixed by removing the redundant call.
2. **Stale-timestamp bug in stuck-request detection.** The first draft of the stuck-`NEW` check called `_new_record()` to get a reference timestamp for an unadvanced request — but `_new_record()` stamps "now" at read time, so a request stuck for hours would always look "just created." Fixed to use the request's own real `submitted_at` from the ledger instead.
3. **Misleading progress bar for a real rejection.** Live-tested by submitting a real customer request end-to-end: the real evidence gate rejected it (`REJECTED_AT_QUALIFICATION`) — a genuinely useful result, proving the gate isn't a rubber stamp. But the status page rendered a full orange progress bar for it, which reads as "100% complete" rather than "stopped." Fixed: side-states (rejected/blocked/pending) now render a status-colored bar (red for a real stop, green for real success) instead of borrowing the in-progress color.

## Validation

**Unit tests** (`tests/test_customer_pipeline.py`, 20 new, all network-touching calls injected/mocked): every stage transition (accepted/rejected/research-required/deferred), idempotency, exception capture, approve/reject guard rails, Paddle price-matching (both matched and unmatched), the real `transaction_checkout_not_enabled` classification, retry-after-unblock, status lookup (confirms email is never leaked), and overview aggregation (stage distribution, needs-attention flagging). Full Python regression: **1527/1527 green** (1507 baseline + 20 new), confirmed clean of real-data pollution by diffing `data/*.jsonl` before/after.

**Live, real end-to-end verification** (not just curl, not just unit tests):
- Submitted a real customer request through the real running server → the fire-and-forget trigger fired → the real evidence gate genuinely evaluated it via a real Groq call → correctly landed on `REJECTED_AT_QUALIFICATION`, rendered correctly on the real status page.
- A second real submission landed on `PENDING_FOUNDER_REVIEW` (the real gate's WAIT/IMPROVE outcome) — further proof of genuine, varied evaluation rather than a fixed response.
- A real Approve action against a proposal with no matching catalog price correctly attempted a match, found none, and landed on `PENDING_CUSTOM_PRODUCT_SETUP` with an honest recovery message.
- A real Approve action against a proposal price-matched to an existing catalog item made a REAL call to the live Paddle API and correctly hit the real, still-open `transaction_checkout_not_enabled` account gate — the exact same live blocker ADR-074/085/086/129 already documented, now proven reachable through the new customer-facing path too, not just the founder-facing one.
- Real consultation and support-ticket calls both verified end-to-end in-browser (chat reply rendered, "Use this" correctly pre-filled the request form; ticket persisted and Telegram-notified).
- All test-generated records (`customer_requests.jsonl`, `customer_pipeline_state.json`, `consultation_log.jsonl`, `support_tickets.jsonl`) deleted after verification — nothing fabricated left staged. The two real `decisions.jsonl` entries these live tests produced were deliberately kept: they are genuine evidence-gate output on genuine (if arbitrary) test text, the same real-ledger-stays-real precedent every other live-tested evaluation this session has followed.

## What's deliberately still not built

Production, Quality Inspection, Packaging, Secure Delivery, automated Follow-up, and real customer-facing email/SMS notifications — all genuinely blocked on either Payment Verification actually succeeding (which needs the Paddle gate to clear) or new email infrastructure that doesn't exist anywhere in this factory yet. Reassessed the same way ADR-129 already stated: the Paddle gate clears, or dedicated new engineering builds real customer email delivery — whichever comes first.
