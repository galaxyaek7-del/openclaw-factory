# Cycle 101 — B12-010 verification, correction and release baseline

**Date:** 2026-10-19
**Product:** B12-010 Nonprofit Grant Pipeline Tracker
**Baseline commit at start:** `4e6a7c8f14a54f431c5af533c8fc31d01d2764fa` (= `origin/main` at the time of the check)
**Outcome:** the product is real and passes every mandatory gate at **$15.00**, but a
real Excel recalculation found seven wrong number formats — values right, displayed
text wrong. They are fixed, guarded by a test, and every dependent record was updated
with the new artifact hash. **Nothing was published.**

---

## 1. What this cycle set out to do, and what actually happened

The plan was six phases: baseline, verify the artifact, check pricing consistency,
prepare an authorization record, publish only with authorization, and verify the first
external transaction.

Phases 1–3 are complete. Phase 4 is prepared in the sense that the records exist and
are correct (`published: false`, `authorization_phrase: null`), and blocked in the
sense that no valid authorization exists. Phases 5–6 are **not executable** and were
not attempted.

The unexpected result is in Phase 2: the workbook *can* be recalculated natively in
this environment. Earlier work recorded "no spreadsheet engine installed" as a
limitation. That was wrong — **Excel 16.0 (build 19127) is installed** at
`C:\Program Files\Microsoft Office\Root\Office16\EXCEL.EXE`, and it runs through COM.

## 2. Phase 1 — Release baseline

| Item | Result |
|---|---|
| `origin/main` vs local `HEAD` | identical (`4e6a7c8…`), working branch in sync |
| Best available engine | Excel 16.0 build 19127 (LibreOffice absent; no Python formula engine) |
| Canonical artifact hashes | xlsx `def9f4c2…`, pdf `b7ad0849…`, png `c17de706…` |
| Gate record | `APPROVED` at $15.00, layers 100 / 100 / 70 |

Recorded in `reports/B12-010/RELEASE_BASELINE_2026-10-19.json`, with the gate
definitions written out in `reports/B12-010/GATE_METHOD_2026-10-19.md` so
"100/100/70" is not an unexplained number.

## 3. Phase 2 — Verifying the actual product

### 3.1 Native recalculation

A **temporary copy** of the canonical workbook was opened **read-only**, recalculated
with `CalculateFullRebuild()`, read cell by cell, closed without saving, and deleted.
The canonical file was never opened for write.

The formulas compute exactly what the guide says:

| Row | Computed | Expected |
|---|---|---|
| EX-001 (2027-03-15, Research) | 147 days / `OPEN` / duplicate flagged | same |
| EX-002 (2026-11-02, Drafting) | 14 days / `DUE IN 14 DAYS` | same |
| EX-003 (Awarded) | −110 / `CLOSED` / helper blank | same |
| EX-004 | duplicate of EX-001 | same |
| Docs ready | 3/6, 5/5, 0/0, 0/0 | same |
| Docs gap | MISSING, OK, OK, OK | same |
| Timeline annual 2027-01-31 | `OPEN` | same |
| Timeline quarterly 2026-12-15 / 90 | next due 2026-12-15, `OPEN` | same |
| Timeline with no first due | "Check first due and repeat days" / `CHECK INPUTS` | same |
| Dashboard | tracked 4, active 3, decisions 1, awarded $15,000, overdue 0, duplicates 2, row problems 0, docs missing 1, reports overdue 0, verdict "MERGE OR DELETE THE DUPLICATE ROWS" | same |

**Zero real error cells.** An earlier detector reported three, but they were header
cells whose literal text is `#`, on Stages/Eligibility/DocLibrary. The detector now
matches only real Excel error literals.

Coverage note, stated so it cannot be misread: the recalculation touched **148**
formula cells — `SpecialCells(xlCellTypeFormulas)` over Opportunities, Timeline and
Dashboard. The workbook contains **427** formulas in total; the rest live on
Docs/Budget/Stages/Eligibility/DocLibrary and are counted by openpyxl, not recalculated
here. The 148 figure is not evidence of full formula coverage.

### 3.2 The defect this found

Values were correct; the **number formats were applied one row out of step**, so Excel
displayed:

| Cell | Label | Showed | Now shows |
|---|---|---|---|
| Dashboard!B6 | Awarded (count) | `100%` | `1` |
| Dashboard!B7 | Award rate | `$1` | `100%` |
| Dashboard!B9 | Total requested (USD) | `3000000%` | `$30,000` |
| Dashboard!B10 | Awarded against requested | `1` | `50%` |
| Dashboard!B12 | Deadlines due within 14 days | `1900-01-01` | `1` |
| Dashboard!B13 | Next deadline (open rows only) | `46328` | `2026-11-02` |
| Opportunities!V2 | Open deadline (helper) | `46461` | `2027-03-15` |

This is exactly the class of defect a value-only Python re-derivation cannot catch: the
values agreed with the independent model, and the buyer would still have opened the
workbook and seen `3000000%` next to "Total requested".

**Root cause:** the format block in `scripts/build_batch12_xlsx.py::b12_010_grant_pipeline`
assigned formats by an earlier row ordering. `Opportunities!V` had a format declared in
the sheet builder but lost it when the formula was written afterwards.

