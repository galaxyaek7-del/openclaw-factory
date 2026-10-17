# B12-001 — readiness for the first verified sale (Cycle 91, 2026-10-17)

> **Superseded in part (Cycle 94):** the workbook was repaired again (input validation, guarded outputs).
> Current file: 8,922 B, sha256 `aee8fc0b100345e7abc6e8a41487ddf551b5b7f235c6f4324827d1c6ab8a092d`.
> The current state and the exact action requested are in `APPROVAL_PACKET_CYCLE94.md`.


**Status:** READY FOR FOUNDER DRAFT. Publication is LOCKED; nothing has been published.

**Copy-paste steps:** `reports/B12-001/PUBLISH_NOW.md`.

## Exact package
| Item | Value | Evidence |
|---|---|---|
| Title | Freelancer Rate & Raise Calculator | OBSERVED (`data/product_batch_12.json`) |
| Price | $14.99 | Founder decision. A price hypothesis, not a validated optimum |
| Deliverable | `books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx`, sha256 `09410945234ee431bf970cb77ad2ca21424e7c0cf6a64731c04f30c03953e4d3` (8,359 B; repaired in Cycle 88) | OBSERVED |
| Cover | `reports/B12-001/cover.png`, 1280×720, sha256 `46f7e5eb3ad4…` | OBSERVED |
| Tags | freelancing, pricing, rate calculator, consultant, spreadsheet, raise, excel template, solo consultant | OBSERVED (`data/seo/b12_001_tags.json`) |
| Description | PUBLISH_NOW.md, step 4 | — |

## Claims, classified
| Claim | Class | Basis |
|---|---|---|
| Computes a minimum rate from 6 cost inputs | OBSERVED | Excel 16 recalculation: $104.60/hr minimum, $120.29/hr with the 15% margin; no error cells |
| 4 sheets; README with 4 steps; no macros or external links | OBSERVED | openpyxl + zip inspection |
| RaisePlanner follows the user's own rate | OBSERVED | Changing take-home pay changed the raise targets (after the Cycle 88 repair) |
| Works in LibreOffice / Google Sheets | INFERRED | Plain arithmetic and one cross-sheet reference; not tested |
| "Support: reply to your Gumroad receipt email" | UNKNOWN | Depends on the founder's Gumroad settings |
| "No sales recorded yet, no reviews" | OBSERVED | Gumroad sales read: 0 |
| Competitor prices $19.00 / $4.99 / €28 (≈$31.46) | OBSERVED by Claude (page price metadata, read-only); founder confirmation pending | `data/evidence/b12_competitors.json` |
| Demand for B12-001 itself | UNKNOWN | No sale, no proof of payment |
| Quality gate 100/100/70, APPROVED | DERIVED | Structural checks (see PUBLICATION_CHECKLIST_CYCLE88.md for what each number measures) |

## How a listing can be created
- **Manual, recommended:** the founder creates a draft on Gumroad from PUBLISH_NOW.md and uploads the two files above.
- **Through the factory: blocked by design.** `FACTORY_LIVE_PUBLISH=false`. Even with it on, a create needs a single-use scoped upload authorization (`channels/write_scope.py`), and is refused if a listing with this title already exists (Cycle 91).

## The exact next action (founder)
1. Confirm the three competitor links in `data/evidence/b12_competitors.json`.
2. Create the **draft** on Gumroad from PUBLISH_NOW.md, using the repaired xlsx (sha256 above), and send the draft link for review.
3. After the review, say "APPROVE B12-001 PUBLISH" and publish by hand.
