# CYCLE 95 — Re-upload reconciliation (13 repaired files)

**Date:** 2026-10-17 · **Manifest:** `reports/quality/REUPLOAD_MANIFEST_2026-10-17.json`
**Method:** read each replacement file and recompute its sha256/size/pages/format; read each
rollback original and recompute its sha256; classify each path with `git ls-files`/`git check-ignore`;
read the live Gumroad file size for each listing (read-only `GET /v2/products/:id`) and compare it to
the replacement size and the delivered-original (backup) size. Nothing was uploaded or changed.

All 13: replacement file exists, size and sha256 match the manifest, valid `%PDF`, page count
matches the manifest, and the rollback original exists with a matching sha256.

| # | Listing | Permalink | Replacement file | Size | sha256✓ | Pages | Location (git) | Rollback original ✓ | Live Gumroad size | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ADA Demand-Letter Response & Triage Kit | palmdr | `books/ada_demand_response_kit.pdf` | 30,154 | ✓ | 3 | ignored (local only) | ✓ | 9,588 | LOCAL ONLY — not uploaded |
| 2 | FTC Consumer Review Rule Compliance Kit | ekhza | `books/ftc_review_rule_compliance_kit.pdf` | 33,174 | ✓ | 5 | ignored (local only) | ✓ | 13,105 | LOCAL ONLY — not uploaded |
| 3 | Restaurant Health Inspection Readiness Kit | dvfvm | `books/restaurant_inspection_readiness_kit.pdf` | 30,594 | ✓ | 4 | ignored (local only) | ✓ | 10,850 | LOCAL ONLY — not uploaded |
| 4 | EU AI Act Audit Logging Kit | fwxmms | `books/eu_ai_act_audit_logging_kit.pdf` | 127,869 | ✓ | 14 | ignored (local only) | ✓ | 109,570 | LOCAL ONLY — not uploaded |
| 5 | Legal Case Research Automation (Solo Attorneys) | uldlwa | `books/_reupload_2026-10-17/legal_case_research_solo_kit.pdf` | 123,594 | ✓ | 16 | untracked (local only) | ✓ | 105,317 | LOCAL ONLY — not uploaded |
| 6 | SOC 2 Compliance Automation Guide for Startups | sjmbrp | `books/_reupload_2026-10-17/soc2_compliance_automation_kit.pdf` | 138,152 | ✓ | 18 | untracked (local only) | ✓ | 121,365 | LOCAL ONLY — not uploaded |
| 7 | AI Agent Blueprint for Small SaaS CloudOps | esnpki | `books/_reupload_2026-10-17/ai_agent_blueprint_cloudops.pdf` | 104,421 | ✓ | 9 | untracked (local only) | ✓ | 93,996 | LOCAL ONLY — not uploaded |
| 8 | Severance Agreement Review Checklist | vunrqm | `books/severance_agreement_review_kit.pdf` | 133,971 | ✓ | 15 | ignored (local only) | ✓ | 118,143 | LOCAL ONLY — not uploaded |
| 9 | Security Deposit Demand Kit for Tenants | yiqba | `books/security_deposit_demand_kit.pdf` | 130,079 | ✓ | 11 | ignored (local only) | ✓ | 115,393 | LOCAL ONLY — not uploaded |
| 10 | Mechanics Lien Filing Kit for Contractors | jibnyt | `books/mechanics_lien_filing_kit.pdf` | 140,613 | ✓ | 17 | ignored (local only) | ✓ | 126,790 | LOCAL ONLY — not uploaded |
| 11 | Stripe Chargeback Defense Kit for Digital Sellers | ceiwk | `books/stripe_chargeback_defense_kit.pdf` | 127,900 | ✓ | 15 | ignored (local only) | ✓ | 114,918 | LOCAL ONLY — not uploaded |
| 12 | CCPA Compliance Action Kit for Small Business | kaooj | `books/ccpa_compliance_action_kit.pdf` | 139,490 | ✓ | 13 | ignored (local only) | ✓ | 121,663 | LOCAL ONLY — not uploaded |
| 13 | Mindfulness Journal for Stress Relief | jvuelq | `books/mindfulness_journal_for_stress_relief.pdf` | 154,817 | ✓ | 18 | ignored (local only) | ✓ | 134,567 | LOCAL ONLY — not uploaded |

## Key result
For **every** listing the live Gumroad file size equals the **delivered-original** size (column 9) and
**not** the replacement size (column 5). Therefore none of the 13 repaired files is uploaded yet: the
repairs are **local only**, exactly as the manifest states, and the rollback originals still match what
customers currently receive.

**Manifest references the intended artifact:** yes — the 3 files the manifest lists under
`books/_reupload_2026-10-17/` are the ones produced by `pdf_glyph_repair.py` from the delivered bytes
(the other 10 are the in-place `fix_pdf_title_overlap.py` / glyph-repair builds already present under `books/`).

**Rollback path:** every original is preserved at
`backups/gumroad_delivered_2026-10-17/<permalink>__delivered.pdf` with its sha256 recorded in the manifest.
No external file was uploaded or replaced; nothing on Gumroad was changed.
