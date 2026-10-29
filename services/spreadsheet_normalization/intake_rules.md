# Buyer Intake Rules — Spreadsheet Service (v1)

## SAFE_INPUT
- CSV/XLSX only, max 50k rows. Buyer provides a file LINK (Drive/Dropbox), never pastes raw data into chat/comments.
- Required: column roles + known issues statement. Rejected: executables, >50k rows, password-protected files without prior agreement.

## SAFE_PROCESSING
- Local Temp dir only. No uploads to third parties. No cloud processing.

## TEMPORARY_STORAGE
- Source + output live only for the delivery window. No archives, no training reuse.

## QA
- Engine QA report mandatory: row reconciliation, column map, dupe rule, no-silent-loss, required fields, currency spot-check.

## DELIVERY
- Clean file + QA report via founder channel. Delivery timestamp logged.

## DELETION
- Temp dir removed after delivery confirmation. Verify removal, log result.
- Privacy scan (credential/secret patterns) runs BEFORE processing and AFTER (output must not leak inputs beyond data).

## FORBIDDEN
- Confidential files via Telegram/public repos/public forms.
- Retaining customer data for any secondary purpose.
