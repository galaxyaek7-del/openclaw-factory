# Operational Learning Baseline

Cycle 102, 2026-10-19. This is the consolidated operational record for the
current product batch (batch 12): where each product actually stands, how that
was established, what the money situation really is, and what lessons are now
guarded by permanent checks.

Method: every statement below is reconstructed from real records on disk —
gate records, live-verification captures, publish evidence, the sales ledger,
the batch registry, and direct HTTP reads of public pages. Nothing here is
copied from a narrative report or from an earlier summary. Each claim carries a
label:

- `OBSERVED` — a real record, command output, or live page.
- `DERIVED` — computed by a documented rule from observed inputs.
- `INFERRED` — a reasonable conclusion from indirect evidence.
- `UNKNOWN` — no evidence exists.

Machine-readable companion: `data/operational_history.json` (and the append-only
`data/operational_history.jsonl`). Regenerate with
`python operational_history.py --write --check`.

## 1. Pricing record correction

The Cycle 100 build report (`reports/CYCLE100_B12-010_BUILD_2026-10-19.md`) was
constructed from a summary that said the $15.00 and $39.00 prices had both been
withdrawn. That is wrong, and the authoritative records already record it
correctly:

- **$15.00 is the winning price for B12-010.** It is the highest price that
  passes every mandatory gate. It was never withdrawn.
  `reports/B12-010/GATE_FINAL_2026-10-19.json` `price_history` records it as
  `APPROVED`; `reports/B12-010/RELEASE_BASELINE_2026-10-19.json` records
  `usd: 15.0` (`DERIVED`, pending founder listing authorization).
- **Only $39.00 was withdrawn.** It was the manifest placeholder and is recorded
  as `REJECTED - no comparable sustains $39 and the page policy caps at $15.00`.
- The apparent conflict between "the $15.00 gate" and "$19.97 market evidence"
  is not a policy conflict. The binding constraint is the page policy:
  `min($1.00 x pages, $15.00)` on a 17-page guide. $17.99 and $19.97 fail only
  that ceiling (`OBSERVED`, `candidates_tested` in `RELEASE_BASELINE`).
- Net proceeds at $15.00 are $13.50 against a $2.50 floor (`OBSERVED`).

The Cycle 101 verification report already corrected this
(`reports/CYCLE101_B12-010_VERIFICATION_2026-10-19.md`, section 6). No record
needed changing this cycle; the correction is restated here and cross-referenced
from the release baseline so the wrong version cannot re-enter circulation.

## 2. Money

- Verified revenue: **$0.00** (`OBSERVED`).
- `data/sales_ledger.jsonl`: 135 rows, **all** `event_type: publish_attempt`,
  maximum amount 0. No sale event exists in any recorded ledger (`OBSERVED`).
- `finance_data.json`: `sales: []`, all channel totals 0 (`OBSERVED`).
- `config/reality.json`: `published_books: []` (`OBSERVED`). Its schema counts
  only products with a real Amazon ASIN, so it does not see Gumroad listings at
  all (see section 5).

## 3. Batch-12 state reconstruction

Source: `data/operational_history.json`, generated from the records named in the
evidence column. "Next" is the first milestone that is not yet verified.

| Product | Price (registry) | Highest verified | Next required | Verified count | Strongest evidence |
|---|---|---|---|---|---|
| B12-001 | $14.99 | `CHECKOUT_VERIFIED` | `FIRST_SALE_VERIFIED` | 6 | `data/cycle94_live_verification.json` |
| B12-002 | $11.99 | `READY_FOR_AUTHORIZATION` | `UPLOAD_COMPLETED` | 3 | `reports/B12-002/GATE_FINAL_2026-10-18.json` |
| B12-003 | $8.00 | `CHECKOUT_VERIFIED` | `FIRST_SALE_VERIFIED` | 6 | `data/cycle99_b12_003_live_verification.json` |
| B12-004 | $11.99 | `CHECKOUT_VERIFIED` | `FIRST_SALE_VERIFIED` | 6 | `data/cycle98_b12_004_live_verification.json` |
| B12-005 | $8.00 | `READY_FOR_AUTHORIZATION` | `UPLOAD_COMPLETED` | 3 | `reports/B12-005/GATE_FINAL_2026-10-19.json` |
| B12-006 | $29.00 | `BUILD_COMPLETE` | `QA_PASS` | 1 | `books/batch12` |
| B12-007 | $19.00 | `BUILD_COMPLETE` | `QA_PASS` | 1 | `books/batch12` |
| B12-008 | $29.00 | `BUILD_COMPLETE` | `QA_PASS` | 1 | `books/batch12` |
| B12-009 | $19.00 | `BUILD_COMPLETE` | `QA_PASS` | 1 | `books/batch12` |
| B12-010 | $15.00 | `READY_FOR_AUTHORIZATION` | `UPLOAD_COMPLETED` | 3 | `reports/B12-010/GATE_FINAL_2026-10-19.json` |

