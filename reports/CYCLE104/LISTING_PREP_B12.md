# Cycle 104 — listing preparation for B12-002 / B12-005 / B12-010

Local only. No Gumroad call was made. Nothing was published.

| id | state | price | files | cover | page | gate | trust |
|---|---|---|---|---|---|---|---|
| B12-002 | READY_TO_PUBLISH__AWAITS_FOUNDER_AUTHORIZATION | $11.99 | 2 | Y | Y | Y | PASS |
| B12-005 | READY_TO_PUBLISH__AWAITS_FOUNDER_AUTHORIZATION | $8.00 | 2 | Y | Y | Y | PASS |
| B12-010 | READY_TO_PUBLISH__AWAITS_FOUNDER_AUTHORIZATION | $15.00 | 2 | Y | Y | Y | PASS |

## Exact authorization needed

- `I authorize publishing B12-002 — Client Project Handoff Pack — to Gumroad at 11.99 USD with the exact files listed in reports/CYCLE104/LISTING_PAYLOADS_B12.json`
- `I authorize publishing B12-005 — Podcast Guest Booking Kit — to Gumroad at 8.00 USD with the exact files listed in reports/CYCLE104/LISTING_PAYLOADS_B12.json`
- `I authorize publishing B12-010 — Nonprofit Grant Pipeline Tracker — to Gumroad at 15.00 USD with the exact files listed in reports/CYCLE104/LISTING_PAYLOADS_B12.json`

## Registry shape drift found

The machine-readable `listing_copy` field is not uniform across these products, which is why an automated listing step could not read two of them:

- B12-002: `listing_copy` is a dict
- B12-005: `listing_copy` is a NoneType
- B12-010: `listing_copy` is a str
