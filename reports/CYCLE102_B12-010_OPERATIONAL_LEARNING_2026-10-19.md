# Cycle 102 — Operational Learning Integration and Release Integrity

2026-10-19. Verification report for Cycle 102. Companion machine-readable
evidence: `reports/B12-010/CYCLE102_FINAL_EVIDENCE_2026-10-19.json`.

Scope: independently verify the Cycle 101 correction, make native workbook
recalculation and number-format validation a reusable QA capability, protect it
with regression tests, correct the operational record, establish evidence-based
product states, and prepare B12-010 for an authorized launch without publishing.

## 1. Authority for B12-010

- Release commit: **`b2e2f34`** (Cycle 101), the current HEAD of `main`
  (`OBSERVED`).
- Canonical artifacts and their hashes:
  - workbook `books/batch12/B12-010_grant_pipeline_tracker.xlsx` — 38,765 B,
    sha256 `df49cecaf704cb06dec3b48c9f826c94cfdae9e2bf91d3a2b76fc670593b8574`
  - guide `books/batch12/B12-010_grant_pipeline_guide.pdf` — 45,453 B, 17 pages,
    sha256 `b7ad0849a7d248db821c79873a8cdc3c42399a6ce054083eaf650298e97f0a49`
  - cover `books/covers/B12-010.png` — 42,566 B, 1280x720,
    sha256 `c17de7066cbd9bf22affa138881fc67ed3d64e7598756277b807836eaaf122ec`
- Hash agreement between `MANIFEST_2026-10-19.json`, `RELEASE_BASELINE_2026-10-19.json`,
  and the files on disk re-checked this cycle (`OBSERVED`).

## 2. Independent verification of the Cycle 101 correction

The seven defects Cycle 101 claimed to fix were confirmed present in the
records and absent in the current workbook:

- `reports/B12-010/GATE_METHOD_2026-10-19.md` documents how the gate is
  composed; `NATIVE_RECALC_EXCEL_2026-10-19.json` records the original
  recalculation that exposed them; `RELEASE_BASELINE` and the Cycle 101
  verification report record the fix.
- The workbook was **re-opened in real Excel this cycle** (16.0 build 19127) via
  the new probe, on a temporary read-only copy, recalculated, and every cell's
  text/value/format inspected. Result: `PASS`, 0 critical, 0 warning, 0 error
  cells. Recorded at `reports/B12-010/WORKBOOK_QA_2026-10-19.json`.
- The value-visible outcomes are confirmed: Awarded count shows `1` (not
  `100%`), Award rate shows `100%` (not `$1`), Total requested shows `$30,000`
  (not `3000000%`), Awarded against requested shows `50%` (not `1`), Deadlines
  due within 14 days shows `1` (not a date), Next deadline shows `2026-11-02`
  (not `46328`), and `Opportunities!V` carries a date format (`OBSERVED`).
- The fix touched formats only. The workbook's formula count and the artifact
  hash are as recorded; no value or formula changed in this cycle.
- Coverage honesty: the workbook has **427** formulas; the probe recalculated
  **148** across `Opportunities`/`Timeline`/`Dashboard`. The 148 is not a claim
  of full verification, and is recorded as such.

No defect from Cycle 101 is reproducible in the current artifact.

## 3. Evidence-based product states

`operational_history.py` reconstructs each batch-12 product's release state from
real records with `OBSERVED`/`DERIVED`/`INFERRED`/`UNKNOWN` labels and validates
invariants. Current snapshot (`data/operational_history.json`):

- `CHECKOUT_VERIFIED`: B12-001, B12-003, B12-004
- `READY_FOR_AUTHORIZATION`: B12-002, B12-005, B12-010
- `BUILD_COMPLETE`: B12-006, B12-007, B12-008, B12-009
- `FIRST_SALE_VERIFIED`: **none** (verified revenue $0.00)

Each product carries the next required milestone and the exact evidence source
behind every verified milestone. The full reconstruction, the pricing
correction, the money picture, the newly-found live-listing fact, and the
recurring-defect lessons are in `reports/OPERATIONAL_LEARNING_BASELINE.md`.

Two honest gaps surfaced by the reconstruction:

- B12-006 – B12-009 have no gate records at all, so their `QA_PASS` is
  `UNKNOWN`, not assumed (`OBSERVED`).
- B12-004's readiness is `INFERRED`; it has no standalone preparation record.

## 4. Reusable workbook QA capability

`native_workbook_qa.py` + `scripts/excel_recalc_probe.ps1` generalize the Cycle
101 investigation:

- `scripts/excel_recalc_probe.ps1` opens a temporary read-only copy in real
  Excel, forces `CalculateFullRebuild()`, and dumps every non-empty cell's
  sheet, address, text, value, format, and formula, plus error cells, engine
  version, and artifact hash. It never writes the release file.
- `native_workbook_qa.py` holds a declarative per-product spec and a pure
  validator. It fails the check on: artifact-hash mismatch, any real Excel
  error cell, a missing expected label, a number format that contradicts what
  the cell shows, a percent/currency display that is broken, and a percent value
  without a percent format.
