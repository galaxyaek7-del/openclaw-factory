# Crash Recovery Evidence — 2026-10-22

**Scope:** read-only recovery verification after the reported runtime panic
(`panic(thread 17060): Illegal instruction`) in the Galaxy Forge workspace.
No file was modified, staged, published, or paid for during this verification.

**Labels used:** MEASURED (directly observed), LIKELY (best-supported inference),
UNKNOWN (no evidence available).

---

## 1. Crash evidence

| Item | Finding | Basis |
|---|---|---|
| Panic source | `opencode.exe` v1.19.0, npm global install (`%APPDATA%\npm\node_modules\opencode-ai\bin\opencode.exe`, 180,714,888 bytes) | MEASURED |
| Embedded runtime | `Bun v1.3.14 (0d9b296a) Windows x64 (baseline)` string present in the binary | MEASURED |
| Panic strings | `Illegal instruction at address`, `oven-sh/bun/issues/18546`, `BUN_INTERNAL_SUPPRESS_CRASH_ON_UV_STUB` present in the binary | MEASURED |
| Standalone `bun` | Not installed (`where.exe bun` fails); no bun reference in `package.json` or `opencode.json` | MEASURED |
| OS crash record | No Application Error / WER event and no `.dmp` in the last 3 hours | MEASURED |
| Panic in session store | No occurrence in `opencode.db` parts other than this session's own messages | MEASURED |
| CPU | Intel Core i5-8365U, 4 cores | MEASURED |
| Smallest safe repro | `opencode --version` → `1.19.0`, exit 0; `opencode --help` → exit 0 | MEASURED |

**Root cause: LIKELY** — SIGILL inside the Bun 1.3.14 runtime embedded in
`opencode.exe` v1.19.0. The specific faulting instruction/trigger is **UNKNOWN**:
no dump, no panic stack, and no deterministic reproduction.
No upgrade, downgrade, or reinstall was attempted.

---

## 2. Checkpoint and orchestration

| Item | Value | Basis |
|---|---|---|
| Last write by interrupted session `ses_ec036181cffeXnc2My6zokMH3S` | `2026-10-22T11:38:46Z` (patch at `11:38:44Z` to `reports/CYCLE107/PRODUCT_LICENSING_EVIDENCE_2026-10-22.md`, B12-002 row `11,503/2f047f5a…` → `11,360/273e05c5…`) | MEASURED |
| New session `ses_e9c77e91effeHzGH5tcsaEyynt` | created `2026-10-22T12:13:45Z` | MEASURED |
| `factory_loop.js` | PID 18396, running since 18/10/2026 14:09:48 | MEASURED |
| Last tick | completed `2026-10-22T12:15:23.697Z` (~10 min cadence) | MEASURED |
| `data/factory_state.json` | `current_task: null`, `active_workflow: null`, `updated_at: 2026-10-22T12:15:23.696Z` | MEASURED |
| `recovery_info` | `interrupted: true` dated 2026-10-18 (stale; "nothing was in flight") | MEASURED |
| Other processes | `server.js` PID 14608; `supervisor.js` PIDs 10972 and 18272 (same start time — possible duplicate supervisors, **not investigated**); n8n PID 5696 | MEASURED |

Orchestration was **not** left mid-task: the state file is clean and the next
scheduled tick completed normally.

---

## 3. Work preservation

- `git status --porcelain`: 2,219 entries, **0 staged**, 2,043 untracked.
- `HEAD` = `cbaed82` (2026-10-22 13:12:12 +0100, n8n read-only workflow health verifier).
- Parallel uncommitted work was intact and executable — no reflog/reset/clean was run.

---

## 4. Artifact integrity (independently recomputed)

| File | Bytes | SHA-256 |
|---|---|---|
| `books/batch12/B12-002_client_handoff_guide.pdf` | 11,360 | `273e05c5d8720ebe61ab44b2a9a6a3ef9f07f4eea4c561283c3ef0dd79b80f07` |
| `books/batch12/B12-002_client_handoff_register.xlsx` | 15,941 | `e733ea8e913899b53ebe9a69d3e273d4ed018f997e47f006bbe1263d90543fda` |
| `books/covers/B12-002.png` | 41,691 | `e850c13e46403395c767fc7c4bc057670e5225c7df4fcd6ff1f5531281f4e892` |
| `books/batch12/B12-005_podcast_guest_scripts.pdf` | 20,146 | `246268d4ba41c6099a1d78ddd74c10203106f6999d4908710178fbd1d749bb9e` |
| `books/batch12/B12-005_podcast_guest_tracker.xlsx` | 17,400 | `0720869bd302ff7c49c03edae97722d22161061191650380fc9047913e124b14` |
| `books/covers/B12-005.png` | 43,443 | `6dbd963a193c1f91634c986cebcaf69335ab9dfb77f01ddeab579eaea17cec8a` |

- Worktree bytes are identical to `git cat-file blob HEAD:<path>` for all four
  tracked B12-002/B12-005 deliverables.
