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

## Addendum: PartnerStack withdrawal methods for Algeria (same day)

Closes matrix action 3 ("PartnerStack DZ check", affects n8n, Kit and one
other row). Source: PartnerStack's own help article "Configuring payout
providers" (support.partnerstack.com/hc/en-us/articles/360009377934). A plain
GET returned 403, so the text was read through a search-provider extract.
`stripe.com/global` was read the same way.

| Method | Algeria? | Class | Basis |
|---|---|---|---|
| PayPal | Depends on P1–P3 above. PartnerStack defers to "PayPal's list of supported countries" and warns that "some accounts only allow money to be sent out." | DERIVED | PartnerStack article + this file's P1–P3 |
| Stripe | **Not available.** Algeria is not among the countries on Stripe's global availability page. | OBSERVED | stripe.com/global |
| Direct deposit (Airwallex) | **Probably not; not proven.** The Airwallex local-transfer fee table names Egypt, Morocco, Nigeria and others but not Algeria. The full country list was elided in the extract. The article says a country missing from the dashboard drop-down "is not yet available." | INFERRED | same article |

**Net**: for an Algeria-based partner, PartnerStack's only plausible route is
PayPal, under the 30-day-hold, US-bank-or-Visa conditions above. The matrix
records no PartnerStack account. The Airwallex question can only be settled
from the country drop-down under "Setup withdrawals", which needs an account,
so it stays a founder decision. Opening that account means accepting
PartnerStack's terms.

## Addendum: impact.com has a documented wire straight to an Algerian bank

Closes matrix action 4 (Impact) for the payout-rail question. Sources are
impact.com's own help center, read as raw `.md` with a plain GET. Hash and
quotes are in the JSON record.

| # | Fact | Class | Source |
|---|---|---|---|
| I1 | DZD (Algerian Dinar, country Algeria) is in impact.com's **"Wire supported currencies"** list for partner withdrawals. | OBSERVED | help.impact.com/other/reference-documentation/supported-currencies-and-timezones.md |
| I2 | DZD is **not** in the ACH or PayPal currency lists. | OBSERVED | same |
| I3 | Wire timing: 3–5 business days after the paystub clears. Fee: "Currency-specific", shown in the dashboard when the bank country is chosen. | OBSERVED (fee amount UNKNOWN) | .../payout-setup/withdraw-funds-to-your-bank-account.md |
| I4 | Minimum withdrawal: $10 or equivalent. Payouts run on a threshold (Tue/Thu) or a fixed day (1st/15th). | OBSERVED | impact.com "How Do Partners Get Paid?" (updated 15 Jan 2026) |
| I5 | Whether the founder's identity and bank pass impact.com verification, and what the Algerian bank charges on an inbound FX wire. | UNKNOWN | founder-only |

**Why this matters**
- impact.com is the only network now documented to pay **directly into an
  Algerian bank account**, with no PayPal, US bank or Visa card in between.
- The earlier register treated Impact as `UNKNOWN` at the country level
  (Semrush and other Impact-hosted programs). The rail is now documented.
- Approval stays discretionary per brand. The terms are binding on signup,
  so FQ/F-04 remains a founder decision; nothing was submitted.

## Updated ranking of payout rails for an Algeria-based publisher

| Rank | Rail | Lands in | Evidence |
|---|---|---|---|
| 1 | impact.com wire (DZD) | Algerian bank, directly | I1–I4 OBSERVED |
| 2 | Payoneer (DigitalOcean / Awin) | Payoneer balance | Matrix: documented end to end; Awin's fee blocker stands |
| 3 | PayPal (ordinary payment) | PayPal → US bank / Visa / external provider | P2–P5 OBSERVED; 30-day hold plus stacked fees |
| — | PayPal Payouts (mass payout) | — | P1: Algeria not eligible |
| — | Stripe (via PartnerStack) | — | not available in Algeria |

This ranking is about **collectability only**. It says nothing about which
program would earn a commission. No program here has produced a click,
conversion or commission for this factory.
