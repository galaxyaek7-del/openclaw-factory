# ADR-085 — Paddle Checkout Readiness: One Action Away, Real Arabic Telegram Send Prepared

**Date:** 2026-07-22
**Status:** Adopted. Built and tested; **re-verified live against the real Paddle account** — still blocked by the same account-onboarding gate ADR-074 found, unchanged as of today.

---

## The founder's ask

"Prepare everything so the moment onboarding clears, the $388 techdoc checkout link fires to my Telegram in Arabic automatically." Top priority, run in parallel with the customer discovery experiment (ADR-084).

## What was built

**`channels/telegram_direct.py`** — new, reusable direct-Telegram-send helper. Every existing Telegram notification in this factory (ADR-073) goes through n8n, which depends on n8n being both running and its workflow manually toggled Active (a real, confirmed n8n platform limitation — ADR-072). ADR-072 and ADR-074 both already sent one-off critical messages by calling Telegram's Bot API directly instead of waiting on n8n; this turns that proven pattern into a shared function rather than a third hand-written call. Reads `TELEGRAM_BOT_TOKEN`/`OPENCLAW_TELEGRAM_CHAT_ID` from `.env`, never raises to its caller (a failed send is reported, not thrown — the real event it's reporting must never be lost over a delivery hiccup).

**`scripts/check_paddle_checkout_status.py`** — re-attempts `create_checkout_transaction()` for the exact, already-existing $388 techdoc price from ADR-074 (`pri_01kxtd4p62t4m7ezap61k5ree0`) — never creates a new product/price, which would mean a second real Paddle product for the same techdoc. Two outcomes:
- **Still blocked**: reported honestly, no Telegram message sent. Expected on every run until the founder finishes Paddle onboarding.
- **Real checkout URL returned**: sent directly to the founder's Telegram in Arabic, and recorded in `data/paddle_checkout_notifications.json` so a second run never re-sends the same real link. A failed Telegram send is *not* recorded as notified — a later retry will try again rather than silently giving up.

**Wired as a Mission Control action** (`check-paddle-checkout-status`, `server.js`'s `ACTION_REGISTRY`, dispatched via `mission_control_api.py`'s new `check_paddle_checkout_status` endpoint) — the founder (or a future Claude session) can trigger this with one click/command the instant onboarding is done.

## A real bug found and fixed via live testing, not assumption

First draft matched the still-blocked case by looking for the literal string `transaction_checkout_not_enabled` (the error *code*) in the exception message. Running the new action live against the real Paddle account immediately proved this wrong: `_raise_with_paddle_error()` (`channels/paddle_publisher.py`) prefers the `detail` text over the `code` when both exist, and Paddle's real response — confirmed identically on 2026-07-18, 2026-07-19, and again live today — never actually surfaces the code string at all, only: *"Checkout has not yet been enabled for this account, you may need to check with Paddle Support that the Paddle onboarding process has completed."* The original code would have mis-reported this as an unexpected error every single time instead of the honest "still waiting on onboarding" case. Fixed to match on the real, three-times-confirmed detail text shape (`"checkout"` + `"enabled"` + `"account"` all present) instead of a code string this account's real responses don't produce. A dedicated regression test (`test_unrelated_paddle_error_is_reported_as_a_real_error_not_swallowed`) confirms a genuinely different Paddle error is never mistaken for the same known gate.

## Why this is not a background poller, and why that's a deliberate choice, not an oversight

This factory has **no scheduler** (`CLAUDE.md`; confirmed repeatedly, e.g. `pause-production`'s own action description) — nothing here runs on a timer. Adding a `setInterval` inside `server.js` to poll Paddle automatically would be a real, meaningful departure from that standing, documented architecture, made silently, on a single instruction. Given that:

**What "automatic" means here**: zero further code changes, one click (or one command run on the founder's behalf) away — not a background timer that fires with no human involved. Re-verified live today that the check itself is fully correct and ready; the only remaining variable is the founder completing Paddle's own onboarding steps at `vendors.paddle.com` (payout/banking, business verification, or similar — same unresolved item ADR-074's addendum already flagged directly to his Telegram).

**If the founder wants genuine unattended polling** (no click required at all), that is a distinct, larger infrastructure decision — this factory's first real scheduler — and deserves an explicit go-ahead of its own rather than being folded into this fix. Flagged here rather than either silently building it or silently failing to meet the word "automatically" at face value.

## Verification

- 10 new unit tests (`tests/test_telegram_direct.py`, `tests/test_check_paddle_checkout_status.py`) — zero live network calls, Paddle/Telegram both mocked.
- Live-verified twice against the real Paddle account today: first run surfaced the detail-vs-code bug above; second run, after the fix, correctly reported the honest still-blocked state with the exact real Paddle message.
- Confirmed no stray state file is written on the still-blocked path (idempotency file only appears after a real, successful send).
- Full suite: 898 Python tests (up from 888), 189 JS tests — zero regressions.

## Impact

- `channels/telegram_direct.py` (new), `scripts/check_paddle_checkout_status.py` (new).
- `mission_control_api.py`: new `check_paddle_checkout_status` endpoint.
- `server.js`: new `check-paddle-checkout-status` Mission Control action.
- `data/paddle_checkout_notifications.json`: created only on a real, successful checkout-link + Telegram send (not present today — onboarding still incomplete).
- **Founder-only next step, unchanged since ADR-074**: finish the pending Paddle onboarding step at `vendors.paddle.com`. The moment that clears, one click on "Check Paddle Checkout Status" in Mission Control (or telling this factory "check now") sends the real $388 checkout link to Telegram in Arabic — already built, already tested, already re-verified live today.
