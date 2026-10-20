# GF-6H — Continuation Report (listing assets, price finding, probe 4)

**Reported at:** 2026-10-20T14:19:55+01:00
**Window:** opened 2026-10-20T13:31:13+01:00 · elapsed 48m42s · **remaining 5h11m18s**
**Base commit at start:** `b09318f` · **branch:** `main`
**Second product built this continuation:** **no** — four probes, none selected (one deferred on capacity, three rejected on evidence)
**B13-001 published:** no · **price changed:** no · **new spend:** $0.00

---

## 1. B13-001 claims verified against artefacts

| Claim | Verification | Result |
|---|---|---|
| Workbook built | `books/batch13/B13-001_renovation_allowance_control.xlsx` | 23,871 B, sha256 `028b9ed14e80ddb8…` |
| Guide built | `books/batch13/B13-001_renovation_allowance_control_guide.pdf` | 19,861 B, sha256 `53c65af902c99d0e…` |
| 23 tests exist and pass | `python -m pytest tests/test_b13_001.py -q` | **23 passed in 1.62s** |
| Workbook opens clean, 415 formulas | `python native_workbook_qa.py --product B13-001 --json` | **PASS, 0 critical, 0 warning, 415 formula cells**, 9 sheets |
| Guide is real and deep | `reports/B13-001/GUIDE_INSPECTION_2026-10-20.json` | 7 pages, 3,802 gate-words, 16 headings, 0 placeholder/mojibake |
| Gate approved | `reports/B13-001/GATE_FINAL_2026-10-20.json` | core 100 / content 100 / market 70, state `QA_PASS_AT_19_USD_AWAITING_LISTING_AND_PUBLICATION_AUTHORIZATION` |
| Evidence set exists | `reports/B13-001/` | 5 JSON files + cover + new listing payload |

Every claim checked out. Nothing needed correcting.

---

## 2. The $19 versus $7 question — resolved, with arithmetic

`economics.evaluate()` was run directly this round; the matrix is in the listing payload.

| Price | Platform | Pages | Approved | Net | Floor | Realistic | Suggests |
|---|---|---|---|---|---|---|---|
| $19 | gumroad_digital | 7 | yes | $17.10 | $2.50 | **no** | $7.00 |
| $19 | gumroad_premium | 7 | **no** | $17.10 | $25.00 | yes | $19.00 |
| $19 | gumroad_digital | 29 | yes | $17.10 | $2.50 | **no** | $15.00 |
| $19 | gumroad_digital | **30** | yes | $17.10 | $2.50 | **yes** | $19.00 |
| $27.99 | gumroad_premium | 7 | yes | $25.19 | $25.00 | yes | $27.99 |

What this actually means:

- The $7 figure is not a hard cap. It is `market_realism`'s *suggestion* under the global `$1/page` default, which applies to `gumroad_digital`.
- `market_realism` is **advisory** inside `evaluate()` — `approved` stays true. So $19 is not "rejected"; it is approved with a warning that it is priced above what 7 pages can credibly justify.
- A second, independent ceiling binds harder: any book under 30 pages is capped at **$15 absolute**. This is why raising the guide to 29 pages changes nothing, and why the threshold is 30, not 19.
- `gumroad_premium` already carries a $5/page override ($50 under-20-page cap), so $19 is *realistic* there — but its **$25 net floor** rejects $19. Premium needs $27.78 or more.

**No live setting was changed.** The price remains $19.00, still `PROPOSED_NOT_AUTHORIZED`.

Three honest options, recorded in the payload:

1. Grow the guide to 30+ pages, keep $19. (Recommended: improves the product, not the arithmetic.)
2. List at $27.99 on premium. (Passes both checks today; 47% price rise on thin content.)
3. Leave it. (Then it lists with an approved-but-unrealistic warning, which is what the current gate already discloses.)

This is now a founder price decision with numbers attached, not an open question.

---

## 3. What was built this continuation

B13-001 was structurally unlistable: no cover, no listing payload, no paste-ready copy. That gap is now closed, locally.

| Artefact | Path | Verified |
|---|---|---|
| Listing cover | `reports/B13-001/B13-001.png` | 1280×720, price-agnostic (no badge to go stale) |
| Listing payload | `reports/B13-001/LISTING_PAYLOAD_2026-10-20.json` | 0 problems, file hashes recomputed |
| Human-readable payload | `reports/B13-001/LISTING_PAYLOAD_2026-10-20.md` | same facts, one page |
| Paste-ready copy | `drafts/b13_001_listing_copy.txt` | passes `brand_dna.validate_customer_facing_text` |
| Builder | `scripts/build_b13_001_listing_assets.py` | idempotent, local-only |
| Guards | `tests/test_b13_001_listing_assets.py` | 11 tests |

The payload states `published: false`, `gumroad_call_made: false`, and
`state: LOCAL_READY__AWAITS_FOUNDER_LISTING_AUTHORIZATION`. It embeds the real
file hashes, the real guide/workbook verification citations, the economics
matrix, and the exact minimal authorization needed.

