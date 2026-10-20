# Commission Attribution Audit

Date: 2026-10-20
Method: read the real ledgers and the code that writes them. No conversion
data was created, imported, or estimated.

## Current state (OBSERVED)

| Ledger | Records | Real revenue |
|---|---|---|
| `data/commission_ledger.jsonl` | 1 TEST, 0 REAL, 0 PROVISIONAL, 0 SIMULATION | $0.00 |
| `data/affiliate_clicks.jsonl` | 29 clicks | n/a (clicks are not revenue) |
| Clicks with a referrer | 0 (all 29 are null) | n/a |
| Clicks with a source/UTM | 0 | n/a |
| `FIRST_REAL_DOLLAR` | False | $0.00 |
| systeme.io commissions | 0 | $0.00 |

`real_commission_summary()` filters strictly on `environment == "REAL"` and
counts only CONFIRMED or PAID. The single TEST record is excluded from every
real total. `first_real_dollar_status()` returns all zeros while that total is
zero, with no partial credit.

## What attribution can and cannot prove today

**Can prove:** a visitor reached a page (page-view ledger), a click was
recorded before the redirect (`record_click` / `record_attributed_click`), and
which UTM fields or referrer that click carried.

**Cannot prove:** that a click became a sale, which sale, its amount, or its
status. That requires a per-transaction record from the affiliate network.
systeme.io does not provide this factory a postback, and no Amazon tag is
configured, so there is no second source either.

Therefore every "commission" figure in this factory is either $0 or a record
with real evidence attached. There is no third category.

## Why null referrers matter

All 29 clicks have `referrer: null`. That is not a bug in the reader; it is
what browsers send when a visitor arrives from a direct open, a privacy
setting, or a link opened inside an app. It means those clicks cannot be
attributed to a channel. They are counted as clicks only, never as evidence
that a specific channel works.

## The double-count guard

`record_commission` refuses a second REAL record with the same
`external_transaction_id` (`DuplicateCommissionError`), under an advisory file
lock so two concurrent deliveries cannot both pass the check. A repeated
webhook cannot inflate revenue. A TEST or SIMULATION record with a repeated id
is allowed, because it carries no financial claim.

## Reversal and refund handling

REVERSED and REFUNDED records exist but are excluded from
`real_confirmed_or_paid_commission_usd`. Because the ledger is append-only and
the summary sums CONFIRMED/PAID records without netting a later reversal, a
commission that is paid and then reversed would still be counted at its
original amount. No real record exercises this path, and no test covers it, so
it is disclosed as an open gap rather than described as solved. Closing it
needs a decision on whether reversals are negative records or a status
transition, and both would change the ledger's write contract.

## Evidence that would settle a real commission

1. A partner dashboard line with a transaction id, date, amount and status.
2. A payout statement matching that transaction.
3. A bank/PayPal receipt matching the payout.

One of the three is a claim. Two is attribution. Three is money. This audit
accepts nothing less than the second as CONFIRMED and nothing less than the
third as PAID.

## Tests

`tests/test_render_and_attribution_integrity.py` covers: REAL-only totals,
PENDING excluded from cash, PROVISIONAL kept separate, REVERSED/REFUNDED
excluded, REAL-without-evidence refused before write, duplicate REAL
transaction refused, null referrer preserved, repeated clicks counted as clicks
not revenue, malformed ledger line skipped, and no affiliate id written into a
ledger.

16 tests. All pass.
