# PayPal and Algeria: what the official pages say (2026-10-22)

Scope: closes the PayPal action in `reports/ALGERIA_PAYOUT_MATRIX_2026-10-21.md`
("re-verify the PayPal Payouts country list once, store the URL and date").
Method: public pages read with a plain HTTP GET. No login, no account, no
application, no spend. Raw quotes and page hashes are stored in
`reports/PAYPAL_ALGERIA_EVIDENCE_2026-10-22.json`.

## Findings

| # | Question | Answer | Class | Source |
|---|---|---|---|---|
| P1 | Does PayPal's mass-payout product (Payouts) list Algeria? | **No.** The "Eligible countries and their feature sets" table has no Algeria / `DZ` row. Albania and Egypt are also absent. | OBSERVED | developer.paypal.com/docs/payouts/standard/reference/country-feature/ |
| P2 | Can a PayPal account in Algeria receive money? | **Yes, under conditions.** Algeria is named in the "PayPal Receive Funds and Automatic Transfer Agreement" (last updated 22 Sep 2026). | OBSERVED | paypal.com/dz/legalhub/paypal/recpymt-full |
| P3 | Conditions for receiving | You must link a **US bank account or Visa credit card** and complete verification. Every receipt has an **initial 30-day hold**. The balance is swept out automatically. The balance and US bank account cannot be used to send payments. Commercial receipts cost **4.9% + a fixed fee** (first $3,000/month). | OBSERVED | same |
| P4 | Can funds reach a local Algerian bank or wallet? | **A rail is published.** The DZ fee schedule (updated 28 Sep 2026) lists `DZ` for "withdrawals through external service providers" to a linked local bank account or wallet at **2.0% + $1.50**, plus the provider's own fees. You must be registered with that provider. | OBSERVED (published fee) | paypal.com/dz/webapps/mpp/paypal-fees |
| P5 | Manual withdrawal to a Visa card | `DZ` listed at **$5.00** per withdrawal, plus bank fees. | OBSERVED (published fee) | same |
| P6 | Will the founder's own account clear these conditions? | **UNKNOWN.** That depends on identity, the linked card or bank, and which external provider operates for DZ. Only the founder can check it, by logging in. | UNKNOWN | — |

## What this changes

- **Networks that pay through PayPal Payouts (the mass-payout API)**
  This is now a likely negative, not a neutral unknown. P1 says Algeria is not
  an eligible Payouts country. Whether a given network uses Payouts, or an
  ordinary PayPal payment, is network-specific and still has to be read from
  each network's own payment page.
- **Networks that send an ordinary PayPal payment** (the matrix records
  systeme.io, AWeber, SiteGround and Hostinger as PayPal-or-wire)
  The route still exists, but it is costly and slow. The commission waits at
  least 30 days, then 4.9% plus a fixed fee is taken on receipt. Then
  2.0% + $1.50 plus provider fees, or $5 to a Visa card, is taken on
  withdrawal. On a small first commission (for example systeme.io's $30
  minimum), fees take a material share. **DERIVED** for a $30 commission:
  receiving costs 4.9% ($1.47) plus a fixed fee whose amount this extract did
  not capture. Withdrawing the rest costs about $2.06 (2.0% + $1.50) or $5.00
  (Visa). That is at least about $3.50 of $30 before the fixed fee, FX and
  provider fees. This is a lower bound, not a number to rely on.
- **Wire transfers and Payoneer** are not affected by this evidence. The
  matrix's Payoneer row stays the only route documented end to end.

## Not done (needs the founder)

- Logging into a PayPal DZ account to confirm P6.
- Linking a card or bank, or registering with an external withdrawal provider.

Each of these is an account action under the founder's identity. None was
attempted.
