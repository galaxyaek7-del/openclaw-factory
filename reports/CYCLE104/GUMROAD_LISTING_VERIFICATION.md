# Cycle 104 — live Gumroad listing verification

Read-only. GET only. No purchase attempted. Price is in US cents.
**PURCHASABLE is UNKNOWN for every row** — it can only be proven by a
real checkout, which this factory is not permitted to perform.

| product | state | published | price | attachments | sales | page |
|---|---|---|---|---|---|---|
| B12-001 | PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS | True | 1499 | 1 | 0 | 200 |
| B12-003 | PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS | True | 800 | 2 | 0 | 200 |
| B12-004 | PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS | True | 1199 | 2 | 0 | 200 |
| EU-AI-ACT-TOOLKIT | PUBLICATION_MISMATCH | True | 15500 | 2 | 0 | 200 |
| B12-002 | NOT_PUBLISHED_AS_EXPECTED | None | None | 0 | None | None |
| B12-005 | NOT_PUBLISHED_AS_EXPECTED | None | None | 0 | None | None |
| B12-010 | NOT_PUBLISHED_AS_EXPECTED | None | None | 0 | None | None |

## Checks

### B12-001 — PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS
- [PASS] published is true: True
- [PASS] not deleted: False
- [PASS] price matches approved: 1499 (expected 1499)
- [PASS] title matches: Freelancer Rate & Raise Calculator
- [PASS] attachment matches local B12-001_freelancer_rate_raise_calculator.xlsx: xlsx, 8922 bytes present on the listing
- [PASS] no unexpected attachments: attachment set equals the promised set
- [REVIEW] attachment names not exposed by the API: file name is null on every attachment; matching used filetype+size only, so a same-type same-size substitution cannot be excluded by this check

### B12-003 — PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS
- [PASS] published is true: True
- [PASS] not deleted: False
- [PASS] price matches approved: 800 (expected 800)
- [PASS] title matches: Founder Access Continuity Organizer
- [PASS] attachment matches local B12-003_access_continuity_inventory.xlsx: xlsx, 13594 bytes present on the listing
- [PASS] attachment matches local B12-003_access_continuity_organizer.pdf: pdf, 19095 bytes present on the listing
- [PASS] no unexpected attachments: attachment set equals the promised set
- [REVIEW] attachment names not exposed by the API: file name is null on every attachment; matching used filetype+size only, so a same-type same-size substitution cannot be excluded by this check

### B12-004 — PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS
- [PASS] published is true: True
- [PASS] not deleted: False
- [PASS] price matches approved: 1199 (expected 1199)
- [PASS] title matches: Meeting Cost & ROI Calculator
- [PASS] attachment matches local B12-004_meeting_cost_roi_calculator.xlsx: xlsx, 12865 bytes present on the listing
- [PASS] attachment matches local B12-004_meeting_method_guide.pdf: pdf, 9639 bytes present on the listing
- [PASS] no unexpected attachments: attachment set equals the promised set
- [REVIEW] attachment names not exposed by the API: file name is null on every attachment; matching used filetype+size only, so a same-type same-size substitution cannot be excluded by this check

### EU-AI-ACT-TOOLKIT — PUBLICATION_MISMATCH
- [PASS] published is true: True
- [PASS] not deleted: False
- [PASS] price matches approved: 15500 (expected 15500)
- [PASS] title matches: EU AI Act Compliance Toolkit — Practical Templates & Implementation Guide for SMEs
- [FAIL] attachment matches local eu_ai_act_compliance_toolkit.pdf: no live attachment with filetype=pdf size=139121; live=[('pdf', 106314), ('pdf', 139401)]
- [REVIEW] extra attachment present: 2 unexpected attachment(s) beyond the promised deliverable set: [('pdf', 106314), ('pdf', 139401)]

### B12-002 — NOT_PUBLISHED_AS_EXPECTED
- [PASS] no listing exists (expected): title absent from the live catalog

### B12-005 — NOT_PUBLISHED_AS_EXPECTED
- [PASS] no listing exists (expected): title absent from the live catalog

### B12-010 — NOT_PUBLISHED_AS_EXPECTED
- [PASS] no listing exists (expected): title absent from the live catalog
