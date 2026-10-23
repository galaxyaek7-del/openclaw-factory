# Factory baseline report (2026-10-23)

## Catalog reconciliation (live Gumroad API, read-only, 2026-10-23)

| Measure | Value |
|---|---|
| Gumroad products | 92 (89 published, 3 unpublished) |
| Total `sales_count` across all products | **0** |
| `data/catalog.json` rows | 83; 82 match a live id; 1 not live (KDP pending row) |
| Live products missing from the catalog | 10, all batch 14 (published 2026-10-23); none other |
| Canonical inventory (`reports/CYCLE104/DIGITAL_PRODUCT_INVENTORY.json`) | 21 products; **0** of their ids match a live Gumroad id |
| Duplicate live titles | 1 ("The 5-Minute Context Reset Playbook", two listings) |
| Published price distribution (USD: count) | 0:1, 7:1, 8:1, 9:2, 11:1, 12:3, 14:2, 15:5, 19:3, 24:1, 29:19, 39:5, 49:19, 59:12, 69:8, 79:3, 89:1, 155:1, 399:1 |

Reading: the platform-keyed catalog tracks the live store well apart from the newest batch; the "canonical" inventory does not track the live store at all (it identifies products by internal, Paddle and Amazon ids). There is no single record that links a product's specification, files, QA, listing and sales.

## Tests and CI

| Run | Result |
|---|---|
| GitHub CI on `cde4f73` | 36/36 jobs successful |
| CI-equivalent run on a clean checkout of the cleaned history (CI=true, GITHUB_ACTIONS=true) | Python groups b 203, e 626, f 237, i-p 1,615 OK; a, c-d, g-h, q-z passed; 0 unimportable of 5,853; all JS batches passed |
| Doctrine gate (`scripts/check_doctrine.py`) | 53 passed |
| Known failing locally, not in CI | `tests/test_exp_c81_utm_regression.py` (parallel session's uncommitted edit expecting a mandatory gate); `tests/test_factory_loop_daily_product_lifecycle_snapshot.js` (untracked, calls a function absent from every commit) |
| Batch 14 product QA | 872/872 formula checks; 10/10 file, guide, brand, bundle and public-page checks |

## Operating metrics

| Metric | Value | Source |
|---|---|---|
| Verified revenue | $0.00 | `config/reality.json`, Gumroad `/v2/sales` |
| Public site traffic | UNKNOWN (no receiver on GitHub Pages; the 32 recorded rows are local probes and tests) | `data/affiliate_page_views.jsonl`, `customer_site/assets/gf-pageview.js` |
| Affiliate clicks recorded | 29 (same caveat: local server only) | `data/affiliate_clicks.jsonl` |
| Agent calls recorded | 14, 3 empty outputs (21%) | `data/agent_executions.jsonl` |
| Loop steps | 53 per tick | `factory_loop.js` |
| Connection verifier | 49 VERIFIED, 3 DEGRADED | `data/connection_status.json` |
| Demand sensing (first run) | 35 questions, 20 sent, 18 accepted | loop log 2026-10-23 |
| IndexNow (first automatic run) | HTTP 200, 73 URLs | `data/indexnow_submissions.jsonl` |

## Defects known at baseline

See `FACTORY_GAP_AND_RISK_REGISTER.md` (R1-R12). The two that block revenue directly: no traffic (R1) and paid files available free (R2, being fixed).
