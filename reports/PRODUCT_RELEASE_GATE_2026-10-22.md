# Product release gate — checkpoint (2026-10-22)

Status: **PARTIAL**. Verified revenue: **$0**. Nothing was published or edited on any platform.

## Scope decision (stated once)

The directive asks for a 10-family production engine. The evidence from the same day argues against adding products first:

- 79 live Gumroad listings and 0 sales (OBSERVED, API).
- About 20 paid products deliver a 1–2-page PDF (OBSERVED).
- Two evidence-backed products promise spreadsheets they don't ship (OBSERVED).
- **Root cause in the pipeline (OBSERVED).** `product_families/families/spreadsheet_systems.py` uses `asset_builder="techdoc_package"` and `packager="single_file"`, with sections such as "Sheet Structure & Formulas". The "spreadsheet" family therefore produces a **PDF describing** a spreadsheet, not a workbook. Real workbooks only come from the cohort builders (`cohort_workbook.py`, `workbook_upgrader.py`).

So this round builds the directive's §5 commercial quality gate first. It is the piece every future family must pass through, and it is tested end to end on real products.

## Architecture (reuse, no second factory)

```
listing copy + local deliverables
   └─ release_gate.evaluate()
        ├─ QUALITY_ASSURANCE        file_testing_engine.test_file() per file (PDF/XLSX/DOCX/ZIP/HTML)
        ├─ substance vs price       real PDF word counts; HOLD if < 25 words/$ and no working tool
        ├─ PACKAGING                manifest: name, bytes, sha256, kind
        ├─ LISTING_PREPARATION      gumroad_delivery_audit.classify() promise-vs-files + content_qa residue
        ├─ RIGHTS_AND_POLICY_REVIEW human reviewer + basis required, else HOLD
        └─ AUTHORIZATION_CHECK      READY_FOR_AUTHORIZATION = "awaiting founder"; no publish path exists
   └─ release_gate.record()     data/release_gate_state.jsonl, once per (product, fingerprint)
```

- **Assignable statuses:** QA_FAILED, HOLD, READY_FOR_AUTHORIZATION. Recording PUBLISHED_VERIFIED raises an error, and a test checks that the module contains no platform-write call.
- **Existing pieces reused:**
  - `file_testing_engine.py` (per-type file tests);
  - `affiliate/content_qa.py` (residue, banned phrases);
  - `scripts/gumroad_delivery_audit.py` (live promise-vs-delivery audit);
  - `product_families/` (family manifests);
  - `business_development.PLATFORM_REGISTRY` (channel registry).

## End-to-end local cycle (VERIFIED by execution)

| Product | As live | With the existing local workbook and corrected copy |
|---|---|---|
| GPSR EU Seller Action Kit (`fetmu`, $79) | QA_FAILED: PROMISES_MORE_FILES_THAN_ATTACHED | **HOLD**; only "human rights/policy review not recorded" remains |
| Trademark DIY Filing Kit (`vkqogv`, $69) | QA_FAILED: PROMISES_SPREADSHEET_NOT_ATTACHED; also below substance (1,705 words / $69, no tool) | **HOLD**; the working tracker clears substance; only rights review remains |

**The workbooks pass `file_testing_engine` (OBSERVED).** Each has 4 sheets, and the sheet names match the listing promises exactly. Each has only 2 formulas: light, but working.

**Packages:** `drafts/release_packages/{fetmu,vkqogv}/release_package.json`. Each contains:

- the manifest with sha256 hashes;
- the source paths;
- the exact listing sentence to replace (GPSR: "PDF cost planner" → "XLSX cost planner workbook");
- the gate's result.

Product files stay in `books/`, which is gitignored; none were copied into the public repo.

### The other reviewed products (same day, VERIFIED by execution)

