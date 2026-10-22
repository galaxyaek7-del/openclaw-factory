# A push path that never publishes the three paid files (2026-10-22)

This is the problem recorded in `reports/CYCLE108/HISTORY_EXPOSURE_AUDIT_2026-10-22.md`.
Local `main` contains commit `f6a9e3b`, which added three complete paid
deliverables (B12-007 PDF and XLSX, B12-009 PDF). A later commit untracks
them, but pushing `main` as it is would make them downloadable from the public
repository through that commit. Rewriting `main` was blocked as destructive.

## What was prepared (no rewrite, nothing pushed)

Branch **`clean-history-20261022`** was built in a separate worktree:
- based on `origin/main` (`7cb880f`);
- every local commit replayed with `git cherry-pick -x` in order, **except
  `f6a9e3b`**;
- the working tree and local `main` were not touched.

## Proof

| Check | Result |
|---|---|
| Tree of `clean-history-20261022` vs tree of `main` at preparation time | **identical** (`9899e976…`) |
| The three paid blobs reachable from `origin/main..clean-history-20261022` | **0 of 3** |
| `f6a9e3b` reachable from the clean branch | **no** |
| `origin/main` is an ancestor of the clean branch | **yes**, so the push is a normal fast-forward, never a force push |

## Founder steps (each needs your explicit go-ahead)

1. Check that the branch still matches `main`. Commits added to `main` after
   preparation must also be cherry-picked onto it:
   `git rev-parse main^{tree} clean-history-20261022^{tree}`
   (the two lines must be equal).
2. Push it as `main`. This also deploys GitHub Pages:
   `git push origin clean-history-20261022:main`
3. Realign local `main` to the published history **only after** confirming
   the push. This rewrites local `main`, so keep a backup branch first:
   `git branch backup-main-before-realign main`, then
   `git switch main` and `git reset --hard origin/main`.
   Run this with every parallel session stopped, because `reset --hard`
   discards uncommitted work.

The 168 paid-format files that were **already** public before today are a
separate founder decision; see the CYCLE108/CYCLE109 risk matrix.
