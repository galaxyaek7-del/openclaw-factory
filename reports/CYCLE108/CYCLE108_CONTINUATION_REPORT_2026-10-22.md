# Cycle108 Continuation Report — 2026-10-22

## 0. Snapshot

- Branch: `main`, `origin/main..HEAD` **ahead 26, behind 0** at the start of this
  round; HEAD `e83f38a`.
- `FACTORY_LIVE_PUBLISH` is unset (`None`) in this shell. No live publish, no
  transaction, no external financial action, no push, no history rewrite, no
  visibility change.
- Staged changes: 0. Dozens of tracked files are modified by parallel/factory
  work and were left untouched; only the two Cycle108 documents named below were
  staged.
- Checkpoint for this report: **`ad103ba`** (`docs(cycle108): quantify
  outgoing-history exposure and containment`).

## 1. P1 — `affiliate/publish_queue.py` security audit

Target: untracked `affiliate/publish_queue.py`, 81 lines / 3,904 bytes,
mtime `2026-09-23 18:34:20`; `data/publish_queue.json`, 2,117 bytes, 4
`PENDING_CAP` items. Imports are stdlib plus `from channels import
gumroad_publisher as gp`; there is no direct HTTP, no credential handling, and
no `FACTORY_LIVE_PUBLISH` / `check_write_authorization` reference of its own.

### Gate inventory (Gumroad mutation surface)

| Entry point | Definition | Gate | First network call | Gate before network |
|---|---:|---:|---:|---|
| `create_product` | 445 | 452 | 501 | yes |
| `update_product` | 615 | 674 | via private body | yes |
| `update_product_file` | 755 | 803 | 827 | yes |
| `enable_product` | 868 | 888 | 892 | yes |
| `add_product_cover` | 903 | 944 | 952 | yes |
| `_upload_file` | 327 | 328 | 342 | yes |
| `_abort_upload` | 290 | 304 | 309 | yes |
| `update_product_description_scoped` | 553 | consumes a single-use scope at 598 | 714 (via private body) | yes |
| `_update_product_write_and_verify` | 681 | none (private) | 714 | only callable after 674 or 598 |

`_update_product_write_and_verify` is reachable only from `update_product`
(after the unconditional gate at 674) and from
`update_product_description_scoped` (after `consume_scope` at 598). The private
body deliberately has no second gate. `create_draft_live` independently calls
`write_gate.require_write_authorization` at
`scripts/gumroad_draft_orchestrator.py:515`.

### Probe

With the current environment:

```
check_write_authorization('create_product')
  -> allowed False, state NOT_CHECKED, live_publish_flag False
gp.create_product('x', ...)
  -> WriteNotAuthorized
```

`publish_queue.py` calls only `create_product` and `enable_product`; both gate
as their first executable statement. No caller exists for `publish_queue.py`:
the only references are strings in `data/commercial_evidence.jsonl:112`,
`data/commercial_war_room.json:16`, `scripts/first_sale_orchestrator.py:1416`
(description text) and `tests/test_first_sale_orchestrator.py:252-259`
(existence check).

### Verdict

- **Write-gate bypass of Gumroad product state: NOT FOUND.** The module does
  bypass the secondary `distributor` / publish-protection registry (it calls the
  publisher directly), but it cannot reach a real mutation: every target
  function refuses with `WriteNotAuthorized` before any HTTP request.
- **Residual local side effect:** a queue entry is appended to
  `data/publish_queue.json` before the gate refuses. This is a local file write,
  not a product-state change; it is left unchanged.
- **Latent, pre-existing design gap (not this module):** the non-Gumroad arms
  (`paddle_arm`, `etsy_arm`, `payhip_arm` and their publishers) do not check
  `FACTORY_LIVE_PUBLISH`; they rely on `dry_run=True` defaults and credential
  readiness. `distributor.distribute()` defaults to `dry_run=True`, and
  `publish_protection.check_publish_allowed()` does not read the global flag.
  This is disclosed for a founder policy decision, not changed here.
- **No code edit and no new regression test.** There is no bypass to lock down;
  gate-first behavior already has coverage in `tests/test_gumroad_publisher.py`,
  `tests/test_description_scoped.py`, `tests/test_upload_gates.py` and
  `tests/test_auto_publisher.py`.

## 2. P2 — Outgoing-history exposure

Full detail: `reports/CYCLE108/HISTORY_EXPOSURE_AUDIT_2026-10-22.md`
(commit `ad103ba`).

- Exactly **3** added artifacts exist in `origin/main..HEAD`, all from
  `f6a9e3b`: B12-007 PDF (5 pages, 14,824 B, blob `132767f70b36…`), B12-007 XLSX
  (6 sheets, 9,374 B, blob `8a8b93d2a98c…`), B12-009 PDF (7 pages, 16,718 B,
  blob `ee14bd7f86a7…`). All are byte-identical to the local deliverables that
  pass `check_b12_integrity.py` (exit 0).
- **Currently exposed: NOT FOUND.** `f6a9e3b` is not on origin (GitHub API
  422), the raw URL returns 404, and the files are absent from both HEAD and
  `0bc69f7` trees. `0bc69f7` is tip mitigation, not history erasure.
- **If pushed as-is: CONFIRMED** — the three complete paid deliverables become
  reachable through `f6a9e3b`'s history.
