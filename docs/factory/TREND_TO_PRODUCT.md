# Trend-to-Product Intelligence Engine (2026-10-29)

Package: `trend_to_product/`. Tests: `tests/test_trend_to_product.py` (36) and the
`trend-to-product` case in `tests/test_ceo_command_center.js`. Dashboard: CEO dashboard,
section "من الاتجاه إلى المنتج" (`lib/ceo_command_center.js::trendToProduct`, data
`data/trend_to_product_state.json`). First research run: `scripts/trend_research_20261029.py`.

Pinterest is a source of market signals and inspiration, never of assets. Nothing in the
package fetches, publishes, prices, schedules or spends (pinned by the
`AuthorizationBoundary` tests). Spend: $0. `FACTORY_LIVE_PUBLISH` unchanged.

## Why a new package

The factory had demand sensing (`lib/demand_sensing.js`: Stack Exchange and Ask HN
questions), market evidence for paid products (`market_evidence.py`), a manual verification
ledger (`multi_source_intelligence/manual_verification.py`) and the product registry. None
of them records per-claim provenance with access method and permitted use, distinguishes
official data from estimates, scores with explicit missing evidence, screens rights, or
links an idea to a product's QA, approval and outcome. The package adds only that, and
reuses:

| Need | Reused |
|---|---|
| Existing products, sales | `data/product_registry.json` (authoritative registry) |
| QA record | each product's manifest `qa` block |
| Approval | `data/publication_approvals.json` |
| Brand/licence claim scan | `executive_quality_gate.check_copyright_trademark_risk` |
| Fake-urgency scan for listing copy | `executive_quality_gate.check_fake_urgency_risk` |
| Production pipelines named per format | `book_generator.py`, `books/_batch14_src`, `native_workbook_qa.py`, `source_grounding.py`, `services/spreadsheet_normalization/`, `kids_studio/` |
| Business arms | T1 arms from `business_arms.py` (`docs/factory/ARM_TAXONOMY.md`) |

## Chain and IDs

`SRC-` source → `SIG-` signal → `OPP-` opportunity → `SPEC-` specification → registry
`internal_id` → manifest QA → publication approval → listing (registry URL) → observed
outcome (registry sales). Stored append-only in `data/trend_to_product/*.jsonl`. Product,
QA, approval, listing and sales are read from their own sources, never copied.

## Rules enforced in code

- A source needs an http(s) URL, the day it was actually read, keyword, topic, source type,
  access method and permitted use. Scraping, login/paywall bypass and rate-limit evasion are
  refused. An API is accepted only if configured; no Pinterest or Etsy API is.
- Every claim cites at least one registered source. Search interest and trend direction
  never count as sales evidence; only our own platform records can evidence a sale.
- Asset use above a platform's cap needs a licence that states commercial use and has a
  reference. Attribution alone is never permission. Pinterest content is never an asset.
- Rights screen: PASS only on real assets that are ours (with process evidence) or properly
  licensed; uncertain ownership or derivative wording is REVIEW; third-party, Pinterest or
  attribution-only material is BLOCK. An idea with no assets is at most REVIEW.
- Scoring (9 dimensions, 0..5): a dimension without evidence is `None` with the reason. The
  composite is over scored dimensions only, with coverage; under 60% coverage or without
  demand evidence the band is `INSUFFICIENT_EVIDENCE`. Results are `advisory: true`,
  `publication_decision: null`. Definitions are in `trend_to_product/scoring.py`.
- Specs: required fields, acceptance tests, observed competitor price range (or UNKNOWN),
  duplication against the registry (title words plus subject concepts), and a blocker when
  the factory cannot verify the format's technical correctness.
- Listing drafts: `DRAFT_NOT_PUBLISHED`, `publish_allowed: false`.
- Calibration against outcomes reports `NOT_ENOUGH_DATA` until 5 spec-built products have
  been listed for 30 days; it never changes weights by itself.

## First research run (2026-10-29)

24 sources, 15 signals, all read through a web-search index on 2026-10-29. No Pinterest
Trends index reading exists (the tool needs a signed-in session), so no first-party
search-volume figure is recorded. Evidence mix: 14 marketplace listings, 5 third-party
estimates, 3 secondary press summaries of Pinterest Predicts 2026, 1 Pinterest help page,
1 Pinterest developer forum reply.

