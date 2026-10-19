# B12-010 Gumroad Listing Package (READY FOR AUTHORIZATION — 2026-10-19)

Cycle 100 (2026-10-19) demand re-validation, rebuild, deep QA and pricing round. Price USD 15.00 **DERIVED** (highest price passing every mandatory gate), not founder-approved. **NOT LISTED** — no Gumroad listing exists for this product and none may be created without a separate, explicit, product-specific founder authorization. Evidence: `reports/B12-010/GATE_FINAL_2026-10-19.json`, `reports/B12-010/GATE_CANDIDATES_2026-10-19.json`, `reports/B12-010/QA_FACTS_2026-10-19.json`, `reports/B12-010/MANIFEST_2026-10-19.json`.

## Product title
Nonprofit Grant Pipeline Tracker

## Short description
One register for every funder and program: a twelve-question eligibility screen, per-application document readiness, computed deadline states, and a post-award reporting calendar that steps forward in whole intervals so a report is never missed. 9-sheet workbook plus a 17-page method guide. Instant download.

## Full description (paste verbatim from `drafts/b12_010_listing_copy.txt`)
Grant work fails in two specific ways. The first is weeks of writing spent on applications that were never eligible. The second is an award put at risk because a report due date lived in one person's head. This kit is built to close both gaps.

It is one register plus one honest method. Every funder and program is a row. Every required document is tracked against that row, so you can see readiness before you write. Every deadline and every post-award report is computed from its own date, so the state is correct the moment you open the file rather than whenever someone remembers to check.

Inside (2 files):
- Grant Pipeline Tracker workbook (.xlsx, 9 sheets): Opportunities (one row per funder and program, with award range, deadline, status, owner and source), Docs (required vs. ready, per application, with where each file lives), Budget (requested vs. confirmed, per line), Timeline (every post-award report, with first due date and repeat interval in days), Dashboard (tracked, active, submitted, decisions, award rate, awarded vs. requested, overdue, due within 14 days, next open deadline, missing documents, duplicate rows, data problems, post-award reports overdue, and a single plain-language Pipeline verdict), plus Stages, Eligibility (twelve must-pass questions), DocLibrary (twelve standard documents and how often each needs refreshing) and a README. Includes four worked example rows and 427 formulas.
- Grant Pipeline Method Guide (.pdf, 17 pages, 28 sections): what the kit is and is not, the eligibility-before-drafting rule, the seven stages and their exit gates, twenty-minute setup, a field dictionary for every column, how the deadline maths and the reporting cadence maths behave, how document readiness is counted, how duplicates and row problems are found, the twelve must-pass eligibility questions, the standard document library, writing narratives from reusable blocks, a budget narrative that survives review, a worked 90-day example, the four-line decline post-mortem, a monthly sixty-minute review, twenty mistakes, reporting after award, compatibility and limitations, FAQ, glossary, and a first-ninety-minutes checklist.

The design choices are deliberate: the deadline state is a sentence, not a colour, because a sentence can be counted and sorted. A document is marked ready only when it exists and is current, not when someone knows where it is. A closed row keeps its history instead of being deleted, because a pipeline that only shows live work cannot tell you that the same funder has declined you twice.

Honest limits: this does not find funders, submit applications, contact anyone, monitor portals, or predict whether you will be funded. It is an organising system for your own work. Eligibility rules, award ranges, match requirements and reporting obligations are set by each funder and by law, and the funder's own guidelines always take precedence. It is not legal, tax, accounting or financial advice. The workbook uses standard spreadsheet functions and is built for Excel; it imports into Google Sheets in ordinary use, but verify the computed columns after import.

New product from Galaxy Forge: no sales recorded yet, no reviews.

Requires: a spreadsheet application that opens .xlsx (Excel, or Google Sheets after import) for the workbook; any PDF reader for the guide. Instant download after purchase. Support: reply to your Gumroad receipt email.

## Intended buyer
Small nonprofits, fiscal sponsors and volunteer grant writers running several applications without a dedicated grants system. Demand evidence is real and cited in `reports/B12-010/DEMAND_EVIDENCE_2026-10-19.json`, `reports/B12-010/DEMAND_VALIDATION_CYCLE100_2026-10-19.json` and `data/evidence/b12_010_competitors.json` — 9 sourced comparables, paid single-file cluster $6.98–$19.97, review counts in the hundreds, and a $67 bundle. "This specific buyer pays for THIS kit" remains unproven: there are still no sales.

## Deliverables (canonical, hashed)
- `books/batch12/B12-010_grant_pipeline_tracker.xlsx` — 38,775 B, sha256 `def9f4c290ff385c79b904e044eaf6c3d454df561991fb20c760eecfcf132eab` (9 sheets, 427 formulas, 11 data validations)
- `books/batch12/B12-010_grant_pipeline_guide.pdf` — 45,453 B, sha256 `b7ad0849a7d248db821c79873a8cdc3c42399a6ce054083eaf650298e97f0a49` (17 pages, 8,198 words, 28 sections)
- `books/covers/B12-010.png` — 42,566 B, sha256 `c17de7066cbd9bf22affa138881fc67ed3d64e7598756277b807836eaaf122ec` (1280×720 listing image)
(never silently replaced; rebuild only via `scripts/build_batch12_xlsx.py::b12_010_grant_pipeline` / `scripts/build_batch12_pdfs.py` on a documented defect)

