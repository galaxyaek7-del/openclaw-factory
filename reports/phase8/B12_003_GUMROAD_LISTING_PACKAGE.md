# B12-003 Gumroad Listing Package (local prep — NOT published)

Cycle 98, 2026-10-19. Everything below is prepared and gated; **nothing is uploaded and the product is not published.**

## Product title
Founder Access Continuity Organizer

## Short description
One row per thing your business runs on, one row per person allowed to touch it, and a three-envelope custody method — so a successor can keep the business alive without you ever writing a password on paper. 6-sheet inventory + 8-page guide. Instant download.

## Full description (paste verbatim from `drafts/b12_003_listing_copy.txt`)
A one-person business has one single point of failure: you. If you are in hospital, offline for a week, or simply unreachable, the business does not pause — it fails quietly, because nobody else knows what it runs on or how to get back in. This is the organizer that fixes that, without ever writing a password on paper.

Built for solo founders and one-person businesses. The rule is the same one the best products in this category use: this is a map, not a vault. It records what exists, where it lives, and who is allowed to touch it — and it routes every secret through a password manager's emergency access, so the plan is useful to a successor without ever being a liability in a drawer.

Inside (2 files):
- Founder Access Continuity Inventory workbook (.xlsx, 6 sheets): Systems (one row per thing the business runs on — what it is, where it lives, who can reach it, the recovery route, whether a second person can get in, criticality 1-5, and when it was last verified), Holders (who may touch what, and the authority basis for it), Envelopes (the three-envelope custody method pre-filled: the map, the keys via password-manager emergency access, and a sealed letter), DrillLog (the annual 30-minute drill, with next-due dates computed), Dashboard (coverage %, critical-gap count, days since the last drill and a single Continuity readiness verdict), and a README. Includes worked example rows.
- Founder Access Continuity Guide (.pdf, 8 pages): the inventory-not-vault rule, what "unreachable" actually means, the three-envelope method, how to name holders inside legal boundaries, the password-manager emergency-access walk-through, the 30-day keep-alive plan, the annual drill, your successor's first 72 hours, ten failure modes this plan prevents, boundaries (this is an organizing system, not a will and not legal advice), an FAQ, and a completion checklist.

New product from Galaxy Forge: no sales recorded yet, no reviews.

Requires: Excel, LibreOffice Calc (free), or Google Sheets (free upload) for the workbook; any PDF reader for the guide. Instant download after purchase. Support: reply to your Gumroad receipt email.

## Intended buyer
Solo founders and one-person businesses who are the single point of failure for everything the business needs. (Demand evidence is real and cited in `reports/B12-003/DEMAND_EVIDENCE_2026-10-19.json` and `data/evidence/b12_003_competitors.json` — 14 real paid comparables, $6.75–$79, MEDIUM-HIGH competition; "this specific buyer pays for THIS pack" is still unproven — no sales yet.)

## Deliverables (canonical, hashed)
- `books/batch12/B12-003_access_continuity_organizer.pdf` — 19,095 B, sha256 `c9c18a4b0505828a1eabaf6a72a2aba8cc6ef5024c8ebe543e47f971889000fb` (8 pages, 3,235 words)
- `books/batch12/B12-003_access_continuity_inventory.xlsx` — 13,594 B, sha256 `7cf3e46fa8c2470e1a14c91ff983bf186542fb92f005a0305ff3cacdf9d5edd5` (6 sheets, 20 formulas, 7 data validations)
(never silently replaced; rebuild only via `scripts/build_batch12_pdfs.py` / `scripts/build_batch12_xlsx.py::b12_003_access_continuity_inventory` on a documented defect)

## Price
$19.00 USD one-time — **FOUNDER-APPROVED 2026-10-19** (`FOUNDER_DECISION_BELOW_COMPARABLE`).
14 real paid comparables ($6.75–$79); the direct business-continuity cluster is $37–$79, the closest-shape single-download packs are $6.75–$20.22. The approved $19.00 sits below every direct comparable; it is above the factory's own $15.00 short-book ceiling (a deliberate founder choice). Gate: **APPROVED at $19.00** — core 100 / content 100 / market 70 (`reports/B12-003/GATE_FINAL_2026-10-19.json`); $11.99, $14.99 and $29.00 are also APPROVED.

## Tags
business continuity, solo founder, checklist, spreadsheet, emergency, access, succession, template

## Cover
`reports/B12-003/cover.png` — 1280x720 PNG, title-only design on the theme colour (no book-cover match found, no price shown), verified non-blank (luma stddev 30.8), sha256 `943429b9687cd809fb49d61aa1164b2322fe5a18261eba5e00aa7c9b34023d6c`. Gumroad's API has no cover upload; uploading the cover is the founder's action.

## Pre-publication checklist
- [x] Title pasted exactly
- [x] Description pasted exactly (keeps the 0-sales disclosure; brand + content-safety checks PASS)
- [x] Price confirmed by the founder ($19.00 approved 2026-10-19)
- [ ] Both files uploaded (verify byte counts after upload)
- [ ] Cover uploaded
- [ ] Preview confirmed
- [ ] STOP: publish only with an explicit B12-003 authorization phrase

## Gate evidence
`reports/B12-003/GATE_FINAL_2026-10-19.json` — core_value 100, content_quality 100 PASS (3,235 words vs 1,499 required at $14.99; 6 sheets / 20 formulas), market_reality 70 PASS at $19.00. QA: `reports/B12-003/QA_FACTS_2026-10-19.json` (technical inspection PASS 6/6; brand_dna PASS; the four Executive Safety checks PASS; the Dashboard's Continuity-readiness logic re-derived independently across 6 boundary scenarios).

## Disclosed economics note
`economics.market_realism_check(19.00, page_count=8, platform='gumroad_digital')` returns `(False, 8.00)`: at 8 pages the per-page ceiling is $8.00, so the **auto-distribution** path (`distributor.py` → `schemas/product.py::from_jsonl_record()`) would silently re-price this product to $8.00. The founder-authorized first-sale path (`scripts/first_sale_orchestrator.py`) does not use `schemas/product.py` and publishes the manifest price directly, so this risk applies only to the auto path. Recorded here rather than hidden.
