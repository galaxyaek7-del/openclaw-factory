# B12-010 — Publication Readiness

Cycle 102, 2026-10-19. This record separates three things that are easy to
confuse: what is **prepared**, what is **authorized**, and what needs
**platform access**. Nothing here authorizes or performs a publication.

Product: `B12-010` — Nonprofit Grant Pipeline Tracker
Channel: Gumroad
Release state: **`READY_FOR_AUTHORIZATION`** (`DERIVED`, `data/operational_history.json`)

## (a) Prepared — done and verified

| Item | State | Evidence |
|---|---|---|
| Workbook | Built, byte-identified | `books/batch12/B12-010_grant_pipeline_tracker.xlsx`, 38,765 B, sha256 `df49cecaf704cb06dec3b48c9f826c94cfdae9e2bf91d3a2b76fc670593b8574` |
| Method guide (PDF) | Built, byte-identified | `books/batch12/B12-010_grant_pipeline_guide.pdf`, 45,453 B, 17 pages, sha256 `b7ad0849a7d248db821c79873a8cdc3c42399a6ce054083eaf650298e97f0a49` |
| Cover image | Built, byte-identified | `books/covers/B12-010.png`, 42,566 B, 1280x720, sha256 `c17de7066cbd9bf22affa138881fc67ed3d64e7598756277b807836eaaf122ec` |
| Quality gate | `APPROVED` | `reports/B12-010/GATE_FINAL_2026-10-19.json` (core 100, content 100, market reality 70) |
| Native workbook QA | `PASS` (0 critical) | `reports/B12-010/WORKBOOK_QA_2026-10-19.json` — Excel 16.0 build 19127 |
| Price | `$15.00` `DERIVED` | `reports/B12-010/RELEASE_BASELINE_2026-10-19.json` — highest price passing every mandatory gate |
| Listing package | Prepared | `reports/phase8/B12_010_GUMROAD_LISTING_PACKAGE.md` |
| Listing copy | Prepared, brand-validated | `drafts/b12_010_listing_copy.txt` (Brand DNA 4/4 PASS) |
| Companion public page | Prepared | `customer_site/b12-grant-pipeline-tracker.html` (shows "$15 (proposed)") |
| Release manifest | `READY_FOR_AUTHORIZATION` | `reports/B12-010/MANIFEST_2026-10-19.json` |

All three artifacts' hashes match between the manifest and the files on disk
(`OBSERVED`, re-checked this cycle). `scripts/check_b12_integrity.py` exits 0.

## (b) Authorized — not done

| Item | State |
|---|---|
| Founder authorization phrase for B12-010 | **Not issued.** `MANIFEST.authorization_phrase` is `null`; `authorization_required` is `true`. |
| Founder price approval | **None.** `RELEASE_BASELINE.price.founder_approved` is `false`; `founder_decision` in `GATE_FINAL` is empty. |
| Chosen release price | `$15.00` is `DERIVED` from the standing pricing rule, **not** approved. |

No authorization statement was composed, inferred, or backfilled this cycle, and
none should be entered except by the founder.

## (c) Requires platform access — not available here

| Item | State |
|---|---|
| Live Gumroad credential in this environment | **Not configured** for a new publish here (no working token for a write from this environment). |
| `FACTORY_LIVE_PUBLISH` | Must stay `false`. |
| Actual upload | Not attempted (`published: false` in the manifest). |

Even a fully authorized product cannot be published without this second,
independent gate. Read-only access to the public store does work — the existing
listings were confirmed live by direct HTTP read this cycle — but publishing
requires a write credential this environment does not hold.

## What would change the decision

The product moves from `READY_FOR_AUTHORIZATION` to `UPLOAD_COMPLETED` only
when **both** (b) and (c) are satisfied, and then only through the real
publishing path. `FIRST_SALE_VERIFIED` requires a real external purchase on top
of that; nothing prepared here can produce it.

## Standing blockers for revenue (unchanged)

1. A product-specific founder authorization phrase for B12-010.
2. A working live publishing credential in this environment.
3. A real external buyer.
