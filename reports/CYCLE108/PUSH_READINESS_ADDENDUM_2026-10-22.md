# Push-Readiness Addendum - 2026-10-22

This addendum records a blocker found while auditing the three parallel
commits that landed during Cycle 108. It does not change any code or history.

## State

- HEAD `3d2e8e4`; `main...origin/main [ahead 21]`, 0 behind.
- Nothing was pushed in this cycle.

## Blocker: a committed paid deliverable remains reachable in local history

`f6a9e3b` ("Commit the B12-007 and B12-009 deliverables their tracked test
needs") added three paid deliverables:

| File | Bytes |
|---|---:|
| `books/batch12/B12-007_digital_declutter_plan.pdf` | 14,824 |
| `books/batch12/B12-007_digital_inventory.xlsx` | 9,374 |
| `books/batch12/B12-009_pet_sitter_handover_kit.pdf` | 16,718 |

`0bc69f7` later removed them from the tip tree and widened `.gitignore` to
`books/**/*.pdf` and `books/**/*.xlsx`, but it could not remove the earlier
commit. `f6a9e3b` is an ancestor of HEAD, so its blobs are reachable from the
branch tip and would be uploaded by a normal `git push`. They could then be
downloaded from the commit's tree even though the current checkout does not
list them.

`0bc69f7`'s own message already says: "main must NOT be pushed until the
founder decides how to drop that commit; a history rewrite was blocked as
destructive." This addendum confirms that statement against the current
history.

## Scale of the pre-existing exposure

`origin/main` already tracks **32** paid-format files under `books/`
(`pdf`/`xlsx`/`docx`/`zip`). Those are a founder-accepted, already-pushed
state; `0bc69f7` deliberately left them untouched. The dependency diff
`origin/main..HEAD -- books/` is empty, so the tip does not add a new paid
file. The only new exposure is the reachable `f6a9e3b` blob set above.

This does not make the push safe under the standing policy; it only bounds
the additional risk.

## Options (none executed)

**A. Drop the three file additions from local history before the first push**
- Create a safety branch: `git branch backup/pre-paid-rewrite`
- Interactive rebase and edit `f6a9e3b` to remove only the three `books/`
  additions, keeping its test changes.
- `0bc69f7` then becomes empty or trivial; keep its `.gitignore` and test-skip
  changes, drop the redundant deletion.
- Verify no reachable object matches the three paths:
  `git log --all --oneline -- books/batch12/B12-007_digital_declutter_plan.pdf`
  should return nothing.
- This rewrites every SHA after `f6a9e3b` and must be coordinated with parallel
  work. It is destructive to shared history and requires explicit founder
  approval.

**B. `git filter-repo`**
- Same effect, requires the tool and a fresh clone; also destructive and
  founder-gated.

**C. Keep the branch unpushed**
- Safe and honest, but blocks every future GitHub-based workflow.

## Recommendation

Do **not** push. Choose A or B only after the founder approves a one-time
history rewrite, and only after the parallel-work owner confirms no other
session is building on the current SHAs. Until then, keep the 21 commits
local.

Note: the B12-007/B12-009 files remain on disk and still pass their tests
locally (`tests/test_b12_007_008_009_repair.py`); they are simply untracked
and ignored now.
