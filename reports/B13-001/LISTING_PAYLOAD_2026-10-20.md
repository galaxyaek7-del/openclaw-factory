# B13-001 Listing Payload

**State:** `LOCAL_READY__AWAITS_FOUNDER_LISTING_AUTHORIZATION`
**Published:** no · **Gumroad call made:** no · **Price:** $19.00 (proposed, not authorized)

## Deliverables

| file | bytes | sha256 |
|---|---|---|
| `books/batch13/B13-001_renovation_allowance_control.xlsx` | 23871 | `028b9ed14e80ddb8...` |
| `books/batch13/B13-001_renovation_allowance_control_guide.pdf` | 41652 | `6c82a7147fbca4eb...` |

## Verification cited

- Gate: `reports/B13-001/GATE_FINAL_2026-10-20.json` — state `QA_PASS_AT_19_USD_AWAITING_LISTING_AND_PUBLICATION_AUTHORIZATION`
- Guide inspection: `reports/B13-001/GUIDE_INSPECTION_2026-10-20.json` — 15 pages, 8237 words
- Workbook QA: `reports/B13-001/WORKBOOK_QA_2026-10-20.json` — verdict `PASS`, 415 formula cells
- Brand check: PASS

## Price realism (computed by economics.evaluate, this round)

| price | platform | pages | approved | net | floor | realistic | suggested |
|---|---|---|---|---|---|---|---|
| $19.00 | gumroad_digital | 15 | yes | $17.10 | $2.50 | no | $15.00 |
| $19.00 | gumroad_premium | 15 | no | $17.10 | $25.00 | yes | $19.00 |
| $19.00 | gumroad_digital | 30 | yes | $17.10 | $2.50 | yes | $19.00 |
| $15.00 | gumroad_digital | 15 | yes | $13.50 | $2.50 | yes | $15.00 |

The guide is now 15 pages. Two independent ceilings decide whether a price is credible. First, any book under 30 pages is capped at $15 absolute. Second, below that cap a price must stay at or under $1 per page. So $19 is still marked unrealistic at 15 pages even though the profit floor is cleared, and it stays that way until the guide reaches 30 pages. At the current depth, $15 is the highest price that clears both checks on gumroad_digital (net $13.50, against a $2.50 floor). On gumroad_premium, $19 is realistic but rejected on profit, because that tier's net floor is $25, which needs $27.78 or more. Nothing was repriced here: price changes need founder authorization.

Recommended: Authorize $15.00, then grow the guide toward 30 pages and revisit $19 once the content genuinely earns it. The price should follow the product, not lead it.

## Still blocked

FACTORY_LIVE_PUBLISH=false and no active write scope; create_product and enable_product are not scopable.

Minimal action: Founder sets FACTORY_LIVE_PUBLISH=true for the run and completes a fresh gumroad_auth_watch.poll() so auth state is VERIFIED and not stale.

## Problems

- none
