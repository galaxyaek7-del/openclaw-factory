# Listing repair preflight (2026-10-29)

Read-only verification of `scripts/apply_listing_repairs_20261029.py` before any live change.
Gumroad was read with GET only; nothing was written to Gumroad, no price changed, nothing was
published or unpublished, no customer was contacted. Evidence classes: OBSERVED, DERIVED, INFERRED, UNKNOWN.

## 1. Repository state (OBSERVED)

- Branch `main`; local HEAD = `origin/main` = `747c933` before this preflight (0 ahead, 0 behind).
- The repair script was committed in `c6dbe02` and `747c933`; the preflight fixes are committed with this report.
- Product files (PDF/XLSX/ZIP) are git-ignored by design (public repo) and exist only on the founder machine.

## 2. Discrepancies found and fixed by the preflight

| # | Finding | Class | Fix |
|---|---|---|---|
| 1 | Trademark guide v2 was built on `books/trademark_diy_filing_kit.pdf` (12,514 B, 21 Sep), not the live file (12,383 B) | OBSERVED | rebuilt on the byte-identical live copy `backups/catalog_audit_2026-10-14/KMNGNgO5gS85H_JppnygIg_0.pdf`; first 4 pages identical in text, page 5 is the fee correction |
| 2 | GPSR bundle used `books/gpsr_eu_seller_action_kit.pdf` (18,389 B), not the live file (18,208 B) | OBSERVED | bundle now uses the byte-identical live copy `backups/catalog_audit_2026-10-14/VPYaNkAdv7Yocko-lIJsZQ_0.pdf` |
| 3 | Text and PDF metadata of the local and live versions are identical; why the bytes differ | UNKNOWN | Gumroad re-serialisation is a possibility, not verified |
| 4 | Re-running the script would re-upload every bundle (not idempotent) | OBSERVED | the plan now reads each listing; one whose attachment already has exactly the bundle's size is `ALREADY_APPLIED` and is not uploaded; `tests/test_apply_listing_repairs.py` (3 tests) |
| 5 | vkqogv description ends "Instant digital download. PDF guide.", omitting the tracker and the correction page the bundle adds | OBSERVED | delivery-line edit added (32 description edits, was 31) |

## 3. The five file repairs

All five listings are published (OBSERVED, GET /v2/products/:id). Bundle members contain no internal,
test, temporary or credential files (name scan plus manual review).

| Listing | Product id | Price | Live file today | Bundle (bytes, sha256) | Members | Checks | Decision |
|---|---|---|---|---|---|---|---|
| vkqogv Trademark DIY Filing Action Kit | `KMNGNgO5gS85H_JppnygIg==` | $69 | 1 PDF, 12,383 B | 17,728 B, `1d5c0530` (updated, see note) | guide (live text + dated USPTO fee-correction page; 5 pp, 1,946 words), tracker XLSX (4 sheets) | fee sheet rebuilt on the USPTO schedule (effective 2025-01-19, read 2026-10-29): 9/9 formulas, 0 errors; 2 classes + SOU + 1 extension each = $1,250 (DERIVED, independent recompute) | **PASS** |
| fetmu GPSR EU Seller Action Kit | `VPYaNkAdv7Yocko-lIJsZQ==` | $79 | 1 PDF, 18,208 B | 20,209 B, `36fa0de1` | live guide (6 pp, 2,592 words), cost planner XLSX (4 sheets) | 2/2 formulas, 0 errors; the description already promised the planner | **PASS** |
| ciowwm EU Late Payment Recovery Kit | `8Vlc3zY6AkxU4DCe7IRVDA==` | $59 | 1 PDF, 3,863 B | 21,276 B, `941103da` | live guide (1 p, 392 words), calculator XLSX (4 sheets) | 1,224/1,224 formulas, 0 errors; the guide refers to "Tracker columns" = sheet "Invoice tracker" | **PASS** (guide still thin) |
| hasjmp Etsy Ads ROI Playbook + Calculator | `ZFXJttaaGoJvEE10JOXbWg==` | $39 | 1 PDF, 3,480 B | 21,925 B, `f7b10ee5` | live playbook (1 p, 300 words), calculator XLSX (4 sheets) | 1,427/1,427 formulas, 0 errors; the title promises the calculator | **PASS** |
| dyjavs Diminished Value Claim Kit | `f542PZ92SUPOjV9F5GJh-Q==` | $59 | 1 PDF, 9,630 B | 22,034 B, `432a26c0` | live guide (3 pp, 1,274 words), claim workbook XLSX (6 sheets) | 209/211 formulas, 0 errors; the other 2 are `COUNTIFS` with `TODAY()` (valid Excel; not implemented by the checker, so UNKNOWN by recompute); the guide refers to "workbook sheet 1" | **PASS** |

