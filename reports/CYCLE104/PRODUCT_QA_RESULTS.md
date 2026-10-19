# Cycle 104 — batch 12 per-product QA results

Offline. $0. No product file was modified by this sweep.

| id | verdict | gate | CQ | depth (words/required) | formulas | tracked | structural |
|---|---|---|---|---|---|---|---|
| B12-001 | BLOCKED_MISSING_DATA | APPROVED | PASS | None/None | 10 | all | PASS |
| B12-002 | BLOCKED_MISSING_DATA | {'gate_at_recommended_price_11_99': 'APPROVED', 'gate_at_manifest_price_29_00': 'REWRITE'} | PASS | 1722/1199 | 102 | all | PASS |
| B12-003 | BLOCKED_MISSING_DATA | APPROVED at $8.00 | PASS | 3235/800 | 20 | all | PASS |
| B12-004 | BLOCKED_MISSING_DATA | APPROVED at $11.99; NOT_READY at the manifest's $19.00 | PASS | 1441/1199 | 111 | all | PASS |
| B12-005 | BLOCKED_MISSING_DATA | APPROVED at $8.00 | PASS | 3336/800 | 154 | all | PASS |
| B12-006 | BLOCKED_MISSING_DATA | ABSENT | FAIL | 254/2900 | 3 | partial/none | PASS |
| B12-007 | BLOCKED_MISSING_DATA | ABSENT | FAIL | 273/1900 | 10 | partial/none | PASS |
| B12-008 | BLOCKED_MISSING_DATA | ABSENT | FAIL | 273/2900 | 1 | partial/none | PASS |
| B12-009 | BLOCKED_MISSING_DATA | ABSENT | FAIL | 233/1900 | None | partial/none | PASS |
| B12-010 | BLOCKED_MISSING_DATA | APPROVED at $15.00 | PASS | 8324/1500 | 427 | all | PASS |

market_reality is MISSING_DATA on every row: this sweep passes no competitor prices and no payment evidence, so layer 3 cannot run here. That is a harness limitation, not a product verdict.