| Candidate | Format | Band | Score / coverage | Competitor list prices |
|---|---|---|---|---|
| Crochet/craft project planner | printable | WEAK | 2.37 / 73% | $9.99-$150 |
| Original crochet patterns | pattern | WEAK | 2.11 / 73% | $1.20-$27.99 (median ~$5.99, ~727k listings) |
| Handmade pricing calculator | Excel | INSUFFICIENT_EVIDENCE | - / 67% | $2.24-$45; free sheets exist |
| Reading journal / hobby tracker | printable | INSUFFICIENT_EVIDENCE | - / 53% | $0.71-$10.74; free sheets common |
| Printable miniatures | printable | INSUFFICIENT_EVIDENCE | - / 40% | $2.32-$7.82 |
| Notion content planning system | Notion | INSUFFICIENT_EVIDENCE | - / 40% | $7-$50 |

Reading: crochet ranks first only because it is the one topic with a trend signal, and that
signal is press coverage of Pinterest Predicts naming crochet inside a lace trend, with no
crochet search figure. The planner borrows that general signal. Neither is a recommendation
to build.

Specs: "Handmade Order Costing & Pricing Workbook" is `SPEC_REVIEW`: it would compete with
our own B14-005 "Etsy & Shopify Product Profit Calculator" (found by the concept check; the
first version of the check missed it). "Lace-Edge Crochet Phone Pouch Pattern" is
`SPEC_BLOCKED`: gauge, drape and fit need a physical test make this factory cannot do.

## Customer-problem signals (B32, same day)

`scripts/trend_problem_signals.py` reads questions from the public Stack Exchange API (no
key; quota 300/day; stops on `backoff` or quota < 50; at most 12 calls per run) and records
one aggregated CUSTOMER_PROBLEM signal per topic (sources typed ANECDOTAL, use SIGNAL_ONLY;
question text is cited, never reused). Problem severity is banded by distinct questions
(1-2:1, 3-9:2, 10-29:3, 30-99:4, 100+:5). Runs weekly from `scripts/registry_daily.py`
(`--if-due`). Tests: `tests/test_trend_problem_signals.py` (11, fake network).

First live run used loose substring matching and counted irrelevant questions ("Do they
sell artist gloves" as pricing, a Bronte question as a reading-tracker problem), which
lifted four candidates from INSUFFICIENT_EVIDENCE to WEAK. Caught on review the same hour:
matching now needs a whole-word topic anchor AND a problem term, a topic with zero matches
drops its earlier problem signal, and those real titles are regression tests. The first
run's records stay in the append-only ledgers; the latest opportunity records supersede them.

Corrected result: crochet patterns 2 questions, paper miniatures 1, planners / pricing /
reading / content 0. Stack Exchange is a thin source for consumer craft topics; it does not
replace a Pinterest Trends or marketplace-search reading (B29).

| Candidate | Band after B32 | Score / coverage |
|---|---|---|
| Crochet/craft project planner | WEAK | 2.37 / 73% |
| Printable miniatures | WEAK | 2.08 / 73% (1 question) |
| Original crochet patterns | WEAK | 2.01 / 87% |
| Pricing calculator, reading journal, Notion content system | INSUFFICIENT_EVIDENCE | - |

## Gaps closed after the acceptance review (same day)

- **Link to real production/QA records, on live data.** New relation `OVERLAPS_EXISTING`,
  accepted only when the spec's own duplication check listed that product. Recorded:
  "Handmade Order Costing & Pricing Workbook" -> B14-005. Its trace reads B14-005's manifest
  QA (PASS), its approval, its listing and its observed outcome (0 sales; traffic, refunds
  and net revenue UNKNOWN because no source records them).
- **Approval lookup was incomplete.** The first trace said B14-005 had no approval: it read
  only `data/publication_approvals.json`, which starts at batch 15. Batches 13-14 were
  authorised per batch in `data/batch*_publish_results.json`; the trace now reports
  `BATCH_AUTHORIZATION` with the founder's recorded text and source.
- **Previews from the actual deliverable** (`trend_to_product/previews.py`): each preview is
  recorded with the sha256 of the deliverable it was rendered from and of the image; a
  preview from an older file version or an edited image fails; a listing draft needs at
  least one RENDER, and a MOCKUP only passes when the listing labels it an illustration.
- **Mission Control:** service `trend-to-product-status` (`/api/v1/trend-to-product-status`,
  login required; 401 without, verified) and a panel in `mission_control_executive_v1.html`.
  It returns the stored state plus the trace of every linked spec.

## Not implemented / not verified

- No automated collection from Pinterest or Etsy; no API credential exists or is assumed.
- No first-party search volume (Pinterest Trends needs a session; Google Trends' daily feed
  is already used by Sensing and yields little for these topics).
- Per-product traffic, refunds and net revenue: UNKNOWN (backlog B6; no refund/fee source).
- Notion delivery path and craft-pattern verification: not available.
- No product was built from these specs; no listing draft was written to disk.

Backlog rows B28-B33 in `docs/factory/FACTORY_ENGINEERING_BACKLOG.md`.