Update (same day): a second read of the USPTO schedule showed that the guide's "$200-250" and
"$225" are the paper-filing fees (statement of use $250, extension $225), not invented figures.
The correction page now shows electronic and paper amounts side by side and says so; the
bundle was rebuilt (17,728 B, `1d5c0530`) and passes the same checks.

The workbooks have never been opened in Excel (no cached values); Excel computes them on first open.
No workbook was opened in Excel during this preflight (UNKNOWN: rendering in Excel itself).

## 4. Description changes (32)

Only the quoted text changes; all other wording is untouched.

- 27 listings: " and this guide." -> " and a PDF guide." Verified: each of the 27 delivered bundles
  contains a guide PDF (manifest bundle opened; its live attachment matches the bundle byte for byte; OBSERVED).
- 5 listings: the delivery wording for the repaired bundles.

| Listing | Product id | Name | Price | Change |
|---|---|---|---|---|
| bqnvfq | `CL0s234DG4r2udkxHr7kLA==` | Car Buy vs Lease Calculator: Total Cost Over the | $12.00 | " and this guide." -> " and a PDF guide." |
| ciowwm | `8Vlc3zY6AkxU4DCe7IRVDA==` | EU Late Payment Recovery Kit | $59.00 | "A single, focused file you download and use immediately" -> "A short PDF guide plus a working XLSX calculator workbook (invoice tracker, notice ladder)" |
| ckwqjc | `2ghb4qzdl5JhAKGeXF0akg==` | Refinance Break-Even & Loan Comparison Calculato | $15.00 | " and this guide." -> " and a PDF guide." |
| czhxhu | `Hb8TH-s7cxGstm4QEEgVQQ==` | Service Business Pricing & Break-Even Calculator | $15.00 | " and this guide." -> " and a PDF guide." |
| dhtppr | `8XdiDpEEqLAH9Ga2tySC7g==` | PTO Accrual & Leave Balance Tracker for Small Te | $12.00 | " and this guide." -> " and a PDF guide." |
| dliccs | `1t5RKMmSW9x7m0p2rsepnQ==` | 13-Week Cash Flow Forecast for Small Business | $19.00 | " and this guide." -> " and a PDF guide." |
| dyjavs | `f542PZ92SUPOjV9F5GJh-Q==` | Diminished Value Claim Kit | $59.00 | "3-page PDF guide covering" -> "3-page PDF guide plus a six-sheet XLSX claim workbook, covering" |
| ebuszz | `lcJ2lwjpD3HR5am_3bfptA==` | Debt Payoff Planner (Avalanche or Snowball) | $12.00 | " and this guide." -> " and a PDF guide." |
| fdjqyp | `-wmI77eNf-3TzDfGBe1Jgg==` | Employee True Cost Calculator (US Small Business | $15.00 | " and this guide." -> " and a PDF guide." |
| fetmu | `VPYaNkAdv7Yocko-lIJsZQ==` | GPSR EU Seller Action Kit | $79.00 | "PDF cost planner" -> "XLSX cost planner workbook" |
| ffsehk | `38WirAIvIlaJbaiYsQ9FAA==` | SAFE Conversion & Dilution Calculator (Post-Mone | $19.00 | " and this guide." -> " and a PDF guide." |
| ghszog | `S0eTeiZhhVFonDvm2mFb_g==` | Home Renovation Budget & Contractor Quote Compar | $14.00 | " and this guide." -> " and a PDF guide." |
| gwwpri | `eJhjR5fM5Br17ppT_fYw5Q==` | Rent vs Buy Home Calculator: Net Worth Year by Y | $12.00 | " and this guide." -> " and a PDF guide." |
| hasjmp | `ZFXJttaaGoJvEE10JOXbWg==` | Etsy Ads ROI Playbook + Calculator | $39.00 | "A single, focused file you download and use immediately" -> "A short PDF playbook plus the XLSX calculator workbook (per-listing tracker, readiness check)" |
| jorsyy | `cLKKwcQ6QCCKWcdYXBA65Q==` | Event Budget & Ticket Break-Even Planner | $12.00 | " and this guide." -> " and a PDF guide." |
| jydqg | `fJ-hUH0SGHvrCtR_H5XLAA==` | Inventory Reorder Point & Stock Tracker | $15.00 | " and this guide." -> " and a PDF guide." |
| kidohv | `gt5WvCt8cwo9khRvVDINBg==` | Wedding Budget & Vendor Payment Planner | $12.00 | " and this guide." -> " and a PDF guide." |
| krrtdf | `UDcPST0OQGjcOK87hFo5kg==` | Sinking Funds & Emergency Fund Planner | $9.00 | " and this guide." -> " and a PDF guide." |
| mcwusn | `49bs32IwUFlq4jv-tIei1w==` | Startup Runway & Burn Planner | $15.00 | " and this guide." -> " and a PDF guide." |
| mfpqin | `JyKW6Ok1C3Ha1fjAjc8G9w==` | Rental Property Deal Analyzer | $24.00 | " and this guide." -> " and a PDF guide." |
| ntbvq | `sJSccVv73KZuXMHiI9yobA==` | Etsy & Shopify Product Profit Calculator | $12.00 | " and this guide." -> " and a PDF guide." |
| qevzns | `dvU4mMSDmnRL7TmKL_Sedg==` | Client Pipeline & Proposal Tracker | $14.00 | " and this guide." -> " and a PDF guide." |
| qhmtd | `54huoJb9O_0cNw082vIZpg==` | Membership & Subscription MRR and Churn Forecast | $15.00 | " and this guide." -> " and a PDF guide." |
| rlgdc | `-3jJcVkCfNPUKv8h7uQyDg==` | Business Mileage Log & Deduction Tracker (US) | $9.00 | " and this guide." -> " and a PDF guide." |
| sfcpyb | `yc_cbXmlKOtJfNndSsezYA==` | Price Increase Impact Calculator | $12.00 | " and this guide." -> " and a PDF guide." |
| ucgjwf | `Pe6E3FUlWedlcUMhec-2jg==` | Shift Schedule & Labor Cost Planner | $14.00 | " and this guide." -> " and a PDF guide." |
| uubnbi | `P43t_52yRtWP4_s4D_Ed0g==` | Zero-Based Monthly Budget Planner | $9.00 | " and this guide." -> " and a PDF guide." |
| xiimbr | `lcQ9eEXpJLX09C_3n76ZBQ==` | Freelance Project Profitability & Effective Hour | $12.00 | " and this guide." -> " and a PDF guide." |
| xmbbls | `GHzrD5U78JUlmKFXMeQmfg==` | Customer Lifetime Value & CAC Payback Calculator | $15.00 | " and this guide." -> " and a PDF guide." |
| ydgbnh | `_-vV2F76nlPPhIhCXeIyog==` | Self-Employed Quarterly Tax Set-Aside Planner (U | $12.00 | " and this guide." -> " and a PDF guide." |
| zbvxmr | `sRyzz1NDSQMGNuszNIsDsw==` | Solar Panel Payback & 25-Year Savings Calculator | $12.00 | " and this guide." -> " and a PDF guide." |
| vkqogv | `KMNGNgO5gS85H_JppnygIg==` | Trademark DIY Filing Action Kit | $69.00 | "Instant digital download. PDF guide." -> "Instant digital download: PDF guide (with a dated USPTO fee-correction page) and the four-sheet XLSX docket tracker." |

### Claims flagged, not changed (founder decision)

| Listing | Wording | Class |
|---|---|---|
| vkqogv | "Attorneys charge $1,000-2,500 ... $2,000-5,000" | UNKNOWN: no source on file; the USPTO fee figures in the same paragraph are correct (OBSERVED, uspto.gov) |
| fetmu | "One month of protected EU revenue dwarfs $79"; "consultant ... ~GBP 150-400/product" | persuasion; source UNKNOWN |
| dyjavs | "Built from WSJ/NAIC mechanics ... checked September 2026" | UNKNOWN, not re-verified |
| ciowwm, hasjmp | generic template bullets ("Checklists and prompts for the parts people usually get wrong") | INFERRED weak: the guides are 1 page |

## 5. Thin listings not covered by the repair (16)

Measured from byte-identical copies of the live files (OBSERVED) except where marked UNKNOWN. The
recommendation is a disclosed heuristic: regulated-compliance topics under ~420 words are UNPUBLISH
(incomplete regulatory guidance can harm a buyer); other short products REPRICE or EXPAND; known-risk
topics HOLD. No price or publication state was changed.

| Priority | Listing | Product | Price | Pages / words | Delivers | Recommended | Why |
|---|---|---|---|---|---|---|---|
| 1 | bfdgx | EU Cosmetics Responsible Person Guide | $69 | 2 / 415 | PDF | UNPUBLISH (or EXPAND) | regulated topic, $69 for 415 words |
| 2 | ldrdm | Food-Contact Materials Starter | $39 | 1 / 272 | PDF | UNPUBLISH | regulated topic, 1 page |
| 3 | eiebdt | Battery & WEEE Mini-Guide for Sellers | $29 | 1 / 258 | PDF | UNPUBLISH | regulated topic, 1 page |
| 4 | vyitxf | Toy Safety File Starter (EN 71 Lens) | $29 | 1 / 358 | PDF | UNPUBLISH | regulated product safety, 1 page |
| 5 | roxdbe | SaaS Churn Email Pack | $39 | 1 / 257 | PDF | REPRICE ($9) or EXPAND | 1 page at $39 |
| 6 | uwyfje | GCC Contractor Payment Command System | $49 | 3 / 846 | PDF | UNPUBLISH (superseded) | the separate "V2 Bundle" listing (jlxmez) sells the fuller version |
| 7 | fwrjot | Freelancer Payment Protection & Scope-Control Toolkit | $49 | 3 / 792 | PDF | REPRICE ($19) or EXPAND | short for the price |
| 8 | zfnagp | Suspended Seller First-Appeal POA System | $39 | 2 / 618 | PDF | REPRICE ($19) or EXPAND | short for the price |
| 9 | yhnyn | Digital-Product Refund Policy Pack | $29 | 1 / 254 | PDF | REPRICE ($9) | template content, 1 page |
| 10 | zjwpx | Freelancer Scope-Creep Contract Kit | $29 | 1 / 253 | PDF | REPRICE ($9) or HOLD | contract wording, 1 page |
| 11 | fccqk | Gulf Job-Landing ATS CV System | $29 | 2 / 556 | PDF | REPRICE ($12-15) | short for the price |
| 12 | palmdr | ADA Demand-Letter Response & Triage Kit | $69 | 3 / 1,244 | PDF | HOLD | legal topic; a local revision was rolled back on 2026-10-22; needs review before any change |
| 13 | engiwk | EU AI Act Compliance Quickstart Checklist | $19 | 2 / 312 | PDF | HOLD | a sibling EU AI Act listing is on hold for invented wording; accuracy unreviewed |
| 14 | edgiq | UK Deposit Recovery Action Pack | $29 | ZIP: workbook + guide PDF | ZIP | HOLD (review) | delivers both files; the thin flag likely comes from the size heuristic |
| 15 | blayvb | Freelancer Rate & Raise Calculator | $14.99 | UNKNOWN | XLSX | HOLD | no byte-identical local copy |
| 16 | tmhlb | EU AI Act Transparency & AI Literacy Quickstart | $9 | 2 / 309 | PDF | KEEP | price matches the size |

## 6. Tests and dry runs (OBSERVED)

- `tests/test_apply_listing_repairs.py` 3/3 (first run plans; second run after success writes nothing;
  a failed bundle is never uploaded); `tests/test_platform_write_gate.py` + `tests/test_no_temp_dependencies.py` 14/14.
- Two consecutive dry runs produced identical plans, including identical bundle sha256 values (deterministic).
- Final dry run: 5 bundles PLANNED (0 already applied), 32 description edits PLANNED, every bundle member file test PASS.

## 7. Remaining risks

- The live run makes 37 changes on the only sales channel; each is verified by re-read inside the publisher,
  and a failure is reported per listing without stopping the others.
- Gumroad attach verification compares sizes only (OBSERVED in `update_product_file`).
- The workbooks were not opened in Excel itself (UNKNOWN: visual rendering).
- Why the local `books/` PDFs and the live PDFs differ in bytes is UNKNOWN; the bundles use the live bytes.

## 8. Decision

| Repair | Decision |
|---|---|
| 5 file repairs | PASS |
| 32 description edits | PASS |
| 16 thin listings | HOLD: founder decision per row; nothing changes automatically |

Live command, to run only with explicit founder authorization:
`python scripts/apply_listing_repairs_20261029.py --live`