## Price
$15.00 USD one-time — **DERIVED (Cycle 100 pricing rule, 2026-10-19)**; `HIGHEST_PRICE_PASSING_ALL_MANDATORY_GATES`. Pending founder listing authorization; not a founder price approval.

9 sourced comparables ($6.98–$111.25; the paid single-file cluster is $6.98–$19.97, the $67 bundle and one $111.25 listing with 0 sales sit outside it). $15.00 is the **highest price that clears the mandatory page-based market-realism policy** for a 17-page guide (`economics.market_realism_check(price, page_count=17)` permits at most `min($1.00 × 17, $15.00) = $15.00`); the manifest's $39.00 fails that gate. It is also independently supported by the market: a comparable with 1.5k reviews is listed at exactly $15.00.

Gate matrix (`reports/B12-010/GATE_CANDIDATES_2026-10-19.json`):

| Price | Quality gate | Economics | Market realism | Verdict |
|---|---|---|---|---|
| $19.97 | APPROVED 100/100/70 | net $17.97 ≥ $2.50 | **FAIL** (ceiling $15.00) | rejected |
| $17.99 | APPROVED 100/100/70 | net $16.19 ≥ $2.50 | **FAIL** (ceiling $15.00) | rejected |
| $15.00 | APPROVED 100/100/70 | net $13.50 ≥ $2.50 | PASS | **winner** |
| $14.99 | APPROVED 100/100/70 | net $13.49 ≥ $2.50 | PASS | passes |
| $12.99 | APPROVED 100/100/70 | net $11.69 ≥ $2.50 | PASS | passes |

## Tags
nonprofit, grant tracker, grant management, grant spreadsheet, nonprofit templates, grant reporting, excel template, google sheets, grants calendar, nonprofit operations

## Cover
`books/covers/B12-010.png` — 1280×720 PNG on the Galaxy Forge dark theme, category badge "NONPROFIT OPERATIONS", price badge $15. Generated by `scripts/generate_all_covers.py::generate_cover` (the same generator as every other Batch 12 cover). **NOT attached** — no listing exists.

## Pre-publication checklist
- [ ] Title pasted exactly
- [ ] Description pasted exactly (keeps the 0-sales disclosure; brand + content-safety checks PASS)
- [ ] Price set to the gate-passing $15.00 (pending founder authorization)
- [ ] Both files uploaded and read back at the canonical sizes
- [ ] Cover attached
- [ ] Preview confirmed
- [ ] Explicit B12-010 authorization given (NOT yet given — this page is not a publication record)

## Publication record
NONE. No listing created, modified or enabled. `FACTORY_LIVE_PUBLISH` was never set for this product; no write-gate authorization was requested. Publication requires a separate founder directive naming B12-010.

## Gate evidence
`reports/B12-010/GATE_FINAL_2026-10-19.json` — core_value 100, content_quality 100 PASS (8,198 guide words + sheet text = 8,324 against 1,500 required at $15.00; 9 sheets / 427 formulas / 11 data validations), market_reality 70 PASS (9 sourced competitors, price within the observed market; no payment evidence exists for this niche, which is disclosed rather than inferred). QA: `reports/B12-010/QA_FACTS_2026-10-19.json` — brand_dna PASS, the four Executive Safety checks PASS, and every computed workbook rule re-derived independently in Python against the four example rows.

## Cross-artifact consistency verified
The guide and workbook describe the same product: 12 eligibility questions, 12 documents, 7 stages, identical column names A–V, DUE IN at 14 days (opportunities) and 30 days (reports), and the same three closed statuses. Nine specific checks are recorded in `QA_FACTS_2026-10-19.json` under `cross_artifact_consistency`.

## Disclosed economics note
`economics.market_realism_check(15.00, page_count=17, platform='gumroad_digital')` returns `(True, 15.00)`; $17.99 and $19.97 return `(False, 15.00)`. The auto-distribution path (`distributor.py` → `schemas/product.py::from_jsonl_record()`) would silently re-price a 17-page `gumroad_digital` product to $15.00, so $15.00 is the only price at which the quality gate, the depth rule and the economics policy all agree. Because at exactly 30 pages the short-book cap stops applying, a 30-page guide would permit up to $30.00 — but reaching 30 pages would require about 6,000 more genuine words, and padding a guide to clear a pricing gate would violate the no-fabrication rule. $15.00 is the honest price for this artifact.

## Disclosed limitations (not defects)
- Workbook math was **not** recalculated by a spreadsheet engine: this environment has no LibreOffice/Excel. Every rule was re-implemented independently in Python, and the example rows agree; the formulas are shipped in `reports/B12-010/formulas_*.txt` for audit.
- The eligibility screen and document library are general practice, not any specific funder's rules. The guide says so in three places.
- The cover is 1280×720 landscape, consistent with every other Batch 12 cover and correct for Gumroad; it is not a KDP cover.
