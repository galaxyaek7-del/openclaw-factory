# B12-004 Gumroad Listing Package (local prep — NOT published)

Cycle 97, 2026-10-18. Everything below is prepared and gated; **nothing is uploaded and the product is not published.**

## Product title
Meeting Cost & ROI Calculator

## Short description
Price every recurring meeting, cut the expensive ones that end in no decision. 5-sheet workbook + 4-page method guide. Instant download.

## Full description (paste verbatim from `drafts/b12_004_listing_copy.txt`)
Your recurring meetings have a price tag — this workbook calculates it. Give each meeting its attendee count and a fully-loaded hourly rate, and it returns the weekly and annual cost, the person-hours, and the one number worth arguing about: cost per decision. Sort by annual cost and cut from the top.

Built for the person who suspects the weekly round-robin is expensive and wants the number, not a productivity tip. Includes a worked example (a 7-person daily standup at $65/hr runs about $26,160/year — the same team shortens one biweekly planning meeting and recovers around $5,200/year), a polite decline script, and a quarterly kill-review process.

Inside (2 files):
- Meeting Cost & ROI Calculator workbook (.xlsx, 5 sheets): Setup (your loaded rate and threshold), MeetingLog (one row per meeting, with input validation and guarded formulas), Dashboard (annual cost, cost per decision, zero-decision savings, most expensive meeting), Rules, and a README.
- Meeting Cost & ROI Method Guide (.pdf, 4 pages): how to price a meeting honestly (the loaded rate plus employer surcharge), how to run the quarterly kill review, five mistakes that ruin the number, and answers to the usual objections.

New product from Galaxy Forge: no sales recorded yet, no reviews.

Requires: Excel, LibreOffice Calc (free), or Google Sheets (free upload) for the workbook; any PDF reader for the guide. Instant download after purchase. Support: reply to your Gumroad receipt email.

## Intended buyer
Team leads, managers and founders with calendar-heavy teams. (Demand evidence is real and cited in `reports/B12-004/DEMAND_EVIDENCE_2026-10-18.json`; "this specific buyer pays for THIS workbook" is still unproven — no sales yet.)

## Deliverables (canonical, hashed)
- `books/batch12/B12-004_meeting_cost_roi_calculator.xlsx` — 12,865 B, sha256 `87ecb1cd223ebf615c46bf49a74c1feb70ea5131a1da9c14dcedff470ccac820`
- `books/batch12/B12-004_meeting_method_guide.pdf` — 9,639 B, sha256 `2c964edcfc8a9dcfb45d6bfcde23da85871ec6b3deacc39a10c71cf227972a46`
(never silently replaced; rebuild only via `scripts/build_batch12_xlsx.py` / `build_batch12_pdfs.py` on a documented defect)

## Price
$11.99 USD one-time — **FOUNDER-APPROVED 2026-10-18.** The checkout-display confirmation the founder attached to the approval is **BLOCKED**: no Gumroad listing exists yet (see Cycle-98 report), so there is nothing to display.
4 real paid comparables (highest $12.00: Kosmic Rift $12.00, Meeting Tax $9.00, QUICKFix $5.77, Meeting Notes & Action Items $2.40). The gate's `price_within_market` ceiling is $13.20, so the manifest's earlier **$19.00 is NOT_READY** (`reports/B12-004/GATE_FINAL_2026-10-18.json`). Gate: APPROVED at $11.99, NOT_READY at $19.00.

## Tags
meetings, productivity, management, calculator, spreadsheet, roi, cost, team

## Cover
`reports/B12-004/cover.png` — 1280x720 PNG, title-only design on the theme colour (no book-cover match found, no price shown), verified non-blank (luma stddev 29.4). Gumroad's API has no cover upload; uploading the cover is the founder's action.

## Pre-publication checklist
- [x] Title pasted exactly
- [x] Description pasted exactly (keeps the 0-sales disclosure; brand + content-safety checks PASS)
- [ ] Price confirmed by the founder ($11.99 recommended; $19.00 fails the gate)
- [ ] Both files uploaded (verify byte counts after upload)
- [ ] Cover uploaded
- [ ] Preview confirmed
- [ ] STOP: publish only with an explicit B12-004 authorization phrase

## Gate evidence
`reports/B12-004/GATE_FINAL_2026-10-18.json` — core_value 100, content_quality PASS (depth sufficient), market_reality 70 PASS at $11.99.