Summary: 3 products at `CHECKOUT_VERIFIED`, 3 at `READY_FOR_AUTHORIZATION`,
4 at `BUILD_COMPLETE`, 0 at `FIRST_SALE_VERIFIED` (`DERIVED`).

Labels behind the stronger claims:

- B12-001/003/004 `CHECKOUT_VERIFIED` is `DERIVED` from live-verification
  captures that recorded a published listing, an HTTP 200 with the served
  product title, and a checkout URL at the intended price. B12-001 additionally
  has `PUBLIC_LISTING_VERIFIED` as `OBSERVED` because its capture compares the
  served file's SHA-256 against the canonical artifact (`cycle94_live_verification.json`
  records the served file as identical).
- B12-004 `READY_FOR_AUTHORIZATION` is `INFERRED` — its readiness is read from a
  live-verification capture; no standalone authorization-preparation record was
  found for it.
- B12-006 through B12-009 have **no** `reports/<id>/` gate record at all, so
  their `QA_PASS` is honestly not verified. They are `BUILD_COMPLETE` only.
- B12-002's gate verdict is nested under `gate_at_recommended_price_11_99`
  (`APPROVED`); the file has no top-level verdict. A naive reader would see
  "no verdict".

Nothing in the batch is published for the first time this cycle, and no
authorization phrase has been issued for B12-010. `FACTORY_LIVE_PUBLISH` remains
`false`.

## 4. What the states do not prove

- `CHECKOUT_VERIFIED` proves a checkout page was reachable. It does not prove
  anyone bought anything. All three published products had zero recorded sales
  at their last check (`OBSERVED`).
- The batch registry `data/product_batch_12.json` lists **all ten** products as
  `READY_FOR_REVIEW`, including products that are live and checkout-verified.
  The registry is stale and must not be used as the state source (`OBSERVED`;
  this is defect class L3 below).
- `FIRST_SALE_VERIFIED` is not verified for any product, and there is no
  evidence anywhere that a first external sale has occurred.

## 5. New operational finding — the store already has live listings

Previously undocumented, and material to the revenue picture:

- `data/sales_ledger.jsonl` contains **50 distinct successful, non-dry-run
  Gumroad publish attempts on the `aekraft.gumroad.com` store between
  2026-09-20 and 2026-09-28**, each with its own live product URL and a real
  product title (for example `GPSR EU Seller Action Kit`, `Turo Guest Dispute
  Toolkit`, `Restaurant Health Inspection Readiness Kit`, `FTC Consumer Review
  Rule Compliance Kit`) (`OBSERVED`, ledger).
- Liveness spot-checked by direct HTTP read this cycle:
  `https://aekraft.gumroad.com/l/blayvb` served `Freelancer Rate & Raise
  Calculator` (B12-001) and `https://aekraft.gumroad.com/l/fetmu` served
  `GPSR EU Seller Action Kit`, `https://aekraft.gumroad.com/l/adyvd` served
  `Turo Guest Dispute Toolkit` (`OBSERVED`). The remaining older listings are
  `INFERRED` live on the strength of the successful publish records; they were
  not all re-fetched.
- Those listings sit on the same store as this batch's published products and
  have produced **zero** recorded sales, so the first-sale blocker is a demand
  problem, not only an authorization problem.
