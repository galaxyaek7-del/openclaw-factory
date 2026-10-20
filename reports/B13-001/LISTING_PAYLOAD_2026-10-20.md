# B13-001 Listing Payload

**State:** `LOCAL_READY__AWAITS_FOUNDER_LISTING_AUTHORIZATION`
**Published:** no · **Gumroad call made:** no · **Price:** $19.00 (proposed, not authorized)

## Deliverables

| file | bytes | sha256 |
|---|---|---|
| `books/batch13/B13-001_renovation_allowance_control.xlsx` | 23871 | `028b9ed14e80ddb8...` |
| `books/batch13/B13-001_renovation_allowance_control_guide.pdf` | 19861 | `53c65af902c99d0e...` |

## Verification cited

- Gate: `reports/B13-001/GATE_FINAL_2026-10-20.json` — state `QA_PASS_AT_19_USD_AWAITING_LISTING_AND_PUBLICATION_AUTHORIZATION`
- Guide inspection: `reports/B13-001/GUIDE_INSPECTION_2026-10-20.json` — 7 pages, None words
- Workbook QA: `reports/B13-001/WORKBOOK_QA_2026-10-20.json` — verdict `PASS`, 415 formula cells
- Brand check: PASS

## Price realism (computed by economics.evaluate, this round)

| platform | pages | approved | net | floor | realistic | suggested |
|---|---|---|---|---|---|---|
| gumroad_digital | 7 | yes | $17.10 | $2.50 | no | $7.00 |
| gumroad_premium | 7 | no | $17.10 | $25.00 | yes | $19.00 |
| gumroad_digital | 30 | yes | $17.10 | $2.50 | yes | $19.00 |
| gumroad_premium | 8 | no | $17.10 | $25.00 | yes | $19.00 |

At 7 pages, $19 is approved on gumroad_digital (net floor $2.50) but market_realistic is false (sub-30-page ceiling $15, then $1/page suggests $7). $19 cannot pass gumroad_premium because its $25 net floor requires at least $27.78. The price is therefore approved-but-unrealistic on one tier and rejected-on-profit on the other. Not changed here: price changes need founder authorization.

Recommended: Grow the guide to 30+ pages and keep $19. It is the only option that improves the product rather than the arithmetic.

## Still blocked

FACTORY_LIVE_PUBLISH=false and no active write scope; create_product and enable_product are not scopable.

Minimal action: Founder sets FACTORY_LIVE_PUBLISH=true for the run and completes a fresh gumroad_auth_watch.poll() so auth state is VERIFIED and not stale.

## Problems

- none
