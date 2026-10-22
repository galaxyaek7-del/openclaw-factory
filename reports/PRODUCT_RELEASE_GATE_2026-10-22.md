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