- Content: B12-002 = 4 pages / 1,738 words PDF, 6 sheets / 102 formulas XLSX;
  B12-005 = 8 pages / 3,371 words PDF, 6 sheets / 154 formulas XLSX.
- B12-010 also matches `reports/B12-010/MANIFEST_2026-10-19.json` and
  `QA_FACTS_2026-10-21.json`: PDF 45,453 / `b7ad0849…`, XLSX 38,765 / `df49ceca…`,
  cover 42,566 / `c17de706…`.
- CRLF concern addressed: `.gitattributes` marks `*.pdf *.xlsx *.zip *.png` binary
  (commit `6dd2d4f`); `git check-attr` confirms `binary: set`, `diff/merge/text: unset`.

## 5. Manifest legitimacy

`git show HEAD:reports/CYCLE104/LISTING_PAYLOADS_B12.json` **already** contains the
canonical hashes `273e05c5…` / `246268d4…`. The working-tree diff is only:

```
"generated_at": "2026-10-19T19:18:05+00:00"  →  "2026-10-22T11:11:43+00:00"
```

No price, state, or hash was altered to fit the artifacts; the corrupted artifacts
were restored to the already-committed canonical values.

---

## 6. Safety gate

| Check | Result |
|---|---|
| `gf_readonly_write_gate_status` | `live_publish_flag_in_this_process: false`, `observable_decision: DENY`, auth `VERIFIED` at `2026-10-19T08:03:23.474741+00:00`, `stale: true` |
| `.env` | `FACTORY_LIVE_PUBLISH=false` |
| `data/operating_mode.json` | `AUTONOMOUS_COMMERCIAL_EXECUTION`, `EVIDENCE_GATED`, `FOUNDER_GATE`, sales 0, revenue 0, invariants CLEAN |
| `config/reality.json` | `published_books: []`; `commercial_proof` **absent** |
| `finance_data.json` | 0 sales, 0 revenue |

No publication, transaction, credential use, or spend occurred.

---

## 7. Verification actually executed

| Command | Result |
|---|---|
| `python scripts/check_b12_integrity.py` | exit 0 — `B12 integrity: OK (10 prep items, 5 baselines)` |
| `python -m pytest tests/test_b12_listing_payloads.py -q` | `9 passed in 1.08s` |
| `python -m pytest tests/test_storefront_commercial_check.py tests/test_catalog_integrity.py tests/test_catalog_sync.py tests/test_commercial_reconciliation.py tests/test_doctrine_layers.py -q` | `146 passed, 2 subtests passed in 3.90s` |
| `python -m pytest tests/test_b12_010_workbook.py tests/test_b12_006_repair.py tests/test_b12_007_008_009_repair.py -q` | `73 passed in 4.75s` |
| `python scripts/check_doctrine.py` | exit 0 — `doctrine_tests: 53 passed` |
| `node scripts/check_jsonl_duplication.js` | exit 0 — no new JSONL-read duplication beyond baseline |

Pre-existing failures, confirmed unrelated to this recovery (unchanged before/after):

- `tests/test_first_product_build.py` → `test_genome_finds_registered_product`,
  `test_market_evidence_not_gf_sale`.
- `tests/test_production_wiring.py` → 3 failures, incl.
  `AssertionError: None != 'UNKNOWN'` / `Missing required field: commercial_proof`.
- `tests/test_final_rehearsal.py -k no_autopublish` → `'enable_product('` unexpectedly
  found in `affiliate/publish_queue.py`.

Same-day follow-up (Addendum 4 of the register): the `test_production_wiring.py`
group is **closed** by completing `config/reality.json` with honest absence
fields; the other three are classified as data absence, data drift, and
untracked parallel work respectively. `tests/test_b12_010_workbook.py` now
passes 22/22 after parallel uncommitted work, so T-53's B12-010 item is closed.
The untracked `tests/test_backup_recovery_visibility.py` was already 4-failed
before this pass (stale baselines, missing endpoint registration); it was not
touched.

---

## 8. Stale references: audited four ways, not uniformly "stale"

The earlier version of this section called all four references stale. That was
too coarse. Each was checked against its own source and is classified below.