- If Excel is unavailable the check exits with an explicit "engine unavailable"
  result (exit 2) and **never** substitutes a Python-only calculation for a
  native one.

Integration into the existing workflow (rather than a side tool):

- `python native_workbook_qa.py --product B12-010 --write-evidence --json` is
  the standing QA step for any shipping workbook.
- `scripts/check_b12_integrity.py` now fails if a workbook with a registered
  spec has no recorded `PASS`, or if the recorded evidence's hash no longer
  matches the file about to ship. It reads the recorded evidence only — it never
  runs Excel — so the gate stays fast and deterministic.
- `reports/B12-010/MANIFEST_2026-10-19.json` now points at the QA evidence
  alongside the recalculation evidence.
- `PRODUCTION_TO_PUBLISHING_PLAYBOOK.md` documents it as a required stage; the
  two stale checklists point to the playbook.

## 5. Regression protection added

`tests/test_native_workbook_qa.py` — 17 tests, all passing:

- the clean recorded workbook shape passes;
- each of the seven Cycle 101 defects is reintroduced into a synthetic
  recalculation dump and asserted to fail the check, naming the right label;
- artifact-hash mismatch, formula error, missing expected label, and
  numeric-percent-without-percent-text are each caught;
- a text cell that happens to carry a date format is **not** flagged, and a
  header cell whose literal text is `#` is **not** treated as an Excel error
  (both were real false-positive sources during development);
- an unregistered product id is rejected;
- the spec's artifact hash equals both the manifest's hash and the hash of the
  file on disk, and every Cycle 101 defect label has an expectation.

The tests need no Excel installation: the decision logic is separated from the
Excel automation on purpose.

## 6. Corrections applied to the operational record

- `reports/B12-010/RELEASE_BASELINE_2026-10-19.json`: cycle advanced to 102,
  `release_commit: b2e2f34` recorded, a `price.history_note` added stating that
  only $39.00 was withdrawn and $15.00 was never withdrawn, and two verification
  rows added (native workbook QA; evidence-based release state). The
  verification matrix is now 17 rows.
- `reports/B12-010/MANIFEST_2026-10-19.json`: now references the workbook QA
  evidence.
- The pricing record itself needed no change: `GATE_FINAL_2026-10-19.json`
  already records $39.00 as `REJECTED` (the manifest placeholder) and $15.00 as
  `APPROVED`, and Cycle 101 had already corrected the "$15.00 was withdrawn"
  misstatement.

## 7. B12-010 publication readiness

Separated into prepared / authorized / platform access in
`reports/B12-010/PUBLICATION_READINESS_2026-10-19.md`. Summary: everything is
built, gated, priced (derived), and packaged; **nothing is authorized** (no
founder phrase, no price approval); **no live publishing credential** is
available in this environment, and `FACTORY_LIVE_PUBLISH` remains `false`.
Nothing was published this cycle.

## 8. Tests run and results

| Command | Result |
|---|---|
| `python -m pytest tests/test_native_workbook_qa.py -q` | 17 passed |
| `python -m pytest tests/test_native_workbook_qa.py tests/test_b12_010_workbook.py tests/test_first_sale_orchestrator.py tests/test_first_sale_monitor.py tests/test_first_sale_monitor_hardened.py tests/test_gumroad_truthful_gate.py -q` | 153 passed |
| same set plus `tests/test_b12_utm_links.py` | 164 passed |
| `python scripts/check_b12_integrity.py` | `OK (10 prep items, 5 baselines)`, exit 0 |
| `python operational_history.py --write --check` | `OK`, exit 0, 0 new transitions on re-run |
| `python native_workbook_qa.py --product B12-010 --json` | `PASS`, 0 critical, hash matches |

Not run: the full repository suite (>50 minutes, known pre-existing failures
unrelated to this batch). No claim is made about it.

`tests/test_b12_utm_links.py` belongs to a parallel track and is **not** part of
this change; it was included only for a broader regression signal.

## 9. Limitations and disclosures

- Excel via COM is the only native engine here (no `pywin32`, no LibreOffice).
  A machine without Excel cannot run the check and will report that honestly.
- Google Sheets import of the workbook is untested and is disclosed to buyers.
- The 50 older live Gumroad listings were confirmed live by spot-check, not
  exhaustively re-fetched.
- The L2 task-title defect (`data/first_sale_tasks_b12-004.json` titled
  `Publish B12-001`) was recorded, not fixed; whether other task files repeat it
  was not audited.
- No founder authorization for B12-010 exists and none was invented.

## 10. Blockers and next actions

Blockers (all founder-only or external):

1. B12-010 founder listing authorization phrase.
2. A working live publishing credential in this environment.
3. A real external buyer — the store already has 50 live listings and zero
   recorded sales, so demand, not just access, is the binding constraint.

Next actions if asked to continue:

1. Get B12-006 – B12-009 through real gates so their state stops being
   `UNKNOWN` (they have artifacts but no gate records).
2. Extend `native_workbook_qa.py` specs to the other shipping workbooks so the
   new gate covers more than one product.
3. Resolve the L3 registry drift (`data/product_batch_12.json`) so downstream
   reports cannot read `READY_FOR_REVIEW` for live products.
