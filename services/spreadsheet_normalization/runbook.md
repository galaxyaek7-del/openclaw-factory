# First-Customer Delivery Runbook — Spreadsheet Normalization

## 1. customer_intake
- Receive: CSV/XLSX + column roles + known issues (via Gumroad service listing post-purchase note, or founder-forwarded file).
- Reject: >50k rows, credentials/secrets present (scan_secrets), non-tabular formats.

## 2. file_validation
- Parse check; encoding repair (utf-8-sig, cp1252 fallback); empty-file reject.

## 3. privacy_check
- Run scan_secrets; quarantine on hit; process in Temp dir; delete source after delivery confirmation.

## 4. processing
- engine.normalize with buyer-confirmed column roles.

## 5. QA
- QA checklist (README): row reconciliation, column map, dupe rule, no silent loss, required fields, currency spot-check.

## 6. before_after_report
- input rows/cols, output rows/cols, dupes removed, missing flagged, transforms applied, elapsed.

## 7. founder_review
- 15-min checklist: spot-check 20 random rows, confirm QA report matches, confirm no secrets in output.

## 8. delivery
- Cleaned file + QA report via founder channel. Record delivery timestamp.

## 9. follow_up
- Day-7 template: "Did the file load cleanly? Anything mis-normalized?" Log outcome to memory.
