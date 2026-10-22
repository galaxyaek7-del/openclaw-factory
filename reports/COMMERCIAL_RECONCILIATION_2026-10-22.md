# Commercial reconciliation — catalog, ledger, gate, distribution (2026-10-22)

Verified revenue: **$0**. Nothing was published, edited, uploaded or recorded in any founder-owned ledger.

## 1. Catalog vs. platform vs. site vs. ledger

| Source | Count | Basis |
|---|---|---|
| Gumroad account (`GET /v2/products`) | **82** products: **79 published**, 3 unpublished | OBSERVED, API |
| Gumroad sales (`GET /v2/sales`, product `sales_count`) | **0** sales, $0 | OBSERVED, API |
| Distinct Gumroad slugs linked anywhere in `customer_site/` | 74; every one resolves to a published product | OBSERVED |
| Published but linked nowhere on the site | 5: `ieashv`, `owtmpe`, `wteork`, `vhofn`, `iaiyt` | OBSERVED |
| `data/catalog.json` (synced 2026-10-19) | 83 rows: 12 reviewed (KEEP), 71 UNREVIEWED | OBSERVED |
| `data/commercial_reality.json` | `highest_verified_index = -1`; no state verified | OBSERVED |
| `config/reality.json` | `published_books: []`, `scale_level 0`, `commercial_proof UNKNOWN` | OBSERVED |

**Discrepancies:**

- **D1. Duplicate listing.** "The 5-Minute Context Reset Playbook" is published twice: `akxaae` and `vhofn`, both at $15, with 9- and 10-page PDFs.
- **D2. Published with no deliverable.** `owtmpe`, "[Unavailable] AI Workflow QA & Stress Test", is published at $0 with no file. Anyone can "buy" it and receive nothing.
- **D3. Unpublished test product still on the account.** `dxfwlu`, "GALAXY FORGE API TEST — DO NOT BUY — DELETE ME".
- **D4. The local catalog is wrong about attachments.** It records them as "UNKNOWN (API exposes attachment size only)". `GET /v2/products/:id` actually returns each file's type, which is what made the delivery audit below possible.
- **D5. The ledger records nothing although 79 listings are live** (a sampled page returns HTTP 200). Root cause in §2.

## 2. The production gate

**Enforcement points (OBSERVED).** Both are in `server.js` (≈4652 and ≈4909) and both read the same two files:

| Route | Blocks when | Effect |
|---|---|---|
| `POST /generate-book` (create) | `reality.json` has `scale_level=0` and `commercial_proof=UNKNOWN`, or `commercial_reality.highest_verified_index < 1` | Blocks product creation through the HTTP route |
| `POST /api/distribute` (distribute) | `hard_stop`, or `highest_verified_index < 1` | Blocks distribution, **including dry runs**: the gate runs before `dry_run` is considered |

**Root cause of the ledger never moving (OBSERVED).**

- `commercial_reality.update_evidence()` and every `verify_*()` function have no caller anywhere in the code; only tests call them.
- The states are strictly sequential, and the first is SIGNAL_RECEIVED ("Founder signal received").
- So no path in the system can ever raise `highest_verified_index` above -1. The gate is permanently shut by construction, not by evidence.

**What it actually blocked (OBSERVED).**

- The automated loop never reached `/generate-book` in the recent log: 2,137 `hunt` ticks report "the latest qualified niche already has a book".
- `factory_loop.log` contains 0 gate rejections.
- The 79 live listings were created through scripts that call `channels/gumroad_publisher.py` directly, outside the gated routes. The gate therefore did not stop catalog growth; it only made the ledger diverge from reality.

**Narrowest correction (proposal only; not applied):**

1. **Founder action.** Record the facts already verifiable from the API through `commercial_reality.update_evidence(SIGNAL_RECEIVED=True, PUBLISH_STATE_VERIFIED=True, PUBLIC_PAGE_VERIFIED=True, …_evidence=…)`, with the API snapshot and HTTP 200 checks as evidence. Do not touch any transaction, payment or delivery state. This makes the ledger true. It also opens `/generate-book`, which is why it is the founder's call.
2. **Optional, code.** Let `/api/distribute` skip the commercial-reality gate when `dry_run` is true. A dry run has no external effect, and `channels/publish_protection.py` already exempts dry runs. Live publishing stays gated by `FACTORY_LIVE_PUBLISH=false` and the founder gates.
3. **Recommendation.** Leave the first-dollar doctrine unchanged. The evidence does not support "more products": 78 paid listings and 0 sales.

## 3. Delivery quality audit (OBSERVED, `scripts/gumroad_delivery_audit.py`, read-only)

Full rows: `reports/GUMROAD_DELIVERY_AUDIT_2026-10-22.json`.

