# Spreadsheet Normalization — Service Package

## Scope
CSV/XLSX cleanup: headers, whitespace, dates→ISO, currency→numeric (US+EU),
SKU upper-strip, duplicate flagging, missing-value report. NOT: bookkeeping
judgment, tax/financial advice, database writes, credentialed systems.

## Intake
Buyer uploads CSV/XLSX + names date/currency/SKU columns (or accepts auto-guess + review).
Max 50k rows pilot.

## Workflow
INPUT → VALIDATION (parse check) → NORMALIZATION → QA report → FOUNDER REVIEW → DELIVERY (cleaned file + QA report).

## QA checklist
- [ ] row count reconciled (in = out + dupes)
- [ ] columns preserved/mapped (list shown)
- [ ] duplicates flagged with rule stated
- [ ] no silent loss (every drop counted)
- [ ] required fields present
- [ ] currency spot-check (EU + US formats)

## Pricing hypothesis
$79 flat pilot (measured: factory ~minutes incl. QA review; founder 15 min).
Tiers after evidence: Simple $49 / Standard $79 / Complex $149. UNVALIDATED.

## Limitations
No semantic fixes (misspelled products stay flagged, not corrected).
No financial advice. No PII retention after delivery.