| Product | Price | Local workbook (file_testing_engine) | Gate as live | Gate with workbook |
|---|---|---|---|---|
| Turo Guest Dispute (`adyvd`) | $29 | PASS, 4 sheets, 5 formulas | HOLD (rights only) | HOLD (rights only) |
| STR Direct Booking (`ppsluq`) | $59 | PASS, 4 sheets, 10 formulas | HOLD: **substance** 1,394 words | HOLD (rights only) |
| Vendor Questionnaire (`pyzqa`) | $89 | PASS, 6 sheets, **217** formulas | HOLD: **substance** 1,566 words | HOLD (rights only) |
| EU Packaging EPR (`gfsvu`) | $69 | PASS, 6 sheets, **628** formulas | HOLD: **substance** 1,546 words | HOLD (rights only) |
| Diminished Value (`dyjavs`) | $59 | PASS, 6 sheets, **211** formulas | HOLD: **substance** 1,274 words | HOLD (rights only) |
| Restaurant Inspection (`dvfvm`) | $49 | none | HOLD (rights only) | — |
| FTC Review Rule (`ekhza`) | $69 | none | HOLD: **substance** 1,715 words | — |

**Finding (OBSERVED).** Seven reviewed products have a working local workbook that was never attached on Gumroad. The live deliverable is the PDF alone. The four with the largest workbooks are sold today as short PDFs below the gate's substance bar, while the tool that justifies the price sits unshipped.

**Version drift (OBSERVED).**

| Product | Live PDF | Local PDF |
|---|---|---|
| Restaurant | 10,850 B | 30,594 B |
| FTC | 13,105 B | 33,174 B |

Which is current is UNKNOWN; the live file cannot be downloaded through this API.

**Packages:** `drafts/release_packages/<slug>/release_package.json`, 9 in total. Each has its manifest and hashes, the live files, the proposed changes and the gate result.

## Checkpoint 2 — root-cause fix and repair package (same day)

### Phase 1: the spreadsheet root cause

**OBSERVED:**

- `asset_generation/builders/` had only PDF builders: `ai_book` and `techdoc_package`.
- The workbook packager mentioned in `product_packaging/bundle.py` was never built.
- `product_families/families/spreadsheet_systems.py` was untracked, dated 2026-09-21, and never imported. It routed the family to `groq_techdoc` + `techdoc_package`: LLM prose about "Sheet Structure & Formulas", rendered to a PDF.

**Correction to checkpoint 1.** That family was never live. The live thin "Workbook"/"Calculator" PDFs came from scripts, not from this family.

**Fix:**

- `asset_generation/builders/xlsx_builder.py` (`xlsx_workbook`):
  - builds the .xlsx from a declared spec, through the existing `cohort_workbook.build_xlsx`;
  - fails closed on no spec, a spec without formulas, a non-.xlsx output, a non-OOXML file, or a file test that does not PASS.
- `spreadsheet_systems.py` is now a real adapter registered in `families/__init__.py`; `product_type_capability` reports it as REAL.
- **Formula recalculation: UNVERIFIED.** No native spreadsheet engine is available, and the builder says so in every result.

**Tests:**

- `tests/test_spreadsheet_family_xlsx.py`: 7 tests, including that a PDF renamed `.xlsx` fails both `is_genuine_xlsx` and the release gate.
- Two existing tests were updated to the new reality: family set 5→6, and spreadsheet_systems REAL instead of NOT YET BUILT.

### Phase 2: FTC and Restaurant canonical PDF (DERIVED from hashes)

**Live file = pre-fix copy (proven).** For FTC and Restaurant, the live file's sha256, recorded in `data/delivery_integrity.json`, equals the `books/_pre_title_fix_2026-10-17/` copy once its 150 / 131 inserted `\r` bytes are removed (the CRLF corruption).

**That version is defective.** Its page-1 title prints over the subtitle; `file_testing_engine` reports FAIL (text overlap).

**Canonical = `books/<name>.pdf`** (repaired 2026-10-17, file test PASS, same pages and words). Evidence:

- `reports/cleanup/PDF_REPLACEMENTS.md` documents the repair and lists the re-upload as a pending founder action.
- ADA (`palmdr`) is in the same situation; it matches on size, but no live hash is on record.

