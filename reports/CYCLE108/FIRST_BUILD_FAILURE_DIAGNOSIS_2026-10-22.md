# First-Build Failure Diagnosis - 2026-10-22 (Cycle 108, Phase 5)

Two tracked tests in `tests/test_first_product_build.py` fail. Both are
**data/provenance failures, not code defects**. No business evidence was
created, no product was regenerated, and no ledger was written.

Test result: `2 failed, 12 passed`.

## Failure 1 - `TestProductGenomeIntegration::test_genome_finds_registered_product`

```
build_product_genome("PROD-5214fb83a464299d") -> {"found": False, ...}
reason: no real books/_generation_log.jsonl record exists for production_id=...
```

Evidence:

- Current `books/_generation_log.jsonl`: **5,917 rows, 0 hits** for the ID.
- HEAD version of the same file: **5,053 rows, 0 hits**.
- `git log -S "PROD-5214fb83a464299d" -- books/_generation_log.jsonl` returns
  no commit: the ID was never in the tracked log.
- The product files exist:
  `books/legal_case_research_automation_playbook.{md,pdf}`.
- `build_legal_playbook.py` does append a real generation record (with
  `product_candidate: True`, `validated: False`) to `GEN_LOG`. So a local run
  of that builder would have created the record.

Conclusion: the artifact in this checkout was produced without the local
generation-log side effect (built elsewhere/copied in), or the log was
replaced afterwards. The production code already returns an explicit,
disclosed `reason`; there is nothing to repair in the genome logic.

Do **not**: synthesize a generation record, copy a hash-only row, or set
`found: True` manually. That would fabricate provenance for a product whose
real build history is not recorded here.

Honest resolution for the test's owner: either (a) re-run the real builder in
a controlled location and let it produce the record, then verify the artifact
against it, or (b) convert the test to a deterministic temp-log fixture that
proves genome lookup works, and keep a separate explicit test documenting
that the real artifact currently has no local provenance.

## Failure 2 - `TestEvidenceSeparation::test_market_evidence_not_gf_sale`

```
AssertionError: 0 != 2   (line 74)
```

Evidence:

- `data/decisions.jsonl`: **3,097 decisions, 0** with
  `evaluation_snapshot.payment_evidence`.
- The test looks up a lowercase niche string; recorded decisions also use
  title case, so the lookup can miss independently of the missing field.
- The canonical ledger `data/market_evidence.jsonl` has **12 real rows**,
  including **3** for `Legal Case Research Automation System for Solo
  Attorneys` (2 `freelancer_agency_pricing`, 1 `complaining_review`).

Conclusion: the decision-snapshot field the test asserts on is **schema
drift/stale data**; the evidence moved to (or always lived in) the canonical
ledger, which the test never reads. The invariant the test protects
(market pricing evidence is REAL but is never a Galaxy Forge sale) still
holds and is already enforced by `reconcile_payment_evidence.py`.

Do **not**: backfill `payment_evidence` into decision snapshots, duplicate
ledger rows, or change the assertion to a smaller number just to pass.

Honest resolution for the test's owner: read the real ledger filtered
case-insensitively by niche, assert every record classifies REAL and
`is_sale == False`, and assert `reconcile_niche(...)` returns
`verified_real_sales == 0` / `verified_real_revenue == 0`. A temp fixture is
also acceptable for the classification half; a fabricated ledger is not.

## Why no edit was made

Both files are untracked and parallel-owned:

```
?? tests/test_first_product_build.py
?? product_genome.py
?? reconcile_payment_evidence.py
?? build_legal_playbook.py
```

Editing another owner's untracked test would hide a real provenance gap and
could be overwritten. The two failures remain visible and documented.