| Reference | Classification | Basis |
|---|---|---|
| `reports/CYCLE107/TODO_CLOSURE_REGISTER_2026-10-20.md` T-33/T-34 (`2f047f5a…`, `a7b11fbc…` "matched manifest sync") | **FALSE CLAIM — corrected by supersession** | `git log -p --follow` on `reports/CYCLE104/LISTING_PAYLOADS_B12.json` shows one commit (`b1a8ffb`) containing only the canonical `273e05c5…`/`246268d4…`; the old values never appeared there. No manifest sync ever occurred. T-51/T-53 and the new Addendum 4 supersede the claim; the historical rows are retained |
| `reports/CYCLE105/ARTIFACT_QA.json` | **TRUE AT SCAN TIME — leave unchanged** | Dated scan (`generated_at 2026-10-21T09:51:14Z`). Its hashes were the real worktree bytes then; it is a historical snapshot, not a current-state assertion. Rewriting it would falsify a dated record |
| `reports/B12-005/QA_FACTS_2026-10-22.json` (`worktree_delivery_file`) | **TRUE WHEN WRITTEN — left unchanged, explained** | `a7b11fbc…`/20,365 B was the real pre-normalization worktree file. Its identity conclusion (`246268d4…` canonical, same extracted text) is still correct. Only the boolean `checks.worktree_is_crlf_normalization_of_committed_blob` has become false as a *current-state* assertion after `.gitattributes` normalized the tracked PDFs; correcting it in place would rewrite evidence, so Addendum 4 explains it instead |
| `data/operational_history.json` | **STALE GENERATED STATE — HOLD, do not regenerate** | Its two hash strings are stale, but it is a generated current-state file consumed by `doctrine_review.py`, `handoffs.py`, and `business_arms.py`. Regenerating it would also rewrite `registry_state` (B12-001/003/004 → `PUBLISHED_AND_VERIFIED`; products 5-8 → `QA_FAIL__NOT_LOCAL_READY`), importing unverified publication state that contradicts `config/reality.json`'s `published_books: []`. Correcting the two strings by hand would make the file partly fabricated. Left as-is pending registry reconciliation |

No artifact was corrupt in any of the four cases. The one genuinely false claim
was a register statement about a manifest sync that never happened; it is now
superseded rather than silently edited.

---

## 9. Work status (none of these was caused by the crash)

From `reports/CYCLE107/TODO_CLOSURE_REGISTER_2026-10-20.md`:

- `O-02` B12-006/007/008/009 content depth — **CLOSED** (Addendum 4, T-55):
  current word counts 3,352 / 2,808 / 3,288 / 2,766 against `price x 100`
  requirements of 2,900 / 1,900 / 2,900 / 1,900; repair suites pass. The earlier
  `233-273 words` figures were pre-repair Cycle-104 snapshots
- `O-03` — BLOCKED (outside session authority)
- `O-05` B12-008 price/state — HOLD (founder decision only; identity closed by T-52)
- `O-06` license terms — UNKNOWN (founder terms decision)
- `F-07` Paddle checkout — BLOCKED (account onboarding)
- `F-08` / `F-09` — founder dashboard items
- `G-01…G-06` — gaps not implemented
- `T-53` B12-010 identity — resolved by parallel work this session
- `T-54` four-reference audit — PASS (T-33/T-34 false claim superseded;
  `operational_history.json` HOLD)
- `T-56` `config/reality.json` commercial fields — PASS (honest absence states)
- `T-57` failing test groups — classified; only the untracked
  `affiliate/publish_queue.py` autopublish path remains open, owned elsewhere

Interrupted session's own todo list (statuses never updated after the crash):

| # | Item | Evidence state |
|---|---|---|
| 0 | Resolve B12-008 asset identity | evidence produced (`reports/B12-008/*_2026-10-22.json`) |
| 1 | B12-008 and B12-002 pricing decision documents | produced (`PRICE_STATE_RECONCILIATION`, `IDENTITY_AND_PRICE_PROVENANCE`) |
| 2 | Licensing release brief from actual artifacts | produced (`PRODUCT_LICENSING_EVIDENCE_2026-10-22.md`) |
| 3 | Paddle historical/current request evidence | produced (`PADDLE_READ_DIAGNOSIS_2026-10-22.md`) |
| 4 | Gumroad cleanup / historical-error analysis | register entries updated |
| 5 | One safe independent commercial improvement | **UNVERIFIED** — no attributable artifact |
| 6 | Update registers + final focused verification | register updated; verification done here |

---

## 10. Status

**Recovery: PASS.** No work was lost, all six audited artifacts are byte-identical
to `HEAD`, the manifest was never falsified, the write gate stayed closed, and the
B12 integrity checks and 228 relevant tests pass.

**Factory health: NOT CLAIMED.** Recovery is not factory health: revenue is still
`$0`, `config/reality.json` still records `published_books: []`, and the write
gate is still closed. `O-05` (price/state) and `O-06` (license terms) remain
founder decisions. `O-02` is closed and the `commercial_proof` schema gap is
fixed with honest absence states, but one real safety finding remains open in
untracked parallel work: `affiliate/publish_queue.py::retry_queue()` can create
and enable Gumroad products with no gate and no live-publish check (no callers
found today). The cycle is therefore **not** reported as complete.

**Commit boundary.** Only this report and the TODO closure register were
committed (documentation-only, explicit paths, no push). The
`config/reality.json` schema fix, the B12-010 parallel-work files, and all other
uncommitted work stay in the worktree.

**Recommended non-actions:** no Bun/opencode upgrade, downgrade, or reinstall until a
reproducible fault or panic stack exists.
