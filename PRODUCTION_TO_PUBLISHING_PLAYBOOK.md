# Production to Publishing Playbook

Canonical, current procedure for taking a Galaxy Forge digital product from build
through to a verified first sale. Created in Cycle 102 because no single
canonical procedure existed: `PUBLICATION_CHECKLIST.md` is a July one-product
checklist for a different product, `LAUNCH_CHECKLIST.md` is Paddle-era, and
`LISTING_MANAGEMENT.md` is a phase report. Those files are kept for history;
this file supersedes them **for the procedure itself**.

Every claim in this playbook is tagged with how it is known:

- `OBSERVED` — a real record on disk, a real command output, or a real live page.
- `DERIVED` — computed by a documented rule from observed inputs.
- `INFERRED` — a reasonable conclusion from indirect evidence; may be wrong.
- `UNKNOWN` — no evidence exists. Never fill this in with a guess.

## The seven release states

A product advances through these states in order. They are **not** interchangeable:

| # | State | Means | Does NOT mean |
|---|-------|-------|---------------|
| 1 | `BUILD_COMPLETE` | Artifacts exist and are byte-identified. | Anything about quality. |
| 2 | `QA_PASS` | The quality gate approved the artifacts on their recorded hashes. | That the product is live. |
| 3 | `READY_FOR_AUTHORIZATION` | Gate passed, price derived, listing package prepared. | That anyone authorized publishing. |
| 4 | `UPLOAD_COMPLETED` | The file was actually uploaded to a live channel. | That it is publicly visible. |
| 5 | `PUBLIC_LISTING_VERIFIED` | A public URL was fetched and shows the product. | That anything can be bought. |
| 6 | `CHECKOUT_VERIFIED` | A live checkout URL exists for the product at the intended price. | That anyone bought it. |
| 7 | `FIRST_SALE_VERIFIED` | A real, externally recorded, paid transaction exists. | It does not guarantee profit. |

Never collapse adjacent states. An upload is not a public listing; a public
listing is not a checkout; a checkout is not a sale.

The release state of every batch-12 product is reconstructed from real records
by `operational_history.py` and written to `data/operational_history.json`
(plus an append-only `data/operational_history.jsonl`). Regenerate with:

```
python operational_history.py --write --check
```

Authority for a single product is `reports/<id>/RELEASE_BASELINE_*.json`; the
human-readable companion is `reports/CYCLE*_<id>_VERIFICATION_*.md`. When they
disagree with `operational_history.py`, treat the disagreement as a defect and
fix the record, not the story.

## Stage 0 — Preconditions

- Work happens in the repository; nothing reaches a live channel by accident.
- `FACTORY_LIVE_PUBLISH` must remain `false`. Publishing is a separate,
  product-specific act, never a side effect of a build or a test (`OBSERVED`:
  `config/reality.json` and the runner read this flag).
- No spend, no paid dependencies, no auth bypass.

## Stage 1 — Build (`BUILD_COMPLETE`)

1. Generate the artifacts with the real builders:
   - Workbook: `scripts/build_batch12_xlsx.py` — call the specific product
     function (for batch 12 product ten: `b12_010_grant_pipeline()`), **not**
     the `makers` loop at the bottom of the file, which rebuilds everything.
   - Guide PDF: the shared `scripts/build_batch12_pdfs.py` regenerates every
     batch-12 PDF, so rebuilding one product rewrites all of them. Reportlab
     and openpyxl embed timestamps, so bytes change between builds even when
     content does not (`OBSERVED`, Cycle 97 baseline comments).
   - Cover: `scripts/generate_all_covers.py` (`OBSERVED`). `scripts/generate_cover.py`
     is broken and deprecated; do not use it.
2. Record the artifacts: byte size and SHA-256 for every file, in
   `reports/<id>/MANIFEST_<date>.json`.
3. Never run `scripts/build_batch12_pages_qa.py`'s `build_pages()`; it rewrites
   every `customer_site/*.html` page, including ones other automations keep
   editing (`OBSERVED`, code comment at the function).

## Stage 2 — Quality gate (`QA_PASS`)

Run the real gate and record the numbers. The gate is a composite:

```
quality verdict == APPROVED
AND economics['approved'] == True
AND market_realism_check(...).ok == True
```

- Thresholds: core value 70, content quality 70, market reality 65.
- Economics constants: `WORDS_PER_DOLLAR` 100, `REWRITE_MARGIN` 15,
  `KILL_BELOW` 40.
- The page policy caps price at `min($1.00 x pages, $15.00)`. A 17-page guide
  therefore caps at $15.00 no matter what comparables sell for. Do **not**
  pad the guide to raise the cap.
- Write `reports/<id>/GATE_FINAL_<date>.json`. Record the verdict honestly;
  the record shapes differ between products (`verdict` may be nested under
  `gate_at_*` keys), so read the file rather than assuming.
- `reports/<id>/QA_FACTS_<date>.json` holds Brand DNA, Executive Safety, PDF
  integrity, and cover facts.
- A workbook must also pass Stage 2b.

