# Finding: git line-ending conversion was corrupting PDFs on disk (2026-10-22)

Fixed in commit `6dd2d4f` (`.gitattributes` + `tests/test_gitattributes_binary.py`).

## What happened

- **Cause.** This machine's system git config has `core.autocrlf=true`, and the
  repository had no `.gitattributes`. reportlab writes uncompressed PDFs, which
  git took for text, so every checkout inserted a CR before each LF *inside the
  PDF*.
- **Scope.** Six tracked PDFs on disk differed from their committed blobs:
  - `books/batch12/B12-003_access_continuity_organizer.pdf`
  - `books/batch12/B12-005_podcast_guest_scripts.pdf`
  - `books/batch12/B12-010_grant_pipeline_guide.pdf`
  - `books/inventory_management_wholesale.pdf`
  - `books/workflow_automation_logistics.pdf`
  - `demo_cookbook.pdf`
- **Proof.** For every file, removing the CR bytes reproduced the committed blob
  exactly. The committed bytes pass a strict `pypdf` parse. The on-disk copies
  failed it with `Broken xref table`.
- **Repair.** The six on-disk copies were rewritten from their committed blobs.
  The index is clean and no commit changed them. The damaged copies are kept
  outside the repository.

## Which hash is canonical

| File | Committed and canonical | Damaged on-disk variant |
|---|---|---|
| B12-003 guide | `c9c18a4b…` / 19,095 B | `115b480a…` / 19,314 B |
| B12-005 guide | `246268d4…` / 20,146 B | `a7b11fbc…` / 20,365 B |
| B12-010 guide | `b7ad0849…` / 45,453 B | `96468130…` / 45,838 B |

Every committed record already pins the canonical hash. That includes
`scripts/gumroad_draft_orchestrator.py`, the committed
`tests/test_b12_010_workbook.py`, and the committed
`reports/B12-010/MANIFEST_2026-10-19.json`.

## Action for the parallel session (not done here)

Several *uncommitted* edits re-pinned the **damaged** variants. They should be
reverted to the canonical values above, not committed:

- `tests/test_b12_010_workbook.py`: `EXPECTED` for the guide was changed from
  45,453 / `b7ad0849…` to 45,838 / `96468130…`. With the repaired file on disk,
  `test_files_exist_at_the_recorded_size_and_hash` now fails, which is correct:
  the pin is wrong, not the file.
- `reports/B12-010/MANIFEST_2026-10-19.json` (modified),
  `reports/CYCLE104/LISTING_PAYLOADS_B12.json` (modified),
  `reports/B12-010/QA_FACTS_2026-10-21.json` and
  `reports/B12-005/QA_FACTS_2026-10-22.json` (untracked) cite `96468130…` and/or
  `a7b11fbc…`.
- The 2026-10-21/22 "identity revalidation" for B12-005 and B12-010 was performed
  on CR-damaged bytes. Its content conclusions still hold, since extracted text is
  unchanged by the CRs. Its byte-identity conclusions do not.

These files belong to in-progress work in another session, so they were left
untouched rather than overwritten.

## Risk that remains UNKNOWN

Any product uploaded to a platform from this working tree before the fix may
have shipped a CR-damaged PDF. Most viewers silently repair a broken xref, so a
buyer may never notice, but the file is not the one that was built and QA'd.
Gumroad's API does not expose uploaded file hashes, so this cannot be checked
from here. A founder could download one live file and compare its SHA-256 with
the table above.
