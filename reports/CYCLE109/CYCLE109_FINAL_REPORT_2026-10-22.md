# Cycle 109 Final Report - 2026-10-22

Repository checkpoint before this report's commit: `a24bf87` (`main` ahead 28
of `origin/main`, behind 0). No push, publish, transaction, history rewrite,
visibility change, or spend was performed. `FACTORY_LIVE_PUBLISH` is unset
(`None`); the write gate denies real mutation.

## 1. Objective and guardrails

The round had two goals: repair the three verified failing tests, and finish
safe pending Cycle 108 work without exposing paid deliverables or inventing
commercial evidence. All work was local and read-only except for test files,
the asset registry links, and cycle reports.

Hard constraints retained: $0 new spend; fail-closed publishing; no financial
action; no destructive Git operation; preserve parallel-owned and untracked
work; never fabricate a sale, revenue, review, or provenance record.

## 2. Result summary

- Three targeted failures now pass: `3 passed in 2.41s`.
- Affected suite: `63 passed in 68.59s`.
- Doctrine tests: `53 passed`; `scripts/check_doctrine.py` OK.
- `scripts/check_b12_integrity.py`: `B12 integrity: OK (10 prep items, 5
  baselines)`.
- `git diff --check`: exit 0.
- The full `pytest tests` run is not green and was not made green by this
  round. An attempted full run exceeded 30 minutes and was killed at 94%;
  `lastfailed` held 62 entries, and a later `--lf` run showed 20 unrelated
  failures plus 6 root-level collection errors (`test_cover.py`,
  `test_output.txt`, `test_results*.txt`, `test_status.txt`, and
  `scripts/show_paddle_test.py`). These are pre-existing code-drift/stale-test
  problems, not regressions from these repairs.

## 3. The three failing tests: root cause, fix, evidence

### 3.1 `tests/test_final_rehearsal.py::test_no_autopublish_path`

Root cause: the test scanned `affiliate/*.py` by directory glob, so an
operator-owned, untracked utility (`affiliate/publish_queue.py`, 81 lines)
failed an invariant meant for repository code. The utility calls only
`create_product` and `enable_product`, both of which check the write gate as
their first executable statement, but the test could not distinguish tracked
code from local scratch.

Fix: enumerate only `git ls-files -- affiliate` Python files; keep the
`enable_product(` / `distributor.publish` assertions; add a `git grep` check
proving no tracked Python module imports `publish_queue`. This preserves the
security intent while making repository ownership explicit.

### 3.2 `test_first_product_build.py` genome lookup

Root cause: a historical `PROD-5214fb83a464299d` row no longer exists in the
generation log, but the real `data/asset_registry.json` still records GF-011.
The genome code only consulted the generation log by `production_id`, then
failed on a real registered asset.

Fix in the local working tree (`product_genome.py`, still untracked and not
committed): `_asset_registry_record()` matches an exact `production_id` or an
exact artifact path; QA accepts `PASS` or an equal `N/N` result; the genome
records `registration_source: "asset_registry"` and adjusts its lifecycle
evidence accordingly. No generation-log row was created or altered.

`data/asset_registry.json` was corrected to link GF-001 to
`PROD-77af8be77621c9a6` and GF-011 to `PROD-5214fb83a464299d`; JSON validation
passes with 22 assets.

### 3.3 `test_controlled_customer_validation.py` protected-state check

Root cause: whole-file SHA-256 values made the test fail whenever any parallel
process appended to `finance_data.json`, `config/reality.json`, or the sales
ledger. A file hash is not the commercial invariant.

Fix in the local working tree (untracked, not committed): assert the real
semantics instead - `finance_data.sales == []`, all totals zero,
`reality.published_books == []`, `commercial_proof == "UNKNOWN"`, and zero
`sale` events in `data/sales_ledger.jsonl`. The genome assertion now passes a
real artifact path and requires the registry source.

Supporting test added and committed: `tests/test_market_evidence_separation.py`
proves legal-niche market evidence carries a source URL and quote, is not a
sale/revenue event, and that finance plus the sales ledger contain zero sales.
It skips the ledger assertion when the untracked local ledger is absent.

Ownership note: `product_genome.py`, `tests/test_first_product_build.py`, and
`tests/test_controlled_customer_validation.py` remain untracked and were not
committed. The targeted tests pass only in this workspace because those local
changes are present.

## 4. Affiliate publish-path audit

Verdict: **no write-gate bypass found**. `affiliate/publish_queue.py` is
untracked, 81 lines / 3,904 bytes, has no callers, no direct HTTP, and no
credential handling. It calls only the gated `create_product` and
`enable_product` entry points.

Every real Gumroad mutation checks the gate before network I/O:
`create_product` (452), `update_product` (674), `update_product_file` (803),
`enable_product` (888), `add_product_cover` (944), `_upload_file` (328), and
`_abort_upload` (304). The scoped description path consumes its single-use
scope at 598 before its private write body. `create_draft_live` independently
calls `require_write_authorization` at
`scripts/gumroad_draft_orchestrator.py:515`.

Live probe: `check_write_authorization('create_product')` returned
`allowed False, state NOT_CHECKED, live_publish_flag False`;
`gp.create_product(...)` raised `WriteNotAuthorized`.

