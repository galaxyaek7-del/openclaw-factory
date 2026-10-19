# B12-005 Gumroad Listing Package (READY FOR AUTHORIZATION — 2026-10-19)

Cycle 99 (2026-10-19) build + evidence round. Price USD 8.00 **DERIVED** (highest price passing every mandatory gate), not founder-approved. **NOT LISTED** — no Gumroad listing exists for this product and none may be created without a separate, explicit, product-specific founder authorization. Evidence: `reports/B12-005/GATE_FINAL_2026-10-19.json`, `reports/B12-005/QA_FACTS_2026-10-19.json`.

## Product title
Podcast Guest Booking Kit

## Short description
A fit-first method for earning podcast guest spots: score a real list of shows, pitch in each host's own words with an angle you can prove, send exactly two follow-ups, and close cleanly. 5 scripts, a one-sheet and question-bank template, a 14-day starting plan, plus a 6-sheet tracker that computes the cadence. Instant download.

## Full description (paste verbatim from `drafts/b12_005_listing_copy.txt`)
Most guest pitches get ignored for the same three reasons: they are sent to a show that was never a fit, they open with a bio instead of a reason for the host's audience to care, and they get followed up until they read as spam. This kit fixes all three, without ever promising a booking.

Built for founders, freelancers, consultants and authors who want to be booked as podcast guests. The method is fit-first and deliberately capped: score a real list of shows, pitch in each host's own words with a specific angle you can prove, send exactly two follow-ups, then close the loop with dignity and move on. The workbook computes the follow-up dates so the cadence cannot drift, flags any third-touch attempt as spam risk, and tells you which of your angles actually earns replies.

Inside (2 files):
- Podcast Guest Tracker workbook (.xlsx, 6 sheets): Assets (the ten things that must exist before you send a single pitch, including three specific angles with their proof), Angles (two to five arguable claims with the proof you can cite, pitched count, replies and a computed reply rate per angle), Pipeline (one row per show - episode you actually heard, contact route, angle used, fit score 1-5, pitch date, auto-computed follow-up dates, status, a Cadence column that says WAITING / FOLLOW UP 1 / CLOSE THE LOOP / CLOSED, and your next action), FollowUps (log every touch; touch number above 2 is flagged as a spam risk), Metrics (shows on the list, pitches sent, replies, reply rate, bookings, booking rate, shows cut as poor fit, cadence overdue, spam risk, assets ready and best-performing angle, plus a plain-language read on whether your sample is even big enough to judge), and a README. Includes worked example rows.
- Podcast Guest Scripts guide (.pdf, 8 pages, 15 sections): what this kit is and is not, the fit-before-pitch principle, the three assets to build first, how to build a target list of 25 to 40 shows instead of 200, the six-signal fit test, the pitch script and why each line exists, the two capped follow-ups, the confirmation brief for after a yes, the thank-you and asset email, a one-sheet fill-in template, a question bank that makes a host want you back, the first 14 days if you are starting today, a weekly 45-minute ritual, a worked example, ten mistakes that get you ignored, and answers to the five objections that stop people starting.

New product from Galaxy Forge: no sales recorded yet, no reviews.

Requires: Excel, LibreOffice Calc (free), or Google Sheets (free upload) for the workbook; any PDF reader for the guide. Instant download after purchase. Support: reply to your Gumroad receipt email.

## Intended buyer
Founders, freelancers, consultants and authors who want to be booked as podcast guests. (Demand evidence is real and cited in `reports/B12-005/DEMAND_EVIDENCE_2026-10-19.json` and `data/evidence/b12_005_competitors.json` — 11 real priced comparables $5.03–$38.00 plus 4 shape-matched Gumroad listings whose prices were not readable (client-rendered pages), HIGH competition; "this specific buyer pays for THIS kit" is still unproven — no sales yet.)

## Deliverables (canonical, hashed)
- `books/batch12/B12-005_podcast_guest_scripts.pdf` — 20,146 B, sha256 `246268d4ba41c6099a1d78ddd74c10203106f6999d4908710178fbd1d749bb9e` (8 pages, 3,336 words, 15 sections)
- `books/batch12/B12-005_podcast_guest_tracker.xlsx` — 17,400 B, sha256 `0720869bd302ff7c49c03edae97722d22161061191650380fc9047913e124b14` (6 sheets, 154 formulas, 6 data validations)
(never silently replaced; rebuild only via `scripts/build_batch12_pdfs.py` / `scripts/build_batch12_xlsx.py::b12_005_guest_tracker` on a documented defect)

