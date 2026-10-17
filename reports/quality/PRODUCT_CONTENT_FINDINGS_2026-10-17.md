# Product content audit: what customers actually receive (2026-10-17)

**Method:**
- All 76 published Gumroad listings were read (read-only API).
- For each, **the exact file Gumroad delivers** was read once (our own product file), its size checked against Gumroad's record, and then opened and measured: pages, words, blank or repeated pages, title topic, placeholders.
- Each delivered file was also run through the factory's file tester.
- **Script:** `scripts/product_content_audit.py`. **Full data:** `reports/quality/PRODUCT_CONTENT_AUDIT.json`.
- **Nothing on Gumroad was changed.**

## Summary
- **59 of 76 have real content** and no flags.
- **1 is EMPTY**, delivering nothing.
- **1 is FILLER**, mostly repeated pages.
- **15 are THIN** for their price; 2 of them promise a calculator or workbook that isn't in the file.
- **13 delivered files have visible defects.** A verified fixed file now exists locally for all 13.

## Empty or filler: unpublish recommended (founder action)
| Listing | What the buyer gets |
|---|---|
| [Unavailable] AI Workflow QA & Stress Test, https://aekraft.gumroad.com/l/owtmpe ($0) | **Nothing**: no file, no content block, no delivery link |
| The 5-Minute Context Reset Playbook, https://aekraft.gumroad.com/l/vhofn ($15) | Cover + **8 near-identical generic habit-tracker pages**; nothing on context resets. (The other copy, `akxaae`, is the real 9-page product.) |

## Visible defects in the delivered file: re-upload (founder action)
A verified replacement is listed for each in `reports/quality/REUPLOAD_MANIFEST_2026-10-17.json` (path, sha256; file tester PASS).

| Listing | Price | Defect a customer sees | Replacement file |
|---|---|---|---|
| ADA Demand-Letter Response & Triage Kit | $69 | title printed over subtitle (page 1) | `books/ada_demand_response_kit.pdf` |
| FTC Consumer Review Rule Compliance Kit | $69 | title printed over subtitle (page 1) | `books/ftc_review_rule_compliance_kit.pdf` |
| Restaurant Health Inspection Readiness Kit | $49 | title printed over subtitle (page 1) | `books/restaurant_inspection_readiness_kit.pdf` |
| EU AI Act Audit Logging Kit | $29 | black boxes (■) instead of hyphens | `books/eu_ai_act_audit_logging_kit.pdf` |
| Legal Case Research Automation for Solo Attorneys | $29 | black boxes (■) instead of hyphens | `books/_reupload_2026-10-17/legal_case_research_solo_kit.pdf` |
| SOC 2 Compliance Automation Guide for Startups | $29 | black boxes (■) instead of hyphens | `books/_reupload_2026-10-17/soc2_compliance_automation_kit.pdf` |
| AI Agent Blueprint for Small SaaS CloudOps Automation | $29 | black boxes (■) instead of hyphens | `books/_reupload_2026-10-17/ai_agent_blueprint_cloudops.pdf` |
| Severance Agreement Review Checklist | $29 | black boxes (■) instead of hyphens | `books/severance_agreement_review_kit.pdf` |
| Security Deposit Demand Kit for Tenants | $29 | black boxes (■) instead of hyphens | `books/security_deposit_demand_kit.pdf` |
| Mechanics Lien Filing Kit for Contractors | $29 | black boxes (■) instead of hyphens | `books/mechanics_lien_filing_kit.pdf` |
| Stripe Chargeback Defense Kit for Digital Sellers | $29 | black boxes (■) instead of hyphens | `books/stripe_chargeback_defense_kit.pdf` |
| CCPA Compliance Action Kit for Small Business | $29 | black boxes (■) instead of hyphens | `books/ccpa_compliance_action_kit.pdf` |
| Mindfulness Journal for Stress Relief | $7 | black boxes (■) instead of hyphens | `books/mindfulness_journal_for_stress_relief.pdf` |

## Thin for the price (founder decision: expand, reprice or unpublish)
Content is real and on-topic, but short: a single PDF of 1–2 pages.

| Listing | Price | Delivered | Words | Note |
|---|---|---|---|---|
| EU Cosmetics Responsible Person Guide | $69 | PDF, 2 pages | 426 |  |
| EU Late Payment Recovery Kit | $59 | PDF, 1 page | 406 |  |
| Amazon FBA Reconciliation Workbook | $49 | PDF, 1 page | 340 | **title promises a workbook; it is one page of guidance** |
| SaaS Churn Email Pack | $39 | PDF, 1 page | 268 |  |
| Food-Contact Materials Starter | $39 | PDF, 1 page | 282 |  |
| Etsy Ads ROI Playbook + Calculator | $39 | PDF, 1 page | 313 | **title promises a calculator; there is none** (one page, formula in prose) |
| Suspended Seller First-Appeal POA System | $39 | PDF, 2 pages | 587 |  |
| Digital-Product Refund Policy Pack | $29 | PDF, 1 page | 269 |  |
| Freelancer Scope-Creep Contract Kit | $29 | PDF, 1 page | 262 |  |
| Battery & WEEE Mini-Guide for Sellers | $29 | PDF, 1 page | 267 |  |
| Toy Safety File Starter (EN 71 Lens) | $29 | PDF, 1 page | 369 |  |
| UK Deposit Recovery Action Pack | $29 | ZIP, 5 units | 383 | includes a spreadsheet with 11 formulas (more useful than its word count suggests) |
| Gulf Job-Landing ATS CV System | $29 | PDF, 2 pages | 538 |  |
| EU AI Act Compliance Quickstart Checklist | $19 | PDF, 2 pages | 290 |  |
| EU AI Act Transparency & AI Literacy Quickstart Checklist | $9 | PDF, 2 pages | 285 |  |

## Limits of this audit
- **Thin threshold:** fewer than 600 words or under 80 words per page. It flags products for review; it doesn't judge their usefulness.
- **Accuracy:** the audit measures presence, structure and topic. It does not check whether the advice is correct.
- **Visual review:** the defects were confirmed by rendering. The black box in the CCPA kit ("Opt■Out") and the repaired hyphen in the Legal Case kit ("Client-Cost") were inspected visually.