Residual risks disclosed, not fixed: the queue appends locally to
`data/publish_queue.json` before the denial, and the non-Gumroad arms
(`paddle_arm`, `etsy_arm`, `payhip_arm`) do not check `FACTORY_LIVE_PUBLISH`.
Neither creates a live external effect in the current configuration.

## 5. Paid-artifact history exposure

`origin/main` already contains **168** paid-format files: 129 cohort bundle
files under `cohort_GF_BATCH10_2026_09/dist` and
`cohort_GF_BATCH11_2026_09/dist`, 32 under `books/`, and 7 elsewhere. A
one-byte range read of an existing paid PDF returned HTTP 206 from both raw
GitHub and Pages, so these are already downloadable.

Commit `f6a9e3b` adds exactly 3 more complete paid deliverables: B12-007 PDF
(14,824 B), B12-007 XLSX (9,374 B), and B12-009 PDF (16,718 B). These are not
currently reachable: the commit is absent from origin (GitHub API 422), the
raw URL is 404, and the files are absent from HEAD and `0bc69f7` trees.
`0bc69f7` removes them from the tip but does not erase history; a push as-is
would make all 3 reachable and raise total exposure to **171**.

Decision remains `HOLD_FOUNDER_HISTORY_DECISION`. Options are documented in
`reports/CYCLE109/HISTORY_EXPOSURE_RISK_MATRIX_2026-10-22.md`: keep push
blocked (A), rewrite `f6a9e3b` with backup and explicit force-with-lease
approval (B), or explicitly accept the exposure (C). No option was executed.

No secrets were found in the outgoing range or origin text. No customer PII
was found in tracked ledgers; the three addresses are business contacts and
the sample uses `example.com`.

## 6. B12-008 price and state

Records conflict: `data/product_batch_12.json`,
`data/product_batch_12_gumroad_prep.json`, and the Phase 8 listing package say
$29, while the final release record and the live gate at $18 say approved.
The $29 state is `QA_FAIL__NOT_LOCAL_READY`; $18 is
`READY_FOR_AUTHORIZATION` with market reality 70.

Direct probes: $18.00 and $18.70 pass; $18.71 and $19.00 fail. The gate script
hardcodes `SUPPORTED_PRICE=18.0`, so $18 is supported but not proven maximal;
$18.70 is the highest tested passing value. Recommendation remains **$18.00**,
because it is gate-approved, integer, and already recorded. The founder has
not approved it; no price was changed.

## 7. O-02, O-05, O-06

- **O-02 (closed, no approval needed):** content depth is 3,353/2,900
  (B12-006), 2,817/1,900 (B12-007), 3,280/2,900 (B12-008), and 2,729/1,900
  (B12-009); all PASS; quality score 100. The batch remains
  `BLOCKED_MISSING_DATA` only because batch market reality is missing.
- **O-05 (founder decision):** choose $18.00 (recommended), $18.70, or $29.00
  (fails current market reality). On approval, correct registry, Gumroad prep,
  and Phase 8 package, refresh the stale state from existing QA evidence, and
  re-run B12 integrity.
- **O-06 (founder/legal decision):** B12-002 has no terms; B12-005 has a
  restriction only; B12-008 has none; B12-010 has no terms. The draft
  single-user license in the founder brief is review-only, not legal advice,
  and has not been applied.

## 8. First-sale candidate

The strongest existing candidate is B12-008 at $18.00: ready-for-authorization
state, passing content depth, a 7-page PDF and a 7-sheet/130-formula workbook,
and a gate-approved $18 price. It is not in `data/catalog.json` or
`products.html`, has no approved license, and has no listing authorization.
The 168-file exposure issue and the unresolved price/license decisions must be
settled before any legitimate listing step.

## 9. Safety and verification

- No publish, external write, purchase, or financial action occurred.
- No push, force-push, rewrite, delete, or visibility change occurred.
- No secrets printed or added; no paid product contents reproduced.
- `FACTORY_LIVE_PUBLISH=None`; write gate denied mutation in a live probe.
- Protected ledgers were not edited: `finance_data.json` (312 B,
  `6b5742e17235c0e8`), `config/reality.json` (1,286 B,
  `a9cfa4e74a1f652f`), and `data/decisions.jsonl` (16,634,705 B,
  `ede3cc33af0ab40d`).
- `data/sales_ledger.jsonl` changed externally/parallel before this round
  (51,289 B, `a71d75d8846c3826`; 135 `publish_attempt`, 0 `sale`, last write
  2026-10-12). This round did not write it.
- `git diff --check` exit 0; doctrine and B12 integrity checks pass.

## 10. Blockers and next action

Blockers:

1. Push is blocked by the 3 latent exposures in `f6a9e3b`; history policy for
   the 168 already-public files is a founder decision.
2. B12-008 price and the B12 license terms require founder approval.
3. The repaired genome and controlled-validation tests remain untracked; their
   local dependency must be committed separately once ownership is confirmed.
4. The full suite has unrelated pre-existing failures and collection errors.
5. Non-Gumroad arms lack the `FACTORY_LIVE_PUBLISH` gate (latent).
6. No real sale, revenue, or customer exists.

Next action, in order: founder decides history option A/B/C; founder approves
price and license; then correct registry/prep/listing state from existing
evidence, re-run artifact QA and B12 integrity, and only then request explicit
listing authorization. Do not push and do not enable live publishing before
those decisions.
