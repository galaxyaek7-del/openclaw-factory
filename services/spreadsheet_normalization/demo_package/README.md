# Micro-B2B demonstration: catalogue merge clean-up for small online sellers

Status: **demonstration only.** No customer has used this service. No inquiry has been
received. Nothing here is published. All data is synthetic.

Reproduce: `python services/spreadsheet_normalization/demo_package/build_demo.py`
(writes `input_messy.csv`, `output_clean.csv`, `qa_report.json`, `before_after.md`; the
clean output is byte-identical across runs).

## 1. Target customer

A one-to-five-person online shop (Etsy, Shopify, a market stall with a web shop) that merges
a supplier price list with its own exports before a price update or a platform move.
INFERRED from the engine's design; no customer interview has been done.

## 2. Problem

Merged exports mix date styles (US, EU, ISO), currency formats (`$8.50`, `€8,50`), stray
spaces, case differences in SKUs, exact duplicates and empty cells. Spreadsheet tools fix
some of this, but silently: a "clean" file can contain a swapped day and month, or
dollars and euros in one column.

## 3. Offer

Send one CSV/XLSX export (up to 5,000 rows, one sheet). Receive:
- the cleaned file (`output_clean.csv` here);
- a QA report stating every change and everything that needs a human decision: dates
  converted, ambiguous dates left as written, impossible dates flagged, exact duplicates
  removed, SKUs that repeat across rows, columns that mix currencies, rows with missing values.

The engine never guesses: an ambiguous date or a repeated SKU is reported, not resolved.

## 4-6. Example input, before/after, sample deliverable

`input_messy.csv` (13 rows from three synthetic sources) -> `output_clean.csv` (12 rows) +
`qa_report.json`. Summary in `before_after.md`:
- 9 dates converted to ISO; `03-04-2026` and `04/05/2026` kept as written (could be either
  day or month first); `2026-02-30` kept and flagged (no such date);
- 1 exact duplicate removed;
- AB-1001 and AB-1002 appear in several rows: reported for the seller to resolve;
- the price column held both `$` and `€`: reported, because the cleaned numbers alone
  would hide it;
- 2 rows with a missing value.

## 7. Scope

Included: structure and header clean-up, whitespace, SKU case, ISO dates, numeric amounts,
exact duplicates, the QA report above, one revision if the QA report shows a misread column.
Excluded: deciding which of two conflicting rows is right, currency conversion, bookkeeping,
tax or financial advice, writing into any system, files with credentials (rejected by the
engine's secret scan), personal data beyond what a product catalogue needs.
Human review: the founder checks every delivery before it is sent.

## 8. Pricing hypothesis (UNKNOWN until a buyer answers)

| Evidence | Value | Class |
|---|---|---|
| Fiverr "excel data cleaning" gigs | mostly from $10-$50, $15 most common; some $100-$200 | OBSERVED, Fiverr category and gig pages, read 2026-10-29 |
| This service's differentiator | a QA report that never hides an ambiguous date, a repeated SKU or a currency mix | DERIVED from the engine |

Hypothesis: **$29 per file up to 5,000 rows** (above the $15 entry gigs because of the QA
report, below the $100+ end). The earlier $49/$79/$149 ladder in `../offer.md` has no buyer
evidence either; this demonstration replaces neither until one is tested.

## 9. Landing page draft

`drafts/micro_b2b/catalogue-cleanup.html` (not under `customer_site/`, so the site
publisher cannot publish it). Needs: an intake that reaches the founder (see the shared
intake work) and founder approval.

## 10. Case study (demonstration)

`case_study_DEMONSTRATION.md`: the synthetic run above, labelled as a demonstration
throughout. It is not a customer result.

## 11. Validation plan

1. Founder approves the page and the intake.
2. Page goes live; one post in a channel where small sellers ask about spreadsheet
   problems (seller forums or LinkedIn; community rules permitting), tracked link.
3. Offer: the first three files cleaned free in exchange for a two-question reply
   ("did the QA report catch something you would have missed?", "would you pay $29?").

## 12. Success / failure

- Continue: at least 1 in-scope file submitted within 30 days of a live page, and at least
  one "would pay" answer among the first three.
- Modify: inquiries arrive but are out of scope (e.g. multi-sheet accounting files):
  re-target the offer.
- Stop: no in-scope submission within 90 days of a live, measured page.