**Rollback copies.** `books/_rollback_2026-10-22/` holds copies byte-identical to the live files (gitignored). Originals untouched.

### Phase 3: workbooks and packages

**Mapping evidence (not name similarity).** Each of the 10 workbooks is named in its product's own `books/*_launch_kit.md`, and every current sha256 equals `data/cycle88_artifact_checksums.json`. That gives 7 + 3: FTC `ftc_review_rule_audit_tracker.xlsx`, Restaurant `restaurant_inspection_logs.xlsx`, ADA `ada_triage_workbook.xlsx`.

**Gate results (VERIFIED by execution):**

| Product | Live | Repaired package |
|---|---|---|
| FTC (`ekhza`) | QA_FAILED (title overlap) | HOLD, rights review only |
| Restaurant (`dvfvm`) | QA_FAILED | HOLD, rights review only |
| ADA (`palmdr`) | QA_FAILED | HOLD, rights review only |

FTC's 223-formula workbook clears its substance hold.

**Consolidated package:**

- `drafts/release_packages/REPAIR_MANIFEST.json`, built by `scripts/build_gumroad_repair_package.py`, with 14 actions:
  - 11 REPAIR;
  - 2 PROPOSE_UNPUBLISH (`owtmpe`, the file-less $0 listing; `vhofn`, the thinner duplicate);
  - 1 PROPOSE_DELETE (the unpublished API test product).
- Each action has before/after, required files (bytes, sha256, file test), evidence and rollback.
- A per-product thin review covers the rest: 9 PROPOSE_UNPUBLISH-or-reprice (under 10 words/$), 6 HOLD expand-or-reprice, 2 HOLD unverifiable (ZIP / xlsx), 1 KEEP, 1 KEEP unpublished.

**Founder queue.** Each action was filed individually in `data/founder_approvals.jsonl` via `gf_ops/founder_approval.py` (13 new; GPSR already pending as `105b50b9f45f`).

**Correction item `0572d147f1b5`.** The pending item `fd394165c746` would unpublish `iaiyt`, the $155 EU AI Act toolkit, on the false "no file" signal. iaiyt has 2 files. That item's status was **not** changed; only the founder decides it.

### Ledger reconciliation (proposal; nothing written)

| State | Proposed | Evidence | Basis |
|---|---|---|---|
| SIGNAL_RECEIVED | founder decides | — | founder-only by definition |
| PUBLISH_STATE_VERIFIED | true | Gumroad API: 79 published of 82 (2026-10-22) | OBSERVED |
| PUBLIC_PAGE_VERIFIED | true | HEAD on all 79 public pages: 79 × HTTP 200 (`reports/GUMROAD_PUBLIC_PAGES_2026-10-22.json`) | OBSERVED |
| CHECKOUT_VERIFIED and later | false | no transaction attempted; 0 sales | OBSERVED (zero confirmed by API) |
| Revenue | $0 | `sales_count` 0 on every product; `/v2/sales` empty | OBSERVED; listed prices are not revenue |

**Consequence (DERIVED).** Recording these would move `highest_verified_index` to 2, which opens the `/generate-book` and `/api/distribute` gates. That is why it stays a founder decision.

## Checkpoint 3 — ledger reconciliation and gate safety (same day)

### Facts re-verified (OBSERVED, 2026-10-22 20:45 UTC, read-only)

- **Gumroad API:** 82 products, 79 published, 3 unpublished.
- **Sales:** `/v2/sales` returns 0 records; `sales_count` sum is 0; `sales_usd_cents` sum is 0.
- **Public pages:** HEAD returned 79 × HTTP 200, covering exactly the set of API-published products.
- **Sources:** `reports/GUMROAD_FACTS_RECHECK_2026-10-22.json` and `reports/GUMROAD_PUBLIC_PAGES_2026-10-22.json`.
- **VERIFIED_REVENUE = $0.**

### Definitions (OBSERVED in code)