The listing copy describes only what exists: 9 sheets, 415 formulas, no macros,
a 7-page guide, and an explicit "no sales recorded yet, no reviews" line.

One guard is worth naming: `test_builder_source_cannot_publish_or_spend` parses
the builder's AST and fails if it ever gains a network import or an HTTP call.
The first draft of that test used a substring match and failed on the builder's
own docstring promise — fixed to check the parsed tree instead of raw text.

---

## 4. Discovery: four probes, three rejected, one deferred

| # | Candidate | Score | Verdict | Decisive evidence |
|---|---|---|---|---|
| 1 | Security-deposit tracker | 17 | REJECTED | Quire Paper sells the same ledger at $12; DepositBackr gives proration away free |
| 2 | CAM reconciliation / lease audit | 17 | REJECTED | CapVeri ships a complete formula template free; Sheet Chief published a 5-sheet tracker 2026-08-13 |
| 3 | Subcontractor COI tracker | 16 | REJECTED | Six free templates, one a 51-column 7-sheet engine |
| 4 | EUDR compliance register | **19** | **DEFERRED** | Clears the gate; not built for capacity/quality reasons |

Probe 4 is recorded separately in `reports/CYCLE106/DISCOVERY_2026-10-20_EUDR_PROBE.json`
because it produced a finding that matters beyond the product decision:

**The EUDR deadlines moved.** Large/medium operators now 30 December **2026**;
micro/small 30 June **2027**; micro/small already under the EUTR 30 December
2026. Regulation (EU) 2025/2650 also shifted due diligence to the first placer —
downstream traders no longer submit their own statement. At least one paid
vendor's own FAQ still carries the superseded SME date. The stale figure was in
my working assumptions and would have shipped as a defect.

Key sources: the Commission's own EUDR topic page, the Commission report to
Parliament and Council, the Article 9 guidance notice, and polygon-one's
Annex II analysis updated 2026-10-18 (Annex II point 4 deleted; five items
remain, with the prescribed declaration wording).

Why it was not built despite clearing 18/25: a compliance product must be right
on scope, role split and retention, and that needs Annex I commodity
verification per commodity before writing a claim. Writing it from memory in
this window would risk exactly the stale-date failure just described. The score
is recorded honestly as passing; the deferral reason is capacity and quality,
not commercial merit.

---

## 5. Differentiation verdict across the whole catalogue

Checked against B12-001 through B12-010 and B13-001. All four probes are
distinct from the catalogue in substance — none is a rename or repackage. The
failure in probes 1–3 is external: a free, formula-complete incumbent does the
same job.

This remains the round's main structural finding: single-purpose small-business
trackers are unviable as paid products because SaaS vendors publish complete
templates as acquisition funnels. The lanes that survive are assembled
interpretation of a dated obligation, a decision the buyer cannot make alone,
or distribution/brand.

---

## 6. Test and gate runs, exact commands

| Command | Result |
|---|---|
| `python -m pytest tests/test_b13_001.py -q` | 23 passed in 1.62s |
| `python -m pytest tests/test_b13_001_listing_assets.py -q` | 11 passed in 1.08s |
| `python -m pytest tests/test_b13_001.py tests/test_b13_001_listing_assets.py tests/test_native_workbook_qa.py tests/test_doctrine_layers.py -q` | **104 passed in 6.46s** |
| `python native_workbook_qa.py --product B13-001 --json` | PASS, verdict `PASS`, findings `[]`, 0 critical / 0 warning |
| `python scripts/check_b12_integrity.py` | `B12 integrity: OK (10 prep items, 5 baselines)` |
| `python scripts/check_doctrine.py` | ok, 8/8 checks, 53 doctrine tests |

Pre-existing failures elsewhere in the suite are unchanged and are not claimed
as green; none of them touch B13-001 or the new assets.

---

## 7. Repository and publication state

- Branch `main`; base `b09318f`; this continuation's commit follows it.
- Working tree was already dirty with 2,134 parallel-track entries; nothing
  unrelated was staged.
- **Publication: still blocked.** `FACTORY_LIVE_PUBLISH=false`, Gumroad auth
  state stale, no active scope, six founder approvals `PENDING`, and
  `create_product`/`enable_product` are outside the scopable operation set.
- **Revenue: unchanged.** Zero sales, zero verified external transactions. No
  sale is claimed anywhere in this report or in the payload.
- **B13-001 price: unchanged** at the proposed $19.00.

Minimal authorization to move it forward: set `FACTORY_LIVE_PUBLISH=true` for
the run and complete a fresh `gumroad_auth_watch.poll()`, after choosing one of
the three price options above.

---

## 8. Remaining known gaps

1. B13-001 has no entry in `data/product_batch_12.json` (the registry that
   doctrine and catalogue tooling hardcode), so it is invisible to those views.
   Deliberately not faked with a half-registry file; disclosed in the payload.
2. No customer-facing page for B13-001. Not required for Gumroad listing.
3. A second product does not exist. Four probes, no selection.
4. The 30-page guide expansion is not started. It is the recommended fix for the
   price bind and the largest remaining value item on this product.
