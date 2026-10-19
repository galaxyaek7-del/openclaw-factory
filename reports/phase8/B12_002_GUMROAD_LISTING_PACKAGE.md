# B12-002 Gumroad Listing Package (local prep — NOT published)

Cycle 98, 2026-10-18. Everything below is prepared and gated; **nothing is uploaded and the product is not published.**

## Product title
Client Project Handoff Pack

## Short description
Run the 45-minute handoff session, transfer the five asset categories with proof, and let the workbook compute a hard Close gate. 6-sheet register + 4-page method guide. Instant download.

## Full description (paste verbatim from `drafts/b12_002_listing_copy.txt`)
A project ends twice: once when you stop working, once when the client can prove they own it. This pack makes the second one happen on purpose. It is the 45-minute handoff session you run live, the three emails you copy and paste, the five asset categories nothing ships without, and a companion workbook that computes a hard Close gate so a project cannot be marked finished while the receiver is still blocked.

Built for freelancers, agencies and contractors handing work to a client or another team. The method is simple and stubborn: a handoff ends when the receiver can prove they own it, not when the sender stops working — so the register is filled in together, on the call, and every credential is reissued into an account the client owns rather than passed over as a password.

Inside (2 files):
- Client Project Handoff Register workbook (.xlsx, 6 sheets): HandoffRegister (one row per project — days to handoff, assets-complete %, open high risks, and a computed Close gate), ChecklistTemplate (18 canonical items across Code, Docs, Accounts, Money, Data, Security, People and Support, each with why it prevents a dispute), AssetChecklist (one row per item, with access transferred Y/N, who verified it, where it lives and a proof note), RiskRegister (Severity x Likelihood scoring — a score of 12 or more is HIGH and blocks the close gate), Dashboard (KPIs including projects ready to close), and a README. Includes worked example rows (a "DNS transfer fails" risk scores 4 x 3 = 12, so the gate stays OPEN until every asset reads Y, no high risk is open, and sign-off is Y).
- Client Project Handoff Guide (.pdf, 4 pages): the transfer-by-evidence principle, the ten-day prep list, the minute-by-minute 45-minute session script, the five asset categories, the access and security rules, three copy-paste emails, the acceptance criteria and close gate, the 14-day support window, the 30/60/90-day review, the failure modes this pack prevents, an FAQ, and a final pre-handoff checklist.

New product from Galaxy Forge: no sales recorded yet, no reviews.

Requires: Excel, LibreOffice Calc (free), or Google Sheets (free upload) for the workbook; any PDF reader for the guide. Instant download after purchase. Support: reply to your Gumroad receipt email.

## Intended buyer
Freelancers, agencies and contractors handing a finished project over to a client. (Demand evidence is real and cited in `reports/B12-002/DEMAND_EVIDENCE_2026-10-18.json` and `data/evidence/b12_002_competitors.json` — 12 real paid comparables, $3.49–$54.89, HIGH competition; "this specific buyer pays for THIS pack" is still unproven — no sales yet.)

## Deliverables (canonical, hashed)
- `books/batch12/B12-002_client_handoff_register.xlsx` — 15,941 B, sha256 `e733ea8e913899b53ebe9a69d3e273d4ed018f997e47f006bbe1263d90543fda`
- `books/batch12/B12-002_client_handoff_guide.pdf` — 11,360 B, sha256 `273e05c5d8720ebe61ab44b2a9a6a3ef9f07f4eea4c561283c3ef0dd79b80f07`
(never silently replaced; rebuild only via `scripts/build_batch12_xlsx.py::b12_002_handoff_register` / `scripts/build_batch12_pdfs.py` on a documented defect)

## Price
$11.99 USD one-time — **FOUNDER-APPROVED 2026-10-18.**
12 real paid comparables (highest $54.89; mode ~$15). The gate's `price_within_market` ceiling is high×1.10, so the manifest's earlier **$29.00 / prep's $39.00 is REWRITE** (content depth and market reality both fail at that price). Gate: **APPROVED at $11.99, REWRITE at $29.00** (`reports/B12-002/GATE_FINAL_2026-10-18.json`).

## Tags
handoff, freelancing, checklist, project management, client, contractor, template, risk

## Cover
`reports/B12-002/cover.png` — 1280x720 PNG, title-only design on the theme colour (no book-cover match found, no price shown), verified non-blank (luma stddev 28.0). Gumroad's API has no cover upload; uploading the cover is the founder's action.

## Pre-publication checklist
- [x] Title pasted exactly
- [x] Description pasted exactly (keeps the 0-sales disclosure; brand + content-safety checks PASS)
- [ ] Price confirmed by the founder ($11.99 recommended; $29.00/$39.00 fail the gate)
- [ ] Both files uploaded (verify byte counts after upload)
- [ ] Cover uploaded
- [ ] Preview confirmed
- [ ] STOP: publish only with an explicit B12-002 authorization phrase

## Gate evidence
`reports/B12-002/GATE_FINAL_2026-10-18.json` — core_value 100, content_quality 100 PASS (1,722 words vs 1,199 required; 6 sheets / 102 formulas), market_reality 70 PASS at $11.99. QA: `reports/B12-002/QA_2026-10-18.json` (technical inspection PASS; brand_dna PASS; the four Executive Safety checks PASS; close-gate boundary logic re-derived independently).
