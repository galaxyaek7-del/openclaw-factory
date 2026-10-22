# History Exposure Audit — 2026-10-22

Status: **BLOCKED_PENDING_FOUNDER_APPROVAL** (no push, no rewrite, no visibility change).

Scope: the outgoing local history (`origin/main..HEAD`, 26 commits ahead, 0 behind,
HEAD `e83f38a`), plus a read-only check of what is already published on
`origin/main`. Method: `git log/diff/ls-tree/cat-file/rev-parse`, the public
GitHub REST API, and HTTP range reads (1 byte) against `raw.githubusercontent.com`
and GitHub Pages. No file contents were downloaded or printed.

## 1. New exposure in the outgoing range

Exactly **three** added artifacts exist in the whole outgoing range. All three
come from one commit, `f6a9e3b`. Each is byte-for-byte identical to the local
deliverable that passes `python scripts/check_b12_integrity.py` (exit 0):

| File | Git blob (SHA-1) | Bytes | Local SHA-256 (prefix) | Complete deliverable | In HEAD tree | In `origin/main` |
|---|---|---:|---|---|---|---|
| `books/batch12/B12-007_digital_declutter_plan.pdf` | `132767f70b36…` | 14,824 | `b25c4e0f7d3e…` | yes — 5 pages | no | no |
| `books/batch12/B12-007_digital_inventory.xlsx` | `8a8b93d2a98c…` | 9,374 | `6ff62c7847c3…` | yes — 6 sheets | no | no |
| `books/batch12/B12-009_pet_sitter_handover_kit.pdf` | `ee14bd7f86a7…` | 16,718 | `43d488f20958…` | yes — 7 pages | no | no |

Evidence that they are not exposed **today**:

- `git cat-file -e HEAD:<path>` and `git cat-file -e 0bc69f7:<path>` both fail
  (`0bc69f7` removed them from the tip tree and widened `.gitignore` to
  `books/**/*.pdf` and `books/**/*.xlsx`).
- `GET /repos/galaxyaek7-del/openclaw-factory/commits/f6a9e3b` returns **422**
  (the commit has never been pushed).
- `https://raw.githubusercontent.com/.../main/books/batch12/B12-007_digital_declutter_plan.pdf`
  returns **404**.

Evidence that they **would** be exposed if the branch is pushed as-is:

- `f6a9e3b` is an ancestor of HEAD (`git merge-base --is-ancestor` true), so the
  blobs are reachable from the pushed history even though the tip tree no longer
  contains them. `0bc69f7` is mitigation of the tip, not erasure of the history.

## 2. Controlled commits in the outgoing range (no paid artifacts)

| Commit | What it adds | Paid deliverable? |
|---|---|---|
| `32737cc` | `tests/test_b12_007_008_009_repair.py` | no |
| `4b383ab` | publisher `add_product_cover` + tests + `reports/B12-001/listing_copy.prepared.md` (marketing copy) | no |
| `0bc69f7` | removes the three files above; widens `.gitignore` | removal only |
| `804b42b` | `config/reality.json` | no |
| `3d2e8e4`, `08a4663` | Cycle108 reports | no |
| `46d182f`, `e60ccb8`, `acf61ce`, `e83f38a` | incident note, test portability, publisher tests, retry classification | no |

No other binary product artifact was added anywhere in `origin/main..HEAD`.

## 3. Secrets in the outgoing range

- Added lines matching credential shapes (`pdl_live_`, `ghp_`, private-key
  header, `xoxb-`, `sk-proj-`, `AKIA`): **0 files, 0 lines**.
- Email-shaped added lines: **0**.
- Origin-wide (not just outgoing): no credential value was found. `pdl_live_`
  appears only inside a docstring in `channels/paddle_publisher.py` that
  describes the key shape; there is no matching live key. `AKIA` has one
  binary-PDF false positive and no text credential. `ghp_`, private-key headers,
  `xoxb-` and `sk-proj-` produce no text hits.
- No `.env`, `.pem`, `.p12`, SSH private key, SQLite or n8n database is tracked
  on `origin/main` (path-name scan).

## 4. Private information in the outgoing range

- No customer/account ledger is added by any outgoing commit.
- Tracked origin data checked schema-only:
  - `data/customer_interest.jsonl`: 0 rows.
  - `data/customer_interest_rejected.jsonl`: 5 rows, 0 email-shaped strings.
  - `data/lead_discovery_events.jsonl`: 21 rows, 0 email-shaped strings.
  - `data/realbiz05_accounts.json`: 1 record, 0 email-shaped strings.
- Nine tracked `data/` files contain email-shaped text; three are business
  partnership contacts (`easecert.com`, `euverify.com`, `cert-rep.com`) and one
  is a quoted public post (`uisual.com`). No customer name/email pair was found
  in tracked ledgers.
- `customer_site/*.html` contains the public contact address; the sample lead
  CSV uses `example.com` only.

## 5. Exposure that already exists (pre-dates this cycle)

- The repository is **public** (`private=false`, `visibility=public`,
  `has_pages=true`, default branch `main`).
- `origin/main` tracks **168** paid-format files (`.pdf/.xlsx/.docx/.pptx/.zip/
  .mp4/.epub`):
  - **129** complete priced bundles under `cohort_GF_BATCH10_2026_09/dist` and
    `cohort_GF_BATCH11_2026_09/dist` (sample manifest: `price_cents: 6900`);
  - **32** under `books/` (the number cited in the earlier addendum);
  - 7 others under `demo_cookbook/`, `seeds/`, `product_review_2026-07-13/`.
- A 1-byte range read of an existing paid PDF returns **206** on both
  `raw.githubusercontent.com` and `galaxyaek7-del.github.io`, proving these
  files are publicly downloadable, not merely present in the tree.

## 6. Verdict

| Question | Verdict |
|---|---|
| Is there new exposure right now? | **NOT FOUND** — the three files are absent from origin and return 404. |
| Would pushing as-is expose new paid products? | **CONFIRMED** — three complete deliverables become reachable via `f6a9e3b`. |
| Are credentials exposed in the outgoing range? | **NOT FOUND**. |
| Is private customer information exposed in the outgoing range? | **NOT FOUND**. |
| Is there pre-existing public exposure of paid products? | **CONFIRMED** — 168 files, downloadable today; independent of this cycle. |

## 7. Containment options (none executed)

**A. Keep the push blocked (current state).** Sufficient for the new risk until
the founder decides. No history is rewritten, nothing already public changes.

**B. Rewrite the unpushed history before any push.** Create a backup branch,
then remove the three file additions from `f6a9e3b` (interactive rebase/edit;
`0bc69f7` becomes a no-op and can be dropped). Verify:
`git log --all --oneline -- books/batch12/B12-007_digital_declutter_plan.pdf`
and the two siblings are empty, and the three blob IDs are unreachable from the
rewritten refs. Force-push with lease only after explicit approval. This is
destructive to the local history and must not be done without a backup branch
and founder approval.

**C. Decide what to do about the 168 already-public files.** Options, in
increasing blast radius:
1. make the repository private (complete containment going forward, but it
   disables the public Pages site/storefront and any public SEO already earned);
2. rewrite all history to remove the files (large, breaks every existing clone,
   and cannot recall copies already downloaded);
3. accept and document the exposure (today's de-facto state; the earlier
   addendum only explicitly accepted the 32 under `books/`, not the 129 cohort
   bundles).

Recommendation: **A now**, then **B before any push**, then an explicit founder
decision on **C**. Do not delete the local deliverables (tests and
`check_b12_integrity.py` depend on them) and do not `git add .` or force-push
without a backup.
