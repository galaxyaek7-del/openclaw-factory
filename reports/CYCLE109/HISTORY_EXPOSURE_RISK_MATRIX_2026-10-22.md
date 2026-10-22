# History Exposure Risk Matrix — 2026-10-22 (Cycle 109)

Read-only risk assessment. No history rewrite, visibility change, deletion,
push, publish, or spend occurred. Source facts are from
`reports/CYCLE108/HISTORY_EXPOSURE_AUDIT_2026-10-22.md` (commit `ad103ba`).

## Current state

- Branch `main` is **ahead 28, behind 0**; HEAD `a24bf87`.
- Repository is public; GitHub Pages is enabled.
- `FACTORY_LIVE_PUBLISH` is unset/`None`; no write authorization.
- The 3 new paid artifacts are **not currently reachable**: `f6a9e3b` is not
  on origin (GitHub API `422`), its raw URL is `404`, and the files are absent
  from HEAD and `0bc69f7` trees.
- `0bc69f7` is tip mitigation, not history erasure. A push would expose
  `f6a9e3b`'s history even though the tip tree no longer contains the files.

## Matrix

| Class | Count | Current exposure | Effect of push | Risk | Why | Containment |
|---|---:|---|---|---|---|---|
| B12-007 PDF (5 pp, 14,824 B, blob `132767f70b36…`) | 1 | None (`404`) | Becomes reachable via `f6a9e3b` | **HIGH** | Complete paid deliverable; IP loss, not merely metadata | Keep push blocked; rewrite `f6a9e3b` (B) or explicitly accept (C) |
| B12-007 XLSX (6 sheets, 9,374 B, blob `8a8b93d2a98c…`) | 1 | None (`404`) | Becomes reachable | **HIGH** | Complete paid workbook | Same |
| B12-009 PDF (7 pp, 16,718 B, blob `ee14bd7f86a7…`) | 1 | None (`404`) | Becomes reachable | **HIGH** | Complete paid deliverable | Same |
| Cohort bundles (`cohort_GF_BATCH10_2026_09/dist`, `cohort_GF_BATCH11_2026_09/dist`) | 129 | **Already public** | No change | **HIGH** | Sample manifest `price_cents:6900`; paid bundles already downloadable | Founder policy: private repo, full rewrite, or documented acceptance |
| Paid files under `books/` | 32 | **Already public** | No change | **HIGH** | Earlier addendum covered only these 32 | Same |
| Other paid-format files outside those trees | 7 | **Already public** | No change | **MEDIUM–HIGH** | Must be reviewed individually before any policy decision | Same |
| Total already public paid-format | **168** | **Already public** | No change | **HIGH** | 129 + 32 + 7; a 1-byte range read of an existing paid PDF returns `206` from raw GitHub and Pages | Same |
| Total if pushed as-is | **171** | 168 public + 3 latent | +3 | **HIGH** | Push creates the last 3 exposures | Do not push |
| Secrets in outgoing range / origin | 0 | None found | None expected | **LOW** | `pdl_live_` is a docstring shape; `AKIA` is a binary-PDF false positive | No action |
| Customer PII in tracked ledgers | 0 | None found | None expected | **LOW** | 3 partnership addresses are business contacts; sample uses `example.com` | Preserve current no-PII state |

## Risk reading

1. **The 3 new files are the only exposures a push would add.** They are
   currently unobservable, so the correct immediate action is no push.
2. **The larger risk already exists.** 168 paid-format files are already on
   public `origin/main`; that is a founder policy decision, not a code fix.
3. **A tip-only fix is insufficient.** Deleting files from HEAD does not
   remove them from `f6a9e3b`; only a history rewrite (with backup and explicit
   approval) changes reachability.
4. **Do not delete local deliverables.** `check_b12_integrity.py` and the
   product tests depend on them.

## Options (not executed)

- **A — Keep push blocked.** Zero new exposure; the 168 remain.
- **B — Rewrite `f6a9e3b` before any push.** Drop the 3 additions and the
  now-empty `0bc69f7`, create a backup branch, verify blob IDs are unreachable,
  re-run the targeted suite, then request explicit `--force-with-lease`
  approval.
- **C — Accept exposure.** Only with an explicit founder decision; document
  the 3 files and the 168 in the acceptance record.

No option is selected here. `HOLD_FOUNDER_HISTORY_DECISION`.