| Term | Definition | Consequence |
|---|---|---|
| `KDP_LULU_RECEIVED` | **Does not exist** anywhere in the code, data, docs or git history (`git log -S`). UNKNOWN term | Nothing to set. The founder-only first state that does exist is `SIGNAL_RECEIVED` |
| `SIGNAL_RECEIVED` (state 1) | "Founder sent the 'Gumroad product published' signal" (`commercial_reality.verify_signal_received`, default source `founder_directive`) | Founder-only. Not inferred from technical evidence; left **false** |
| `PUBLISH_STATE_VERIFIED` (2) | Publish state verified via external check | Evidence: API, 79 published |
| `PUBLIC_PAGE_VERIFIED` (3) | Public page visible | Evidence: 79 × HTTP 200 |
| `CHECKOUT_VERIFIED` (4) and later | Buy button functional, transaction, payment, delivery, customer evidence, repeatability | No evidence: no transaction attempted, 0 sales. All **false** |
| `highest_verified_index` | Index of the last state in an unbroken run from state 1 (`_get_highest_verified_index`) | With state 1 false, it is -1 regardless of later states |
| `check_governance_gate()` | Verdict from `current_state`; "distribution" and "generation" are blocked only at None/SIGNAL_RECEIVED; scale_level stays 0 until REPEATABILITY_VERIFIED | Unchanged |
| `POST /generate-book` | Blocked if `reality.scale_level==0 && commercial_proof=='UNKNOWN'` **or** index < 1 | **Stays blocked even at index 2**, because of `config/reality.json` |
| `POST /api/distribute` | Blocked if `hard_stop` or index < 1, including dry runs | Opens at index ≥ 1 |

### Reconciliation applied (scenario A)

**Applied.** States 2 and 3 were recorded through `commercial_reality.update_evidence` with the evidence above. Backup: `data/commercial_reality.json.bak-20261022_reconcile`.

**Proven first on a temp copy, then observed on the real ledger:**

- `highest_verified_index` = **-1** (unchanged);
- `current_state` = None (unchanged);
- governance verdict = HOLD, scale_level 0 (unchanged);
- monitor classification: NO_TRANSACTION_OBSERVED.

**No gate changed. Rollback:** `copy data\commercial_reality.json.bak-20261022_reconcile data\commercial_reality.json`.

**Scenario B (DERIVED by execution on a temp copy only).** Adding the founder's `SIGNAL_RECEIVED` would make the index 2. That opens `/api/distribute`; `/generate-book` stays blocked by `config/reality.json`.

### Gate safety finding (OBSERVED)

**Where `FACTORY_LIVE_PUBLISH` is enforced.** Only in `channels/write_gate.py`, which only `channels/gumroad_publisher.py` uses. `distributor.distribute(dry_run=False)` does not check it for the other arms.

**What else stands between a live call and a real publish:** `channels/publish_protection.py` (a first publish of a new arm needs founder approval; Gumroad, Etsy, Payhip and Paddle are "proven" arms that publish autonomously), the quality gate, and arm credentials.

**Arm status now:** gumroad ready, paddle ready (its API key gets 403), x ready (new arm, so founder-gated; credits depleted, 402), payhip, etsy and kdp unavailable.

**Consequence (DERIVED).** Today the `/api/distribute` ledger gate is the only global stop on a live push to Paddle through that route. Raising the index removes it.

### Decision per gate

| Gate | Decision | Evidence |
|---|---|---|
| Ledger fact reconciliation (states 2–3) | **PASS**; applied, index unchanged | API + 79 × 200; temp-copy proof |
| `SIGNAL_RECEIVED` | **HOLD**; founder-only | no founder signal on record |
| `/generate-book` | **BLOCKED**; stays blocked even after a founder signal, by `config/reality.json` | server.js ≈4652 |
| `/api/distribute` | **BLOCKED**, and must stay so until the proposal below | server.js ≈4909 |
| CHECKOUT_VERIFIED and later | **BLOCKED**; no evidence | 0 sales; no transaction |
| Live Gumroad writes | **BLOCKED** by `write_gate` (`FACTORY_LIVE_PUBLISH=false`) | channels/write_gate.py |

