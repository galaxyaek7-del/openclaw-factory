# Affiliate financial reconciliation (2026-10-23)

## Real

| Measure | Value | Source |
|---|---|---|
| REAL commission records | 0 | `data/commission_ledger.jsonl` |
| Confirmed or paid (USD) | 0 | `real_commission_summary()` |
| Paid (USD) | 0 | same |
| Other currencies | none | same |
| FIRST_REAL_DOLLAR | False | `first_real_dollar_status()` |
| Payouts received | ZERO VERIFIED | no payout record of any kind |
| Real clicks | UNKNOWN for the public site; 30 rows recorded by the local server (27 unlabeled, 3 direct) | `data/affiliate_clicks.jsonl` |

## Rules now enforced

- Revenue counts a transaction only in its latest state CONFIRMED or PAID; REVERSED/REFUNDED/DISPUTED/PENDING never count.
- `*_usd` fields contain USD only; each currency is reported separately; no conversion is ever applied.
- REAL and PROVISIONAL records and status changes need evidence; CONFIRMED/PAID REAL need a real transaction id.
- SIMULATION, TEST and PROVISIONAL never enter real totals.

## Synthetic reconciliation (scenario J, temp ledger)

Pending 10 USD, confirmed 20 USD, paid 40 USD, confirmed 15 EUR: USD confirmed-or-paid 60, paid 40, EUR 15 reported separately; matches an independent calculation.
