# B13-001 Listing Payload

**State:** `LOCAL_READY__AWAITS_FOUNDER_LISTING_AUTHORIZATION`
**Published:** no · **Gumroad call made:** no · **Price:** $15.00 (selected by the founder, not authorized for a live listing)

## Deliverables

| file | bytes | sha256 |
|---|---|---|
| `books/batch13/B13-001_renovation_allowance_control.xlsx` | 23894 | `6a48ebc859a064ac...` |
| `books/batch13/B13-001_renovation_allowance_control_guide.pdf` | 41858 | `7f8218938a794392...` |

## Verification cited

- Gate: `reports/B13-001/GATE_FINAL_2026-10-20.json` — state `QA_PASS_AT_19_USD_AWAITING_LISTING_AND_PUBLICATION_AUTHORIZATION` (recorded at the earlier $19 proposal)
- Gate at the selected price: `reports/B13-001/GATE_SELECTED_PRICE_2026-10-20.json` — verdict `APPROVED` at $15.00
- Guide inspection: `reports/B13-001/GUIDE_INSPECTION_2026-10-20.json` — 15 pages, 8298 words
- Workbook QA: `reports/B13-001/WORKBOOK_QA_2026-10-20.json` — verdict `PASS`, 416 formula cells
- Brand check: PASS

## Price realism (computed by economics.evaluate, this round)

| price | platform | pages | role | approved | net | floor | realistic | suggested |
|---|---|---|---|---|---|---|---|---|
| $15.00 | gumroad_digital | 15 | selected | yes | $13.50 | $2.50 | yes | $15.00 |
| $19.00 | gumroad_digital | 15 | previous proposal; fails realism below 30 pages | yes | $17.10 | $2.50 | no | $15.00 |
| $19.00 | gumroad_digital | 30 | what $19 would require: 30 pages or more | yes | $17.10 | $2.50 | yes | $19.00 |
| $19.00 | gumroad_premium | 15 | premium tier at the current depth | no | $17.10 | $25.00 | yes | $19.00 |
| $27.99 | gumroad_premium | 15 | premium alternative that clears the $25 net floor | yes | $25.19 | $25.00 | yes | $27.99 |

The guide is 15 pages. Two independent ceilings decide whether a price is credible. First, any book under 30 pages is capped at $15 absolute. Second, below that cap a price must stay at or under $1 per page. $19 at 15 pages clears the profit floor but fails realism, and stays that way until the guide reaches 30 pages. $15 is the highest price that clears both checks on gumroad_digital (net $13.50 against a $2.50 floor), which is why the founder selected it as the preferred proposed price on 2026-10-20 and declined to expand the guide merely to justify $19. On gumroad_premium, $19 is realistic but rejected on profit (that tier's net floor is $25, needing $27.78 or more). No live listing or platform price was changed: this remains a local proposal.

Selected: $15.00 on gumroad_digital at 15 pages, as the highest price that is both approved and realistic at the deliverable's actual depth.

## Founder decision

- Decided: 2026-10-20
- Preferred price: $15.00
- Scope: preferred pricing direction only; not a listing or publication authorization
- Expand the guide to 30 pages to justify $19: declined by the founder
- Publication authorized: False · live price changed: False

## Still blocked

FACTORY_LIVE_PUBLISH=false and no active write scope; create_product and enable_product are not scopable.

Minimal action: Founder sets FACTORY_LIVE_PUBLISH=true for the run and completes a fresh gumroad_auth_watch.poll() so auth state is VERIFIED and not stale.

## Problems

- none