| Issue | Count | Products |
|---|---|---|
| THIN_DELIVERABLE: paid, all files under 10 KB | 22 (incl. 1 unpublished test) | e.g. `wteork` FBA "Workbook" $49 = one 3.7 KB PDF; `zfnagp` "POA System" $39 = 2 pages / 618 words; `bfdgx` EU Cosmetics RP Guide $69 = 4.6 KB |
| PROMISES_SPREADSHEET_NOT_ATTACHED | 3 | `vkqogv` Trademark kit ("four-sheet docket tracker"; `books/trademark_filing_tracker.xlsx` exists locally); `wteork`; `drtaj` (unpublished) |
| PROMISES_MORE_FILES_THAN_ATTACHED | 1 | `fetmu` GPSR: "PDF guide + PDF cost planner", but only the guide is attached. Its chapter 7 points to a "companion .xlsx" (`books/gpsr_eu_seller_cost_planner.xlsx`) the buyer never receives |
| PUBLISHED_WITHOUT_DELIVERABLE | 1 | `owtmpe` (see D2) |
| PREVIEW_FILE_DELIVERED | 1 | `iaiyt` EU AI Act $155: buyers get the full v2 PDF (139,401 B, matches `books/eu_ai_act_compliance_toolkit_v2.pdf`) plus a "preview" PDF |
| ZIP_CONTENTS_UNVERIFIED | 9 | the API cannot show what is inside a ZIP |

**Correction to my own earlier step.** The list endpoint's `file_info` was empty for `iaiyt`, `ieashv` and `svlky`. The single-product endpoint shows 2 files each, so they are not undelivered.

Local measurements of the thin PDFs (pypdf): 30 local PDFs are under 10 KB; most are 1–2 pages and 135–618 words. Sizes are a proxy; page and word counts come from local copies, and live copies can differ slightly.

**Risk (INFERRED).** Selling 1–2-page PDFs at $29–$69, or a listing that promises a file it doesn't deliver, invites refunds and disputes, and risks platform action against the account. That account is the only live sales channel.

## 4. Distribution ranking for existing products

Criteria, in order:

1. Reviewed with quality PASS.
2. Market or problem evidence (catalog evidence level 1).
3. No delivery defect.
4. Deliverable substance.

The listed price is not a criterion. There is no traffic signal to rank by: the site has 31 recorded page views, mostly internal probes, and Telegraph pages have 142 gross views across 56 pages.

| Rank | Product | Price | Why it ranks here | Free channel fit (no ads) |
|---|---|---|---|---|
| 1 | EU AI Act Compliance Toolkit (`iaiyt`) | $155 | 31-page v2, sourced review, but delivers a stray preview file | Own-site SEO guide already exists; LinkedIn posts drafted in `customer_site/linkedin-eu-ai-act-post.md` (founder account) |
| 2 | FTC Consumer Review Rule Kit (`ekhza`) | $69 | Reviewed, evidence level 1, no defect | SEO article answering "FTC fake review rule small business" |
| 3 | Vendor Questionnaire Response Kit (`pyzqa`) | $89 | Reviewed, no defect, B2B pain (stalled deals) | SEO + answering questionnaire questions where SMB founders ask (no link-dropping) |
| 4 | EU Packaging EPR Action Kit (`gfsvu`) | $69 | Reviewed, no defect; dated regulation (PPWR Aug 2026) | Same audience as GPSR; one EU-seller guide can serve both |
| 5 | Turo Guest Dispute Toolkit (`adyvd`) | $29 | Reviewed, no defect, narrow time-boxed pain (48 h window) | High-intent search; existing landing page `customer_site/turo-guest-dispute-toolkit.html` |
| 6 | Restaurant Health Inspection Kit (`dvfvm`) | $49 | Reviewed, no defect | Local-business SEO |
| 7 | STR Direct Booking Revenue Kit (`ppsluq`) | $59 | Reviewed, no defect | Host communities that allow resources |
| Hold | GPSR (`fetmu`), Trademark (`vkqogv`) | — | Fix the missing spreadsheet first: the files exist locally, so attaching them is a founder-authorized Gumroad edit | — |
| Hold | Diminished Value (`dyjavs`), ADA (`palmdr`) | — | Thin (3 pages) for $59–69 | — |

Distribution guarantees no sales. No channel above has been used, and no engagement was generated.

## 5. Affiliate payout options (summary; details in `data/affiliate_algeria_evidence.json`)

| Option | Status |
|---|---|
| impact.com DZD wire | **CONDITIONAL**. Platform-level VERIFIED; account and program acceptance UNKNOWN; currency is irreversible at setup |
| Envato (impact.com) | CONDITIONAL payout; eligibility UNKNOWN; manual review |
| Shopify (impact.com) | Payout CONDITIONAL. Acceptance needs an established audience; **likely rejected today** (INFERRED) |
| Canva (impact.com) | UNKNOWN; program reported closed most of the time |
| PayPal-route programs (AWeber, n8n, Brevo, SiteGround, systeme.io) | CONDITIONAL (US bank or Visa required) |
| Stripe-only routes | BLOCKED (Stripe unavailable in Algeria) |
| Payoneer (Awin) | UNKNOWN |

## 6. Founder decisions this report creates

**Live Gumroad fixes.** Each is a live edit:

- attach the existing spreadsheets to GPSR and Trademark;
- remove the preview file from the EU AI Act deliverables;
- unpublish `owtmpe`;
- unpublish one duplicate Context Reset Playbook;
- delete the API test product.

**Thin products.** Expand, reprice or unpublish the ~20 thin paid products.

**Ledger truth (§2.1).** Record the API-verified publish and public-page states. This opens `/generate-book`.