### Stage 2b — Native workbook QA (required for any `.xlsx`)

A value-only check cannot see a formatting defect: Excel will happily display
`100%` for a count, `$1` for a rate, or `1900-01-01` for the day count `1`
(Cycle 101 found seven exactly like this). Any workbook that ships must be
recalculated by a real spreadsheet engine and re-checked with:

```
python native_workbook_qa.py --product B12-010 --write-evidence --json
```

- The engine is Excel via COM: `New-Object -ComObject Excel.Application`
  (Excel 16.0 build 19127 here). There is no `win32com`/`pywin32` in this
  environment and no `soffice`, so PowerShell COM is the only real engine.
  If Excel is unavailable, report the limitation; never substitute a
  Python-only recalculation and call it verified.
- The probe always opens a **temporary read-only copy** and never saves over
  the release artifact.
- Engine gotcha (`OBSERVED`): setting `$excel.Calculation` before
  `Workbooks.Open` throws `HRESULT 0x800A03EC`. Set it after the open.
- Recorded evidence: `reports/<id>/WORKBOOK_QA_<date>.json` with verdict,
  critical count, engine version, and the artifact hash it checked.
- `scripts/check_b12_integrity.py` fails if a registered workbook has no
  recorded `PASS` or if the recorded hash no longer matches the file about to
  ship. Re-run it after any workbook rebuild.
- Coverage honesty: the existing workbook has 427 formulas; the probe reports
  how many it recalculated (148 are on the three sheets scanned in this
  configuration). Never present the smaller number as full verification.

## Stage 3 — Pricing rule (`READY_FOR_AUTHORIZATION`)

- Choose the **highest price that passes every mandatory gate**. Test the
  candidate set and record each result in `reports/<id>/GATE_FINAL_*.json`
  under `price_history` and in `RELEASE_BASELINE_*.json`.
- A price rejected by one check (for example the page ceiling) is a rejected
  candidate, not a withdrawn final price. Record which is which.
- The price is `DERIVED`, not `founder_approved`, until the founder authorizes
  that specific product. `founder_decision` stays empty until then.
- Verify takedown/withdrawal of a previously published price explicitly; do not
  assume a superseded price was withdrawn (see the Cycle 100 correction in
  `reports/OPERATIONAL_LEARNING_BASELINE.md`).

## Stage 4 — Authorization (separate gate)

- Publishing requires a **product-specific** founder authorization phrase.
  A general approval, a prior cycle's approval, or a ready listing package is
  **not** authorization.
- Record the phrase as received. Never compose, infer, or backfill it. Until it
  exists, `MANIFEST.authorization_phrase` stays `null` and the state stays
  `READY_FOR_AUTHORIZATION`.
- Platform credentials are a *second*, independent gate: even a fully authorized
  product cannot publish without a live channel credential configured in this
  environment. Preparation and access are separate from authorization.

## Stage 5 — Upload (`UPLOAD_COMPLETED`)

- Only via the real publishing path (`channels/`, `src/publish/`) with the
  authorization phrase present and `FACTORY_LIVE_PUBLISH` handled explicitly.
- Never part of a build, a test, or a QA run.
- Record the upload result (id, timestamp, target) — not just "uploaded".

## Stage 6 — Public listing (`PUBLIC_LISTING_VERIFIED`)

- Fetch the public URL and store the response: HTTP status, the product title
  as actually served, the price as actually served, and a content check.
- Compare the served bytes/hash of any downloadable file against the release
  artifact. A listing whose served file differs from the artifact is a defect.
- Exposure of a pricing page is not a payment path: a 403/404 or a
  bot-protection page means "blocked", never "verified".

## Stage 7 — Checkout (`CHECKOUT_VERIFIED`)

- A live checkout URL exists for this product at the intended price and
  currency. Record the URL, price, and currency.
- `OBSERVED` for published products in this batch: B12-001
  `https://aekraft.gumroad.com/l/blayvb` at $14.99; B12-003 at $8.00; B12-004
  at $11.99. All three had zero sales at last check.
- Purchasing on the founder's own behalf to force a state is not verification
  and must not be done silently.

## Stage 8 — First sale (`FIRST_SALE_VERIFIED`)

- Requires a real external transaction: a paid record in the sales source,
  reconciled into the ledger. `data/sales_ledger.jsonl` currently contains only
  publication attempts and zero sales; `finance_data.json` has an empty `sales`
  list (`OBSERVED`).
- Verified revenue today is $0.00. Never mark this state from a checkout
  existing, a test purchase, or a projection.

## Operating rules

- Independent, reversible, zero-cost work only.
- No spend, no paid dependencies, no auth bypass, no external publish, price
  change, or listing edit without explicit product-specific authorization.
- Label every claim `OBSERVED` / `DERIVED` / `INFERRED` / `UNKNOWN`.
- When a check cannot run, record the limitation and the reason. A missing
  capability is not a pass.
- Keep the automation honest: `scripts/check_b12_integrity.py`, the bounded
  test groups, and `operational_history.py --check` are the standing guards.