- `config/reality.json` reports zero published books because it counts only
  Amazon ASINs — a deliberate, documented KDP-only schema, not the whole store
  (`OBSERVED`, the file's own `_published_note`). The operational record should
  stop implying "nothing has ever been published anywhere": 50 Gumroad listings
  were published and are still live.
- The ledger also records 17 real (non-dry-run) publish attempts that failed,
  the most recent on 2026-10-03 with `HTTP 402 credits depleted` from the X
  platform (`OBSERVED`). Those are failures to publish, not live products.

## 6. Recurring defect classes and their permanent guards

Each class below has actually occurred in this batch. Each now has a standing
check rather than a promise to be careful.

**L1 — Excel displays a value that hides a defect.** Cycle 101: seven number
formats were attached to the wrong cells, so Excel showed `100%` for a count,
`$1` for an award rate, `3000000%` for a currency total, the serial `1` as
`1900-01-01` for a date, and the serial `46328` for a live date. Value-only
tests passed throughout.
*Guard:* `native_workbook_qa.py` recalculates with real Excel and checks
display against number kind; 17 tests in `tests/test_native_workbook_qa.py`
reintroduce each defect and assert it is caught; `scripts/check_b12_integrity.py`
fails if the workbook changes without a matching recorded `PASS`.

**L2 — Generated records contain copy-paste identity errors.** In
`data/first_sale_tasks_b12-004.json`, the B12-004 publish task is titled
`Publish B12-001 (requires founder phrase)` while its result is B12-004's
(`url https://aekraft.gumroad.com/l/ieashv`, `published: true`,
`externally_verified: true`). Task titles are not parameterized by product.
*Guard:* `operational_history.py` derives identity from the result payload and
never from a task title; the defect is recorded here so a title is never again
trusted as the state source. `UNKNOWN` whether other task files repeat it
(not audited this cycle).

**L3 — The registry drifts from reality.** `data/product_batch_12.json` says
`READY_FOR_REVIEW` for all ten products, including three that are live and
checkout-verified. Any report that reads the registry alone will be wrong.
*Guard:* release state comes from evidence, not the registry;
`operational_history.py --check` fails its invariants (verified-without-evidence,
verified-but-labelled-UNKNOWN, milestone order, first-sale-without-listing) and
`scripts/check_b12_integrity.py` cross-checks registry/prep consistency.

**L4 — Evidence shapes differ between products and cycles.** Three different
live-verification shapes exist (`api_readback`+`public_page` for B12-001,
`live`+`checkout` for B12-004, `facts.product`+`facts` for B12-003), and gate
verdicts are sometimes nested under `gate_at_*` keys. A parser written for one
product silently reads nothing for another and reports a false "not verified".
*Guard:* `operational_history.py` normalizes all known shapes explicitly and
supports the `QA_FACTS_*.json` fallback glob, and its invariants fire when
evidence is present but unparsed.

**L5 — Verification coverage is narrower than it sounds.** The workbook has 427
formulas; the native probe recalculated 148 on the sheets it scans. "Recalculated
by Excel" is true and is not the same as "all 427 formulas verified".
*Guard:* coverage counts are recorded in the evidence file and stated in the
playbook; the probe reports what it actually touched.

**L6 — "Withdrawn" without naming the price.** Cycle 100 claimed two prices were
withdrawn when only one was. A superseded or rejected candidate is not a
withdrawn final price.
*Guard:* `price_history` and `RELEASE_BASELINE` now name each price and its
status explicitly, and `RELEASE_BASELINE.price.history_note` states the
correction inline.

## 7. Reusable capability added this cycle

`native_workbook_qa.py` + `scripts/excel_recalc_probe.ps1` turn the one-off
Cycle 101 Excel investigation into a repeatable step: recalculate a workbook in
real Excel against a temporary read-only copy, record every cell's text,
value, and format, and fail the QA gate on any error cell, format/value
mismatch, missing expected label, or artifact-hash mismatch. Current result for
B12-010:

```
B12-010: PASS (0 critical, 0 warning) on Microsoft Excel 16.0 build 19127
```

recorded at `reports/B12-010/WORKBOOK_QA_2026-10-19.json` with the artifact hash
`df49cecaf704cb06dec3b48c9f826c94cfdae9e2bf91d3a2b76fc670593b8574`.

Honest limitation: this environment has no `pywin32` and no LibreOffice, so
Excel via COM is the only available native engine. On a machine without Excel
the check exits with an explicit "engine unavailable" result rather than
substituting a Python-only calculation.

Procedure documentation: `PRODUCTION_TO_PUBLISHING_PLAYBOOK.md` (new, canonical;
supersedes `PUBLICATION_CHECKLIST.md` and `LAUNCH_CHECKLIST.md` for the
procedure itself).

## 8. Open unknowns

- Full repository test suite: not run (>50 minutes, known pre-existing failures
  unrelated to this batch). No claim is made about it.
- Google Sheets import of the B12-010 workbook per version: untested; disclosed
  to buyers.
- Other spreadsheet editors (Numbers, LibreOffice): unavailable.
- B12-006 – B12-009 quality gates: no gate records exist; their QA state is
  `UNKNOWN`.
- The 50 older Gumroad listings: titles and URLs are observed; confirmation that
  each is still individually live is `INFERRED`, not fully re-fetched.
- Whether other generated task files repeat the L2 title defect: not audited.
- B12-010 founder listing authorization: not issued, so none is recorded.