## Price
$8.00 USD one-time — **DERIVED (Cycle 99 pricing rule, 2026-10-19)**; `HIGHEST_PRICE_PASSING_ALL_MANDATORY_GATES`. Pending founder listing authorization; not a founder price approval.
11 real priced comparables ($5.03–$38.00; the closest single-download packs are $6–$19, the media-kit end is $18–$38). $8.00 is the **highest price that clears the mandatory market-realism policy** for an 8-page guide (`economics.market_realism_check(price, page_count=8)` permits at most `min($1.00 × 8, $15.00) = $8.00`); the manifest's $29.00 fails that gate. Gate: **APPROVED at $8.00** — core 100 / content 100 / market 70 (`reports/B12-005/GATE_FINAL_2026-10-19.json`); $9.00, $11.99, $14.99 and $19.00 are also APPROVED on the quality gate, but only $8.00 passes *both* gates.

## Tags
podcast, guest pitching, outreach, email templates, publicity, tracker, checklist, pr

## Cover
`reports/B12-005/cover.png` — 1280x720 PNG, title-only design on the theme colour (no price shown), verified non-blank (luma stddev 22.5), sha256 `6dbd963a193c1f91634c986cebcaf69335ab9dfb77f01ddeab579eaea17cec8a` (byte-identical to `books/covers/B12-005.png`). **NOT attached** — no listing exists.

## Pre-publication checklist
- [ ] Title pasted exactly
- [ ] Description pasted exactly (keeps the 0-sales disclosure; brand + content-safety checks PASS)
- [ ] Price set to the gate-passing $8.00 (pending founder authorization)
- [ ] Both files uploaded and read back at the canonical sizes
- [ ] Cover attached
- [ ] Preview confirmed
- [ ] STOP lifted: explicit B12-005 authorization given (NOT yet given — this page is not a publication record)

## Publication record
NONE. No listing created, modified or enabled. `FACTORY_LIVE_PUBLISH` was never set for this product; no write-gate authorization was requested. Publication requires a separate founder directive naming B12-005.

## Gate evidence
`reports/B12-005/GATE_FINAL_2026-10-19.json` — core_value 100, content_quality 100 PASS (3,336 words vs 800 required at $8.00; 6 sheets / 154 formulas / 6 data validations), market_reality 70 PASS at $8.00, REWRITE at the manifest's $29.00 (content depth). QA: `reports/B12-005/QA_FACTS_2026-10-19.json` (technical inspection PASS 6/6 using the batch-consistent PDF-only method; brand_dna PASS; the four Executive Safety checks PASS; the Pipeline cadence logic and the Metrics "read this honestly" logic re-derived independently across 9 boundary cases).

## Disclosed economics note
`economics.market_realism_check(8.00, page_count=8, platform='gumroad_digital')` returns `(True, 8.00)`; $9.00 and above return `(False, 8.00)`. The auto-distribution path (`distributor.py` → `schemas/product.py::from_jsonl_record()`) would silently re-price an 8-page `gumroad_digital` product to $8.00, so $8.00 is the only price at which the quality gate, the depth rule and the economics policy all agree. The founder-authorized first-sale path (`scripts/first_sale_orchestrator.py`) never repriced, so the page-count ceiling is a **policy choice, not a technical limit**: the comparable cluster would support a higher price, and raising it would require either a founder override of the page-count policy or a longer, genuinely useful guide (depth is not the constraint — 3,336 words supports ~$33 under the 100-words-per-dollar rule).

## Disclosed defect found and fixed this round
The workbook's Metrics sheet had two real bugs, caught by an independent Python re-derivation before any listing: (1) `B13` ("Assets status") tested `B11` — the spam-risk count — instead of `B12`, the assets-ready count, so it could read "ASSETS READY" while assets were still missing; (2) `B15` ("Read this honestly") compared the numeric assets-ready count to the string `"ASSETS READY"`, which is always true, so once a user passed 10 pitches the sheet would permanently report "Assets incomplete". Both fixed in `scripts/build_batch12_xlsx.py` and the workbook rebuilt; the re-derivation now matches the shipped formulas.
