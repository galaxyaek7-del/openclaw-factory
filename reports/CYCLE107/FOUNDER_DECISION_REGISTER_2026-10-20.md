# Founder Decision Register - Cycle 107

Date: 2026-10-20
Only decisions the founder has actually made are listed as made. Everything
else is a request with its exact action and its consequence.

## Made

| ID | Decision | Date | Consequence |
|---|---|---|---|
| FD-107-01 | B13-001 preferred proposed price is $15.00 | 2026-10-20 | Workbook, guide and listing copy are aligned to $15; gate recomputed and approved |
| FD-107-02 | No 30-page expansion for B13-001 | 2026-10-20 | The product ships at its current depth; no additional content was written |
| FD-107-03 | Publication is not authorized | 2026-10-20 | `FACTORY_LIVE_PUBLISH` stays false; state is LOCAL_READY |
| FD-107-04 | Cycle 107 records NO QUALIFIED CANDIDATE | 2026-10-20 | EUDR, CBAM and EU EmpCo are not taken forward; no product was built from them |
| FD-107-05 | Zero new spend, no accounts, no agreements | standing | No application, deposit or subscription was made this cycle |

## Requested, not yet decided

| ID | Question | Exact action if approved | If not approved |
|---|---|---|---|
| FQ-01 | Publish B13-001 at $15.00? | Set `FACTORY_LIVE_PUBLISH=true`, refresh Gumroad auth, create the product with workbook + guide + listing copy | The product stays local; $0 revenue continues |
| FQ-02 | Use the existing systeme.io affiliate tag in a real asset? | Confirm the account is in good standing and the terms read on 2026-10-20 still apply; then authorize publication of the rendered asset | No affiliate click is possible; $0 commission continues |
| FQ-03 | Apply to impact.com? | Founder submits the application and tax data; no deposit, but a $10/month dormancy fee after 6 unpaid months | The only free network with explicit Algeria support is unused |
| FQ-04 | Choose a payout route? | Decide between PayPal Algeria (US bank or Visa, 30-day hold, $5 transfer) and a bank wire; verify fees with the bank | Commission can accrue but cannot be withdrawn |
| FQ-05 | Set `AMAZON_ASSOCIATE_TAG`? | Add the tag to `.env`; links become tracked | Amazon book links stay untagged |
| FQ-06 | Verify the public host serves `/api/affiliate/*`? | Deploy or confirm the route on the public host (GF18) | Amazon/affiliate clicks from the public site are not recorded |

## Decisions this session deliberately did not make

- It did not raise or lower the $65 opportunity floor, or any gate threshold.
- It did not mark any candidate as accepted, published, or sold.
- It did not choose a payout provider on the founder's behalf.
- It did not create, submit, or accept any affiliate program agreement.
- It did not overwrite the Cycle 107 verdict; the discovery repair adds a
  second, independent rejection path and preserves the original record.

## What the founder gets by deciding FQ-01

A real listing, a real price, and the first opportunity for a real sale. Until
then every commercial metric in this factory is structurally zero, and no
amount of additional code changes that.