- **Already public: CONFIRMED** — the repository is public and `origin/main`
  tracks **168** paid-format files: 129 complete priced bundles in the two
  `cohort_*/dist` trees (sample manifest `price_cents: 6900`), 32 under `books/`
  (the earlier addendum's figure), and 7 elsewhere. A 1-byte range read returns
  **206** from both raw GitHub and GitHub Pages for an existing paid PDF.
- **Secrets: NOT FOUND** in the outgoing range (0 files, 0 lines) or on origin
  (only a `pdl_live_` shape description in a docstring; no `ghp_`, private key,
  `xoxb-`, `sk-proj-`; the `AKIA` hit is a binary-PDF false positive).
- **Private customer information: NOT FOUND** in tracked ledgers. The three
  partnership addresses are business contacts at public domains; the sample CSV
  uses `example.com`; no customer name/email pair was found.
- **Containment (none executed):** (A) keep push blocked; (B) before any push,
  rewrite `f6a9e3b` to drop the three additions and drop the now-empty
  `0bc69f7`, with a backup branch and explicit approval; (C) founder decision on
  the 168 already-public files — private repo, full history rewrite, or
  documented acceptance. Do not delete local deliverables (tests depend on
  them).

## 3. P3 — Cycle108 task status

| Item | Status | Evidence |
|---|---|---|
| Publish-queue security | **CLOSED — not found** | gate probe + gate-first inventory; no code change |
| O-02 content depth | **CLOSED** | production enforcer: B12-006 3,353/2,900; B12-007 2,817/1,900; B12-008 3,280/2,900; B12-009 2,729/1,900; CQ PASS 100; overall `BLOCKED_MISSING_DATA` from `market_reality` |
| First-build failures | **DIAGNOSED, not patched** | genome `PROD-5214fb83a464299d` absent from 5,917 worktree / 5,053 HEAD log rows; 0/3,097 decisions carry `payment_evidence`; both target files are untracked/parallel-owned |
| O-05 B12-008 price | **HOLD — founder decision** | $29 `QA_FAIL__NOT_LOCAL_READY`; $18 `READY_FOR_AUTHORIZATION`; gate $18 APPROVED market 70, $29 NOT_READY (`market_reality 40 < 65`); ceiling $18.70; recommend **$18.00** |
| O-06 licensing | **HOLD — founder/legal decision** | B12-002 `UNKNOWN_NO_TERMS`; B12-005 `PARTIAL_RESTRICTION_ONLY`; B12-008 none; B12-010 no terms; review-only draft v0.1 |
| B12-008 commercial candidate | **PREPARED, not published** | PDF 17,945 B `769074972b7f…`, 7 pages; XLSX 17,408 B `89cc470444e4…`, 7 sheets, 130 formulas; not in `products.html`/catalog |
| History exposure | **CONFIRMED IF PUSHED; current none** | 3 files in `f6a9e3b`; 168 already public |
| Push readiness | **BLOCKED** | see §5 |

## 4. Verification (this round)

| Check | Result |
|---|---|
| Targeted pytest (publisher, retry, orchestrator, auto-publisher, rehearsal, first-product-build) | **181 passed, 3 failed** in 60.79s |
| Known failure 1 | `test_final_rehearsal.py::test_no_autopublish_path` — local untracked `affiliate/publish_queue.py` exists |
| Known failure 2 | `test_first_product_build.py::test_genome_finds_registered_product` — missing provenance record |
| Known failure 3 | `test_first_product_build.py::test_market_evidence_not_gf_sale` — decision snapshot has 0 `payment_evidence`, test expects 2 |
| `python scripts/check_doctrine.py` | exit 0, `ok: true`, 53 passed |
| `python scripts/check_b12_integrity.py` | exit 0, `OK (10 prep items, 5 baselines)` |
| `git diff --check` | exit 0 (CRLF advisory warnings only) |
| Protected artifacts | `finance_data.json` 312 B `6b5742e17235…`; `config/reality.json` 1,286 B `a9cfa4e74a1f…`; `sales_ledger.jsonl` 0 B `e3b0c44298fc…`; `data/decisions.jsonl` 16,634,705 B `ede3cc33af0a…` |
| Environment | `FACTORY_LIVE_PUBLISH=None`; staged 0; no push |

The three failures are the same known, pre-existing conditions reported earlier
and are not caused by this round's document-only work. No product code was
modified.

## 5. Push readiness

**BLOCKED.** Pushing would publish three complete paid deliverables through
`f6a9e3b`'s history even though the tip tree no longer contains them. Clearing
requires founder approval of a history rewrite (Option B) or an explicit decision
to accept the exposure. Separately, the 168 files already on public
`origin/main` need an explicit founder decision; the earlier addendum only
accepted the 32 under `books/`.

## 6. Next safe action

1. Founder chooses **A / B / C** for the three files and, separately, the policy
   for the 168 already-public files. Until then, keep the push blocked.
2. If **B** is approved: create a backup branch, rewrite `f6a9e3b` to drop the
   three additions, verify the blob IDs are unreachable and the three paths have
   no history, re-run the targeted suite, then request approval for a
   `--force-with-lease` push.
3. In parallel, the next business decision is B12-008: approve the **$18.00**
   price and the review-only license terms, or keep both on HOLD. No spend and
   no publish occur without that decision.
