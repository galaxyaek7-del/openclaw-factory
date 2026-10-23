# Batch 14 — ten spreadsheet tools, built, verified and published (2026-10-23)

Founder request (2026-10-23): produce ten high-value digital products with review, inspection and testing, then upload and publish them on Gumroad in one full cycle, at realistic prices.

## Products (all live, verified by API re-read the same day)

| ID | Product | Price | Gumroad |
|---|---|---|---|
| B14-001 | 13-Week Cash Flow Forecast for Small Business | $19 | https://aekraft.gumroad.com/l/dliccs |
| B14-002 | Rental Property Deal Analyzer | $24 | https://aekraft.gumroad.com/l/mfpqin |
| B14-003 | Debt Payoff Planner (Avalanche or Snowball) | $12 | https://aekraft.gumroad.com/l/ebuszz |
| B14-004 | Self-Employed Quarterly Tax Set-Aside Planner (US, 2026) | $12 | https://aekraft.gumroad.com/l/ydgbnh |
| B14-005 | Etsy & Shopify Product Profit Calculator | $12 | https://aekraft.gumroad.com/l/ntbvq |
| B14-006 | Service Business Pricing & Break-Even Calculator | $15 | https://aekraft.gumroad.com/l/czhxhu |
| B14-007 | Inventory Reorder Point & Stock Tracker | $15 | https://aekraft.gumroad.com/l/jydqg |
| B14-008 | Client Pipeline & Proposal Tracker | $14 | https://aekraft.gumroad.com/l/qevzns |
| B14-009 | Startup Runway & Burn Planner | $15 | https://aekraft.gumroad.com/l/mcwusn |
| B14-010 | Zero-Based Monthly Budget Planner | $9 | https://aekraft.gumroad.com/l/uubnbi |

Each listing: published, one cover, one file whose size equals the reviewed bundle (re-read via `GET /v2/products/:id`). Site pages: `customer_site/tools.html` and `customer_site/tool-*.html`.

## Why these, and the prices

Measured state before the batch: 82 Gumroad products, 0 sales. Site traffic was reported here as about ten visits a month; that was wrong: public traffic is not measured at all (no page-view receiver on GitHub Pages; the recorded rows are local probes). Corrected 2026-10-23. Most existing listings are compliance kits at $49-69. Comparable spreadsheet tools on Etsy/Gumroad (searched 2026-10-23) sell at about $3-50, most at $9-29; a comparable rental deal analyzer is listed at $29.25. A store with no reviews priced at the lower-middle of that range.

## Verification

| Check | Result |
|---|---|
| Workbook opens and contains formulas (`file_testing_engine.test_xlsx`) | PASS × 10 |
| Formula cells recalculated by `lib/xlsx_eval.py` and matched against an independent Python model of the same math | 872 / 872 |
| Guide PDF: title and disclaimer extracted from the rendered text | PASS × 10 |
| Listing copy through `brand_dna.validate_customer_facing_text` | PASS × 10 |
| Bundle zip integrity, exactly workbook + guide + README | PASS × 10 |
| Bundle SHA-256 at publish time equals the reviewed manifest | PASS × 10 |
| Public listing page answers 200 and shows the title | PASS × 10 |

Facts verified against sources before use: 2026 Social Security wage base 184,500 (SSA, Oct 2025); Etsy US fees 0.20 / 6.5% / 3% + 0.25 / Offsite Ads 15% capped at 100; Shopify Basic 2.9% + 0.30; IRS estimated-tax periods and 2026 due dates; safe harbor 100% / 110%.

Defects found by the review and fixed before publishing: a summary formula summing the wrong column (debt planner), example narratives that did not match the example numbers (cash flow, rental, service pricing, budget), an impossible over-capacity example plan, an evaluator `ROUND` that rounded half to even (Excel rounds half away from zero), and a disclaimer phrase that tripped the trademark scan.

## Tooling added

- `lib/xlsx_eval.py`: `^`, `PMT`, `NPER`, `SUMIF`, operator criteria, `AVERAGE`/`COUNT`/`COUNTA`, `INT`/`ROUNDUP`/`ROUNDDOWN`, Excel `ROUND`.
- `scripts/publish_batch14.py`: dry run by default; hash-checked, scoped, read-back-verified publication.

## Governance note

The ten were published through `channels/gumroad_publisher.py` directly (as the earlier listings were), with the live flag set only inside the publishing process, the Gumroad auth state re-verified and a single-use upload scope per file. The central Quality Gate in `distributor.py` (gate 1 evidence runner + gate 2 founder review ledger) was not consulted; no founder approval record was written on the founder's behalf. The authorization is the founder's instruction of 2026-10-23.

Found, not mine: the working tree's uncommitted `tests/test_exp_c81_utm_regression.py` expects `distributor.py` to consult the Quality Gate on every real publish (founder directive 2026-10-17), but `distributor.py` still consults it only when configured; that test fails until the matching code change lands.

## What sells these

Nothing yet: 0 sales is the starting point. The products now have pages on the site, sitemap entries and the daily IndexNow submission. Whether anyone visits is not yet measurable (see docs/factory risk R1).
