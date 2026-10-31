# Thin paid listings: repair plan (2026-10-31)

Source: `reports/GUMROAD_DELIVERY_AUDIT_2026-10-31.json` (THIN_DELIVERABLE on a paid listing),
then each delivered file downloaded read-only and measured (pages, words, workbook sheets). The
files themselves are paid content and are not in this repository. Sales on every listing below: 0.

## Findings

| Listing | Price | Delivers (measured) | What the page says | Class |
|---|---|---|---|---|
| drtaj, Verified B2B Lead Lists | $99 | 1-page PDF (81 words): an info sheet for a done-for-you service | a 200-lead build in 6 days | Service, not a download. Unpublished: keep it that way |
| bfdgx, EU Cosmetics Responsible Person Guide | $69 | 2-page PDF (415 words) | generic template ("a single, focused file") | Generic page, high price |
| palmdr, ADA Demand-Letter Response & Triage Kit | $69 | 3-page PDF (1,244 words) | long list of sections | Component list, no size stated |
| uwyfje, GCC Contractor Payment Command System | $49 | 3-page PDF (846 words) | 13 components, size disclosed | Already honest |
| fwrjot, Freelancer Payment Protection & Scope-Control Toolkit | $49 | 3-page PDF (792 words) | 10 tools | Component list, no size stated |
| roxdbe, SaaS Churn Email Pack | $39 | 1-page PDF (257 words) | generic template | Generic page |
| ldrdm, Food-Contact Materials Starter | $39 | 1-page PDF (272 words) | generic template | Generic page |
| zfnagp, Suspended Seller First-Appeal POA System | $39 | 2-page PDF (618 words) | many components, size disclosed | Already honest |
| yhnyn, Digital-Product Refund Policy Pack | $29 | 1-page PDF (254 words) | generic template | Generic page |
| zjwpx, Freelancer Scope-Creep Contract Kit | $29 | 1-page PDF (253 words) | generic template | Generic page |
| eiebdt, Battery & WEEE Mini-Guide for Sellers | $29 | 1-page PDF (258 words) | generic template | Generic page |
| vyitxf, Toy Safety File Starter (EN 71 Lens) | $29 | 1-page PDF (358 words) | size disclosed | Already honest |
| edgiq, UK Deposit Recovery Action Pack | $29 | ZIP: 4-sheet workbook (2-8 rows each, 11 formulas) + 1-page PDF (249 words) | tracker, scorecard, deadlines, letters, filing guide | Component list, no size stated |
| fccqk, Gulf Job-Landing ATS CV System | $29 | 2-page PDF (556 words) | 8 components | Component list, no size stated |
| engiwk, EU AI Act Compliance Quickstart Checklist | $19 | 2-page PDF (312 words) | 7 sections; dates current (high-risk deferred to 2 Dec 2027) | Component list, no size stated |
| tmhlb, EU AI Act Transparency Quickstart | $9 | 2-page PDF (309 words) | size disclosed; dates current | Already honest |
| blayvb, Freelancer Rate & Raise Calculator | $14.99 | 4-sheet workbook, 10 formulas | a calculator | Fine (flagged only by file size) |

## Repairs

1. **Disclose what is delivered (ready, needs your approval).** The eleven "component list" and
   "generic page" listings get the line the honest four already carry, with page and word counts
   measured from the live file:
   `python scripts/apply_thin_listing_disclosures_20261031.py` (dry run, report in
   `data/thin_listing_disclosures_20261031.json`), then `--live`. Description only: no price,
   file or title changes. This removes the risk that a buyer pays $29-69 expecting a kit.
2. **Price (your decision, per listing).** A 1-page, ~250-word reference at $29-39 is priced like
   our 15-page workbooks. The honest-four precedent sells condensed references at $9-49. A
   consistent rule would be: 1 page $9, 2-3 pages $15-19, unless the content is expanded.
3. **Expand (later, only where demand appears).** No listing here has a sale or a recorded visit,
   so expanding content now is effort without evidence. The trigger to expand one: a sale, a
   refund request, or an inquiry about it.
4. **drtaj** stays unpublished; if the service is offered, it belongs on a service page with the
   e-mail intake (micro-B2B arm), not as a $99 download.