**The evidence supports reconciliation only.** A separate proposal to change gate behavior would first need defense in depth: make `distributor.distribute(dry_run=False)` require `FACTORY_LIVE_PUBLISH` or a single-use scope for **every** arm, the same rule `write_gate` applies to Gumroad. That change touches 14 test files that exercise live distribution with mocks, so it is not part of this reconciliation. Only after it lands should the founder be asked for `SIGNAL_RECEIVED`.

### Tests (executed 2026-10-22)

**Broad regression: 1,449 passed, 18 failed (880 s).** Scope: the 68 test files that touch product families, builders, packaging, orchestrator, cohort workbooks, file testing or the portfolio engine.

**Failures caused by this work: 1.** `test_product_manifest` expected the converted-family set without `spreadsheet_systems`. The test now records the new manifest. Rerun: **92 passed** across all directly affected files.

**Failures not caused by this work: 17 (OBSERVED).**

- **13 in `test_run_identity.py` / `test_durable_telemetry.py`.**
  - Both test files are untracked, and so is `orchestrator/run_id.py`.
  - The tests call `run_cycle(telemetry_path=…)` and `ExecutionResult(run_id=…)`, which the committed code does not accept (TypeError).
  - This is in-progress parallel work whose tests are ahead of its code.
- **4 in `test_backup_regimen.py`** (untracked).
  - Its protected-file hash for `finance_data.json` no longer matches.
  - That file has an uncommitted change dated 2026-10-21, not made in this session.

None of these were modified.

## First-dollar rule: what is actually blocked

| Activity | Blocked? | Where |
|---|---|---|
| Research, opportunity discovery | No | — |
| Local product creation via scripts/cohort builders | No | Gate only covers `POST /generate-book` |
| QA, packaging, listing preparation, this release gate | No | — |
| Distribution via `POST /api/distribute` | **Yes, including dry runs** | `server.js` ≈4909 |
| Creation via `POST /generate-book` | Yes | `server.js` ≈4652 |
| Live publication | Gated separately (`FACTORY_LIVE_PUBLISH=false`, founder gates) | — |

Both gates read a ledger that can never advance (no caller of `commercial_reality.update_evidence`); see `reports/COMMERCIAL_RECONCILIATION_2026-10-22.md` §2.

**Narrow proposal (not applied):**

1. Exempt `dry_run` from the `/api/distribute` gate.
2. The founder records the API-verified publish and public-page states.
3. Keep the doctrine.
4. Route every future product family through `release_gate` before it may be called ready.

## Capability and payout matrix

- **Channels:** `business_development.PLATFORM_REGISTRY` (19 platforms, sourced).
- **Payout:** `data/affiliate_algeria_evidence.json`.
- **Selling-side facts:**
  - Gumroad: the only verified live channel (79 listings).
  - Paddle: API key gets 403 on every call.
  - Canva Creators, Notion Marketplace, Creative Market, Envato (author side), Figma community: seller eligibility from Algeria and payout UNKNOWN; not researched this round.

## Tests (executed 2026-10-22)

- `tests/test_release_gate.py`: 11 passed.
- Every test file depending on the reused modules (9 files): **153 passed**, 0 failed.

## Founder-only decisions

1. **Live Gumroad edits.** For `fetmu` and `vkqogv`: attach the workbook and replace the listing sentence (packages above).
2. **Human rights/policy review of the two packages.** A review records the reviewer and basis. The gate will not move to READY_FOR_AUTHORIZATION without it.
3. **The §2 proposals** on the ledger and dry-run gate.

## Next resumable task

Run `release_gate.evaluate()` over the other 9 reviewed (KEEP) products, using their local files. That needs a slug → local-file mapping: the catalog `files` field lists types, not paths.

Then fix `spreadsheet_systems` so it builds a real workbook via `cohort_workbook.build_xlsx`, instead of a PDF about one, before any new spreadsheet product is made.

**Checkpoint:** this file plus `data/release_gate_state.jsonl`.