**Fix:** explicit, label-aligned formats on all seven cells/columns, plus
`op[f"V{r}"].number_format = "yyyy-mm-dd"` inside the formula loop.
`test_number_formats_match_the_kind_of_number_they_show` now asserts every one, so a
future rebuild cannot silently reintroduce it.

### 3.3 Re-verification after the fix

Rebuilt, then recalculated again in Excel 16.0: **0 error cells**, every display
correct, every computed value unchanged. Evidence:
`reports/B12-010/NATIVE_RECALC_EXCEL_2026-10-19.json`.

New workbook hash: **`df49cecaf704cb06dec3b48c9f826c94cfdae9e2bf91d3a2b76fc670593b8574`**
(38,765 bytes; was `def9f4c2…` / 38,775 B). The PDF and cover are unchanged.

### 3.4 Everything updated with the new hash, together

- `reports/B12-010/MANIFEST_2026-10-19.json` (plus `rebuilt_at_utc`, `rebuild_reason`)
- `reports/B12-010/QA_FACTS_2026-10-19.json` (plus recorded formats and recalc result)
- `reports/phase8/B12_010_GUMROAD_LISTING_PACKAGE.md`
- `reports/CYCLE100_B12-010_BUILD_2026-10-19.md` (size/hash, limitation now annotated)
- `tests/test_b12_010_workbook.py` (expected hash + format assertions)

## 4. Phase 3 — Pricing consistency

Pricing is consistent and unchanged: **$15.00** is the highest candidate that passes
all three mandatory constraints (quality layers, economics, page-based market realism).
$17.99 and $19.97 fail market realism alone because 17 pages cap the price at $15.00.
$39.00 remains rejected; $15.00 was never withdrawn.

Full definitions and the candidate table: `reports/B12-010/GATE_METHOD_2026-10-19.md`.

## 5. Phase 4–6 — Publication and the first sale

| Item | Status | Reason |
|---|---|---|
| Product-specific founder authorization | **BLOCKED** | none exists; `authorization_phrase` is `null` |
| Live publishing credential in this environment | **BLOCKED** | no working Gumroad token here |
| Publish action | **NOT ATTEMPTED** | deliberately not executed without authorization |
| Externally verified sale | **BLOCKED** | nothing is published |

`data/product_batch_12.json` and the manifest both keep `published: false` and a null
listing URL. `FACTORY_LIVE_PUBLISH` was not changed.

## 6. Corrections to the supplied Cycle 100 report

The report provided at the start of this cycle contains four factual errors. They are
recorded here because a wrong record is worse than a missing one.

1. **"$15.00 and $39.00 were both withdrawn."** Wrong. **$15.00 is the winning price.**
   Only $39.00 was withdrawn.
2. **"A policy conflict: the gate prohibits above $15.00 while the market range extends
   to $19.97."** Not a conflict. The page-based ceiling is a **binding rule**; the
   market band simply extends above it. Two prices failed because of the rule, not
   because two policies contradicted each other.
3. **`scripts/generate_cover.cover.py`.** Wrong filename. The real, working generator is
   `scripts/generate_all_covers.py`; `scripts/generate_cover.py` is broken and unused.
4. **"The working tree is clean."** Not true. Hundreds of untracked files from parallel
   work exist. Only this product's scope is clean and committed.

## 7. Verification status, in the required vocabulary

| Area | Status |
|---|---|
| Artifact hashes match the manifest | **PASS** |
| Native Excel recalculation | **PASS** (0 error cells, 148 formula cells over 3 sheets) |
| Number formats | **PASS** (7 defects found and fixed; regression-tested) |
| Deadline and cadence rules | **PASS** (Excel and independent Python agree) |
| Brand DNA and Executive Safety checks | **PASS** |
| PDF integrity (17 pp, 8,198 words, 0 placeholders, 0 mojibake) | **PASS** |
| Cover spec (1280×720) | **PASS** |
| Companion page content and price | **PASS** |
| Registry agreement (`check_b12_integrity.py`) | **PASS** |
| Bounded regression (167 tests) | **PASS** |
| Full repository test suite | **UNKNOWN** — not run; over 50 minutes with known pre-existing failures |
| Google Sheets import | **UNKNOWN** — untested per version; disclosed to buyers |
| Other editors (Numbers, LibreOffice) | **UNKNOWN** — not available |
| Publication | **BLOCKED** — no authorization |
| First external sale | **BLOCKED** — nothing published |

## 8. What is true now

- There is one real, internally complete product at a defensible $15.00.
- Its workbook is now verified by a real spreadsheet engine, not only by a Python model.
- Its displayed numbers are correct, which they were not before this cycle.
- It has still never been published, and no external person has paid for it.
- Verified revenue remains **$0.00**.

## 9. What would change the next decision

- A founder authorization phrase for B12-010 unlocks publication (and only that).
- A working Gumroad credential in this environment is the second gate; both are needed.
- Any real sale would move the pricing question from "derived" to "evidenced" and would
  be the first real input the price has ever had.
