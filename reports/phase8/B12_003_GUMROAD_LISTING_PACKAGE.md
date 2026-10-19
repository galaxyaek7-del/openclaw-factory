# B12-003 Gumroad Listing Package (PUBLISHED — 2026-10-19)

Cycle 98 prep, updated Cycle 99 (2026-10-19). Final price USD 8.00. **PUBLISHED and independently verified** at https://aekraft.gumroad.com/l/svlky (product id `TFeaaWXO3zySimrs2Jbjbw==`): published=true, price 800 cents, 8 tags, cover attached, both deliverables attached (xlsx 13,594 B + pdf 19,095 B), 0 sales. Evidence: `data/cycle99_b12_003_live_verification.json`.

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
$8.00 USD one-time — **FINAL (Cycle 99 founder directive, 2026-10-19)** (`FOUNDER_DECISION_BELOW_COMPARABLE`).
14 real paid comparables ($6.75–$79); the direct business-continuity cluster is $37–$79, the closest-shape single-download packs are $6.75–$20.22. $8.00 is the **highest price that clears the mandatory market-realism policy** for an 8-page guide (`economics.market_realism_check(price, page_count=8)` permits at most `min($1.00 × 8, $15.00) = $8.00`); the earlier $19.00 record failed that gate and is superseded. It prices below the entire direct business-continuity cluster. Gate: **APPROVED at $8.00** — core 100 / content 100 / market 70 (`reports/B12-003/GATE_FINAL_2026-10-19.json`); $11.99, $14.99, $19.00 and $29.00 are also APPROVED on the quality gate, but only $8.00 passes *both* gates.

## Tags
business continuity, solo founder, checklist, spreadsheet, emergency, access, succession, template

## Cover
`reports/B12-003/cover.png` — 1280x720 PNG, title-only design on the theme colour (no book-cover match found, no price shown), verified non-blank (luma stddev 30.8), sha256 `943429b9687cd809fb49d61aa1164b2322fe5a18261eba5e00aa7c9b34023d6c`. **Attached live (2026-10-19)** via `channels/gumroad_publisher.add_product_cover` from the public URL `https://raw.githubusercontent.com/galaxyaek7-del/openclaw-factory/main/reports/B12-003/cover.png` (`main` push `6d213fa`); verified: `covers_count=1`, `main_cover_id 85df16acb420f4494b5c67e70ec5bf08`, read-back sha256 identical to the canonical cover.

## Pre-publication checklist
- [x] Title pasted exactly
- [x] Description pasted exactly (keeps the 0-sales disclosure; brand + content-safety checks PASS)
- [x] Price set to the final, gate-passing $8.00 (Cycle 99 directive)
- [x] Both files uploaded (live read-back: xlsx 13,594 B + pdf 19,095 B, exact canonical sizes)
- [x] Cover attached (verified live, 1 cover)
- [x] Preview confirmed (published live; public page HTTP 200, USD 8.00)
- [x] STOP lifted: explicit B12-003 authorization given (Cycle 99 directive)

## Publication record
Live: https://aekraft.gumroad.com/l/svlky · product id `TFeaaWXO3zySimrs2Jbjbw==` · published 2026-10-19.
Sequence: sanctioned phrase-gated flow (`--run --authorize-draft --publish-authorization "APPROVE B12-003 PUBLISH"`), then `--apply-listing` (8 tags + description), then `--attach-cover`, then `--republish`. Independent verification: `data/cycle99_b12_003_live_verification.json` (all checks PASS; one honest UNKNOWN for the page's absent availability meta, which is absent on every Gumroad listing). Sales: 0 (authoritative `GET /v2/sales`).

## Gate evidence
`reports/B12-003/GATE_FINAL_2026-10-19.json` — core_value 100, content_quality 100 PASS (3,235 words vs 800 required at $8.00; 6 sheets / 20 formulas), market_reality 70 PASS at $8.00. QA: `reports/B12-003/QA_FACTS_2026-10-19.json` (technical inspection PASS 6/6; brand_dna PASS; the four Executive Safety checks PASS; the Dashboard's Continuity-readiness logic re-derived independently across 6 boundary scenarios).

## Disclosed economics note
`economics.market_realism_check(8.00, page_count=8, platform='gumroad_digital')` returns `(True, 8.00)` — the selected price now agrees with the factory's own policy. At 8 pages the per-page ceiling is $8.00, so the auto-distribution path (`distributor.py` → `schemas/product.py::from_jsonl_record()`) would no longer re-price this product; previously (at $19.00) it silently would have. The founder-authorized first-sale path (`scripts/first_sale_orchestrator.py`) never repriced. This is why the final price is $8.00: it is the highest price that passes every mandatory gate in every layer.
