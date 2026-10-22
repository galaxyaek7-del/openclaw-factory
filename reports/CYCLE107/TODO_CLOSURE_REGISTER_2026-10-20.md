# TODO Closure Register - Cycle 107

Date: 2026-10-20
Scope: GF-C107-FIRST-SALE-RESET and GF-AUTO-TODO-AFFILIATE-107.
Constraint: TOTAL_NEW_SPEND=$0. No publication, no account creation, no binding agreement.

Statuses here mean what they say. "PASS" means a command was run and its output
seen. "BLOCKED" means an action outside this session's authority is required.
"UNKNOWN" means no test has been run that could settle it.

## Closed this cycle

| ID | Item | Evidence | Status |
|---|---|---|---|
| T-01 | Discovery gate rejects before scoring | `market_discovery_engine.py` G1-G6; 24 tests; retro replay 3/3 rejected | PASS |
| T-02 | Evidence provenance for Cycle 107 URLs | 29-URL classification; V1 404, V2 DNS, V3 403 block page | PASS |
| T-03 | Incident recorded for repeated post-score rejection | `INC-454a108bcdd3`, 15 fields validated, preventive control `tests/test_discovery_gate_repair.py` | PASS |
| T-04 | B13-001 false "all-in" label | label fixed, drawn reserve surfaced at `Summary!B20`, workbook/guide rebuilt | PASS |
| T-05 | B13-001 independent value check | 17 fields, 0 mismatches | PASS |
| T-06 | B13-001 workbook QA | Excel recalculation, 416 formulas, 0 error cells, 0 critical/warning | PASS |
| T-07 | B13-001 disclosure present in guide | `scripts/build_b13_001_guide.py:569-572` plus gate word count | PASS |
| T-08 | Affiliate tracked-link renderer | `scripts/render_affiliate_asset.py`; refuses untracked/outside paths; 2 placeholders replaced | PASS |
| T-09 | Attribution-integrity tests | `tests/test_render_and_attribution_integrity.py`, 16 tests | PASS |
| T-10 | Affiliate link never committed | output in gitignored `drafts/affiliate/rendered/`; `git check-ignore` exit 0 | PASS |

## Awaiting a founder decision

| ID | Item | Why it cannot be closed here | Status |
|---|---|---|---|
| F-01 | B13-001 publication at $15.00 | Requires `FACTORY_LIVE_PUBLISH=true`; publication is not authorized | BLOCKED_BY_AUTHORIZATION |
| F-02 | Gumroad credential freshness | Session auth is VERIFIED but stamped 2026-10-19; refresh requires founder login | BLOCKED |
| F-03 | systeme.io affiliate account/tag use | Account terms and tax identity are the founder's; tag exists, no application submitted by this session | HOLD |
| F-04 | impact.com application | Binding agreement plus tax/identity data at $2,000/yr; free but discretionary approval | HOLD |
| F-05 | Amazon Associates tag | `AMAZON_ASSOCIATE_TAG` unset; all 4 links untagged | BLOCKED |
| F-06 | Any payout route selection | Choice affects tax residency reporting; no payout has ever been received | HOLD |

## Real gaps with no code

| ID | Item | Current truth | Status |
|---|---|---|---|
| G-01 | Conversion/commission tracking | No network postback exists. Clicks are real; conversions are not observable | NOT_IMPLEMENTED |
| G-02 | Public serving of `/api/affiliate/*` | Local server has the routes; public host is not verified to serve them (GF18) | UNKNOWN |
| G-03 | Traffic to any affiliate asset | 0 published assets, 0 real clicks on the systeme link | BLOCKED_ON_PUBLICATION |
| G-04 | B13-001 platform product existence | No Gumroad call was made (`gumroad_call_made: false`) | UNKNOWN |
| G-05 | Two prior numbers: "189 tests", "23 technical checks" | No reproducible command or artifact retained | UNKNOWN |
| G-06 | Algeria payout feasibility per network | Eligibility and fees are published; receipt in Algeria is untested | UNKNOWN |

## Pre-existing failures (not introduced by this cycle)

`node scripts/check_jsonl_duplication.js` exits 1. `test_final_rehearsal::test_no_autopublish_path`
fails. `test_first_product_build` has 2 failures. The g-h group has 7 failures.
`tests/test_production_wiring.py` has 3 failures. CI status is UNKNOWN (`gh` absent).

The suite is not green. Nothing in this register claims it is.

## Same-round extension — 2026-10-21 (catalog truth + payout evidence)

Scope was widened, not weakened: still `TOTAL_NEW_SPEND=$0`, no publication,
no account change. Evidence for every row below is in
`reports/CATALOG_SYNC_2026-10-21.md`, `reports/ALGERIA_PAYOUT_MATRIX_2026-10-21.md`,
and `reports/COMMERCIAL_OPPORTUNITY_REVIEW_2026-10-21.md`.

| ID | Item | Evidence | Status |
|---|---|---|---|
| T-11 | Offline catalog integrity capability | `scripts/catalog_integrity.py`; 22 tests | PASS |
| T-12 | Fresh read-only live catalog evidence | 82 products, 79 published, 0 sales; `reports/LIVE_CATALOG_READ_2026-10-21.json` | PASS |
| T-13 | Stable-id catalog sync capability | `scripts/catalog_sync.py`; id first, slug fallback, never title; 38 tests | PASS |
| T-14 | Catalog rebuilt without invented metadata | 12 → 83 records; 71 appended; KDP preserved; unknown fields explicit | PASS |
| T-15 | Published-listing coverage | 79 of 79 reconciled slugs; `CATALOG_COVERAGE` now NOTE | PASS |
| T-16 | Idempotent rerun | second live run: `changed=False`, no write, no backup | PASS |
| T-17 | Adjacent regression | 32 + 19 + 5 + 22 tests; doctrine gate exit 0 (53 tests) | PASS |
| T-18 | Algeria payout routes documented per route | 32 rows; 0 VERIFIED, 10 CONDITIONAL, 19 UNKNOWN; four-gate model | PASS |
| T-19 | Duplicate live listing surfaced, not merged | two distinct ids/slugs, same name, both `$15.00`, 0 sales | PASS (reported) |
| O-01 | Batch-12 registry vs prep-file conflicts | 9 findings: 3 registry-lags, 6 state conflicts | OPEN — not silently rewritten |
| O-02 | B12-006/007/008/009 content depth | QA 233–273 words against a 1,900–2,900 target | OPEN — content work |
| O-03 | B12-002/005/010 listing authorization | Founder-only phrase + live credential | BLOCKED_BY_AUTHORIZATION |
| O-04 | Payout eligibility at account level | Identity/tax/banking verification is founder-only | BLOCKED |

New honest unknowns: PayPal Payouts Algeria availability has no stored artifact
(`UNKNOWN`, not "unavailable"); Awin/Payoneer, Impact, Tipalti and PartnerStack
DZ receiving rails are `UNKNOWN`; the list API exposes no filenames, hashes or
buyer data. A published listing is still not evidence of a sale.

## Later same day - verification, curation, B12 repair, Gumroad reconciliation

Scope unchanged: `TOTAL_NEW_SPEND=$0`, no publication, no account change, no
finance write. Evidence: `reports/CATALOG_RECONCILIATION_PROOF_2026-10-21.json`,
`reports/B12_STATE_RECONCILIATION_2026-10-21.json`,
`reports/COMMERCIAL_RECONCILIATION_2026-10-21.json`. Completion crossed UTC
midnight: final verification ran at `2026-10-22T00:13Z`.

| ID | Item | Evidence | Status |
|---|---|---|---|
| T-20 | Independent catalog arithmetic proof | `catalog_sync.py --verify`; 12 invariants; 12→83 from backup and 83→83 current both PASS | PASS |
| T-21 | Catalog business-state curation | 3 records annotated; 0 deleted/merged; integrity 11 ERROR → 0 ERROR / 2 WARNING / 2 NOTE | PASS |
| T-22 | B12 registry vs prep-file repair | 3 published, 3 ready-unauthorized, 4 QA-fail; backup + `product_batch_12.json`; authorization still NOT_GRANTED | PASS |
| T-23 | Gumroad sales reconciliation | `reconcile_gumroad()`; live 0 platform / 0 internal; 16 tests | PASS |
| T-24 | Regression on touched suites | catalog sync + integrity 60 passed; commercial reconciliation 16 passed; doctrine 53 passed (`check_doctrine.py` ok) | PASS |
| O-01 | Batch-12 registry vs prep-file conflicts | 9 findings repaired: 3 registry-lags, 6 state conflicts | CLOSED |
| O-05 | B12-008 deliverable drift | 4 hash/size drifts + stale workbook QA; files are untracked and were not modified this pass | OPEN - re-run QA/re-baseline only after inspection |
| F-07 | Paddle transactions API | Live `GET /transactions` returns **403 Forbidden** with the configured credential | BLOCKED - API permission/account issue |
| F-08 | Duplicate `vhofn` unpublish | Keep `akxaae`, unpublish `vhofn`, then remove its card at `customer_site/products.html:122` | BLOCKED_BY_FOUNDER_DASHBOARD |
| F-09 | Zero-file `owtmpe` removal | Published, 0 files, price $0; API cannot delete/unpublish | BLOCKED_BY_FOUNDER_DASHBOARD |

`B12-004` remains `PUBLISHED_AND_VERIFIED` from independent live evidence; no
gate verdict was invented for it. `data/product_batch_12_gumroad_prep.json` was
not edited; its `registry_corrections.applied=false` is now a stale status flag,
not stale content.

## Post-reconciliation execution - storefront commercial gate (2026-10-22)

Scope unchanged: `TOTAL_NEW_SPEND=$0`, no publication, no account change, no
finance write. `FACTORY_LIVE_PUBLISH=false` was re-read, not changed.

| ID | Item | Evidence | Status |
|---|---|---|---|
| T-25 | Storefront commercial consistency capability | `scripts/storefront_commercial_check.py` + 14 tests; live pre-fix 2 ERROR / 6 WARNING, post-fix 0/0/0; 75 active buy links, 3 held, `global_hold_banner: false` | PASS |
| T-26 | Storefront defects fixed at source | removed page-wide "not for sale" banner that contradicted 75 live checkouts; scoped 3 held buttons; corrected Real Estate Transaction Deadline Kit card `$59` -> `$29` against `LIVE_CATALOG_READ_2026-10-21.json` (`price: 2900`) | PASS |
| T-27 | B12-010 identity preserved | PDF/XLSX/cover bytes and SHA-256 match `reports/B12-010/MANIFEST_2026-10-19.json`; no file rewritten | PASS |
| T-28 | B12-002/005/010 authorization boundary | registry `authorization_status: NOT_GRANTED`; no listing action taken; B12-002 gate $11.99 and B12-005 gate $8.00 cited, not re-authorized | PASS |
| T-29 | Final focused regression and doctrine gate | exact prior suite 129 passed, 2 subtests; combined suite 143 passed, 2 subtests; `check_doctrine.py` ok; py_compile ok | PASS |
| O-05 | B12-008 deliverable drift | `check_b12_integrity.py` exit 1: XLSX/PDF hash+size drift, stale workbook QA; untouched this pass | OPEN |

## Final closure verification - 2026-10-22 (post-storefront)

Scope unchanged: `TOTAL_NEW_SPEND=$0`, no publication, no account change, no
finance write. Every result below was produced by a command or direct file read
in this pass.

| ID | Item | Evidence | Status |
|---|---|---|---|
| T-30 | Held-card truth rules + final storefront gate | `scripts/storefront_commercial_check.py` now rejects held-card active offers and delivery claims and warns on un-scoped page offers; `tests/test_storefront_commercial_check.py` 17 passed; `--json --write` -> `PASS`, 0 ERROR / 0 WARNING / 0 NOTE, 80 cards, 75 active links, 3 held, 72 distinct active slugs | PASS |
| T-31 | Storefront held-card copy fixed at source | removed held EU AI Act free-copy/email offer; replaced its delivery claim with "not available for purchase or download while the hold is active"; scoped page-wide free offers to "available kit"; fine print now 78 cards / 74 distinct / 3 held, matching the page | PASS |
| T-32 | B12-010 independent identity + workbook QA | PDF/XLSX/cover bytes and SHA-256 match `MANIFEST_2026-10-19.json`; native Excel QA PASS at XLSX `df49ceca...`, 9 sheets, 427 formulas, 0 critical/warning; `authorization_phrase` remains null | PASS |
| T-33 | B12-002 identity and content | current PDF/XLSX hashes match `reports/CYCLE104/LISTING_PAYLOADS_B12.json` (`2f047f5a...` / `e733ea8e...`); gate at `$11.99` APPROVED; sweep PASS, 4 pages, 6 sheets, 102 formulas; publication authorization absent. The `$11.99` `price_basis` says `FOUNDER_APPROVED_BELOW_COMPARABLE_2026-10-18`, but no separate primary founder phrase is stored, so treat it as documented-not-primary | PASS (identity/QA); price provenance needs founder confirmation |
| T-34 | B12-005 identity and stale QA hash | current PDF/XLSX hashes match `LISTING_PAYLOADS_B12.json` (`a7b11fbc...` / `0720869b...`); current sweep PASS, 8 pages, 6 sheets, 154 formulas; `QA_FACTS_2026-10-19.json` still records a different PDF hash (`246268d4...`, 20,146 bytes), so the exact current PDF is not covered by that QA record | HOLD - refresh QA identity before any authorization |
| T-35 | Historical "11 catalog errors" | `reports/CATALOG_RECONCILIATION_PROOF_2026-10-21.json` records `resolved_errors: 11` and the exact classes: unexplained $0 price, duplicate name, 3 B12 registry lags, 6 B12 state conflicts; current integrity `0 ERROR / 2 WARNING / 2 NOTE`; sync `83/83`, `changed=False` | PASS |
| T-36 | Storefront/catalog count reconciliation | `products.html` has 80 card containers = 78 product offers + 2 non-product promo/info blocks. The 78 offers = 75 active buy links + 3 held buy links; 74 distinct products = 72 active slugs + 2 held slugs. Duplicate links: `fgruzn` x3, `uldlwa` x2, held `iaiyt` x2. 79 published catalog products reconcile as 74 listed + 5 omitted (`svlky`, `ieashv`, `blayvb`, withdrawn `owtmpe`, duplicate `vhofn`). Footer "78 product cards / 74 distinct / 3 held" is truthful; the checker's `cards=80` counts the 2 non-product blocks. | PASS (truthful count); 3 legitimate omitted products remain a founder merchandising decision |
| T-37 | Paddle 403 diagnosis | configured key is live-format and 69 chars; read-only GETs to `/products?per_page=1`, `/transactions?per_page=1`, and the API root all return `403 forbidden` / "You aren't permitted to perform this request." `invalid_token` is absent, so the key is valid but lacks permissions. API-root request ID `943c0135-06ba-46a3-b6b4-881dbb2c4869`. Exact fix in `reports/CYCLE107/PADDLE_READ_DIAGNOSIS_2026-10-22.md` | BLOCKED - add `product.read` / `transaction.read` / `price.read`; no write attempted |
| T-38 | Final focused suite + doctrine | `pytest` over catalog sync, catalog integrity, commercial reconciliation, doctrine layers, storefront = `146 passed, 2 subtests`; `check_doctrine.py` `ok: true` (15 claims, 0 critical; 53 doctrine tests) | PASS |
| O-05 | B12-008 current state | current PDF/XLSX match `FINAL_RELEASE_RECORD_2026-10-20.json`; native QA at the current XLSX hash `89cc4704...` PASS, 130 formulas, 0 critical/warning; drift is an expected version change, but registry still says `QA_FAIL__NOT_LOCAL_READY` at `$29` while the gate supports `$18`, and no authorization exists | HOLD - founder price/state decision; baseline intentionally not rewritten |
| O-06 | Product license / resale terms | no product-specific license file or catalog field found; only Python package licences exist in `venv`; listing copy does not state resale/commercial-use terms | UNKNOWN - not recorded, not invented |
| O-07 | B12-005 QA-to-artifact binding | `QA_FACTS_2026-10-19.json` PDF hash does not match the committed PDF whose hash is anchored in `LISTING_PAYLOADS_B12.json`; content sections and word counts are unchanged when page headers are excluded | HOLD - re-run QA and record the current hash before authorization |

B12-008 is not re-baselined. B12-002/005/010 remain `NOT_GRANTED` /
`AWAITS_FOUNDER_LISTING_AUTHORIZATION`; no listing action was taken.

## Addendum - 2026-10-22 evidence closure (B12-005 / B12-008 / licensing)

Scope unchanged: `TOTAL_NEW_SPEND=$0`, no publication, no account change, no
finance write, no product file changed. This addendum supersedes the status of
`O-05`, `O-06`, and `O-07` only; their earlier rows are retained as history.

| ID | Item | Evidence | Status |
|---|---|---|---|
| T-39 | B12-008 price/state reconciliation | `reports/B12-008/PRICE_STATE_RECONCILIATION_2026-10-22.json`: current PDF `769074...` and XLSX `89cc4704...` match `FINAL_RELEASE_RECORD_2026-10-20.json`; native workbook QA PASS at the current XLSX (130 formulas, 0 critical/warning); `$18` gate APPROVED (market score 70, ceiling `$18.70`); `$29` gate `NOT_READY` (market score 40); registry/prep/phase8 still say `$29` and `QA_FAIL__NOT_LOCAL_READY`; storefront is notify-only and not in `products.html` or `data/catalog.json`; no authorization. The gate file's own `role` is `RECOMMENDED_PRICE` and its note says it "Still requires founder listing authorization"; the final release record's state is `READY_FOR_AUTHORIZATION` and its unresolved field calls `$18` the "gate-supported proposed price." A direct read-only probe shows `$18.70` also passes and `$18.71` fails, so the gate's claim that `$18` is the highest passing price is not proven by its own hardcoded `SUPPORTED_PRICE=18.0`. Therefore `$18` is `GATE_SUPPORTED_NOT_FOUNDER_APPROVED`, not an authoritative price or a uniquely derived maximum. `check_b12_integrity.py` still exits 1 because its baseline was not rewritten | HOLD - founder price/state decision |
| T-40 | B12-005 QA identity refresh | `reports/B12-005/QA_FACTS_2026-10-22.json`: committed canonical LF blob is 20,146 bytes / `246268d4...`; worktree CRLF PDF is 20,365 bytes / `a7b11fbc...`; removing CR bytes reproduces the committed blob exactly; extracted text SHA-256 is identical (`1e32e4f7...`); both variants pass technical and brand QA; 8 pages, 3,371 words, 15 sections, 1280x720 cover, no placeholders/mojibake; historical QA retained unchanged | PASS |
| T-41 | Product licensing evidence register | `reports/CYCLE107/PRODUCT_LICENSING_EVIDENCE_2026-10-22.md`: no standalone EULA/license/catalog field for B12-002/005/008/010; B12-005 has one restriction on PDF page 8 ("do not resell or redistribute the files"), no affirmative grant; B12-008 `license`/`licence` words are subject matter, not terms; B12-010 `licence` is subject matter; B12-002 and B12-008 report covers do not match their documented generator outputs and have `UNKNOWN` source; no third-party asset manifest | HOLD - founder terms decision |
| T-42 | Founder decision register updated | `reports/CYCLE107/FOUNDER_DECISION_REGISTER_2026-10-20.md`: added FQ-07 (B12-008 price/status), FQ-08/FQ-09/FQ-10 (B12-002/005/010 authorization), FQ-11 (Paddle read permission), FQ-12 (B12 buyer license), FQ-13 (omitted/cleanup listings) | PASS (request recorded) |
| T-43 | Final focused regression + doctrine after this pass | `pytest` over catalog sync, catalog integrity, commercial reconciliation, doctrine layers, storefront = `146 passed, 2 subtests`; `scripts/check_doctrine.py` `ok: true` (15 claims, 0 critical, 7 warning; 20 incidents, 0 findings; 53 doctrine tests) | PASS |
| T-44 | Historical 11 catalog error audit | Itemized: 1 zero-price published listing (`IW58tjt2zS14fPYrWZOuxg==`, withdrawn, $0, 0 files), 1 duplicate name pair (indexes 17/81), 3 B12 registry lags (`B12-001/003/004`), and 6 B12 state conflicts (`B12-002/005/006/007/008/009`). The 3+6 were registry repairs on 2026-10-21; the first two remain `WARNING` and founder-dashboard actions. Current `catalog_integrity.py` is `PASS` with `0 ERROR / 2 WARNING / 2 NOTE`. B12-008 is a separate, later price/state HOLD, not a reopened catalog error | PASS (audited); 2 warnings remain |
| O-05 | B12-008 current state | Superseded by T-39: current artifacts and QA are coherent; the unresolved issue is the live `$18` vs `$29` price decision plus stale registry/prep/phase8 state. No baseline was rewritten | HOLD - founder price/state decision |
| O-06 | Product license / resale terms | Superseded by T-41: no complete terms exist; B12-005 has only a no-resale/redistribution restriction; the other three have none; cover provenance for B12-008 is unknown. No rights were inferred | UNKNOWN - founder terms decision |
| O-07 | B12-005 QA-to-artifact binding | Superseded by T-40: refreshed QA covers both the canonical committed LF blob and the current CRLF worktree bytes, proved to be the same extracted text | CLOSED |

Current publication boundary: B12-002, B12-005, B12-008, and B12-010 all have
no valid listing authorization. `FACTORY_LIVE_PUBLISH=false` was re-read, not
changed. No commit or push was made in this pass.

## Addendum 2 - 2026-10-22 commercial blocker resolution

Scope unchanged: `TOTAL_NEW_SPEND=$0`, no publication, no account change, no
finance write, no product file changed, no listing/price edited.

| ID | Item | Evidence | Status |
|---|---|---|---|
| T-45 | B12-002 `$11.99` provenance | The only source chain is `data/product_batch_12.json` (`price_basis: FOUNDER_APPROVED_BELOW_COMPARABLE_2026-10-18`, `price_rationale: Founder decision 2026-10-18`), repeated by `reports/B12-002/GATE_FINAL_2026-10-18.json`, `data/product_batch_12_gumroad_prep.json`, `drafts/b12_002_listing_copy.txt`, and `reports/phase8/B12_002_GUMROAD_LISTING_PACKAGE.md`. The same phase8 file's checklist still has `- [ ] Price confirmed by the founder ($11.99 recommended...)` unchecked; `reports/B12-002/DEMAND_EVIDENCE_2026-10-18.json` says `requires_founder_confirmation: true`; `data/operational_history.jsonl` records only `QA_PASS`/`READY_FOR_AUTHORIZATION` and "no publication authorization is recorded". No independent primary phrase, account record, or dated founder message exists. | HOLD - `UNKNOWN_PRIMARY_PROVENANCE`; documented claim is not proof |
| T-46 | B12-008 directive prices | `$10.70` has no B12-008 record; targeted searches of `reports/B12-008`, `reports/CYCLE104`, `reports/CYCLE107`, both batch-12 registries, and `scripts/b12_008_gate.py` found no `$10.70`; unrelated `10.7` hits were timestamps. `$18.00` is `RECOMMENDED_PRICE`/`GATE_SUPPORTED`, not founder-approved and not the maximum. `$18.70` passes, `$18.71` fails. `$29.00` remains `NOT_READY` (market 40). | HOLD - `$10.70` `UNKNOWN_NOT_FOUND`; `$18` gate-supported only |
| T-47 | Paddle 403 validation | Current key is present, live-format, 69 chars, no whitespace. `reports/COMMERCIAL_RECONCILIATION_2026-10-21.json` records 403 on `/transactions`; the 2026-10-22 probes recorded 403 on `/products`, `/transactions`, and the API root. `data/c86_execution_record.json` records earlier `GET /products` 200, `PATCH /products/{id}` 200, and `GET /api-keys` 200. No key fingerprint or raw 2026-10-22 HTTP body was retained. Permission removal, key replacement, account/role change, and account restriction remain candidates. | BLOCKED - 403 confirmed; root cause `UNKNOWN`; support request drafted |
| T-48 | Gumroad ID/storefront reconciliation | `reports/LIVE_CATALOG_READ_2026-10-21.json` (2026-10-21T17:44:07Z): 82 products, 79 published, all sales 0. `data/catalog.json`: 83 records = 82 Gumroad + 1 local-only KDP; 82 unique Gumroad slugs; all 82 catalog records match the snapshot on product id, published flag, price, and sales; no missing/extra slug; no duplicate slug. `owtmps` has no record in either source. The actual withdrawn zero-price listing is `owtmpe` (`IW58tjt2zS14fPYrWZOuxg==`, published, $0, 0 delivery files). Duplicate pair remains `akxaae` (`rMOopS7Q7LHxwaPTY462uw==`) and `vhofn` (`9Zq9SGkALI0tjd7A97Pc_A==`), both $15; omitted active products remain `svlky` (`TFeaaWXO3zySimrs2Jbjbw==`, $8), `ieashv` (`-cbRBfZyJMTKpl-Xk8Oz3Q==`, $11.99), `blayvb` (`W9FpZXpQB-fNiVCteT6Cow==`, $14.99). | PASS (evidence reconciliation); founder-dashboard cleanup unchanged |
| T-49 | Licensing evidence re-check | Re-extracted PDF text: B12-002 4 pages/1,738 words, no license/resale terms; B12-005 8 pages/3,371 words, one restriction on page 8 ("do not resell or redistribute the files"), no affirmative grant; B12-008 terms are subject-matter words (driver's license/vehicle licence); B12-010 `licence` is subject-matter. No standalone EULA/terms/catalog license field; B12-002 and B12-008 report covers have `UNKNOWN` provenance. | HOLD - no verified commercial-release grant; B12-005 restriction is material |
| T-50 | Final read-only verification after this pass | `pytest` over catalog sync, catalog integrity, commercial reconciliation, doctrine layers, storefront = `146 passed, 2 subtests`; `check_doctrine.py` `ok: true`; `storefront_commercial_check.py` `PASS` (80 cards, 75 active, 3 held, 72 distinct active, 0 findings); `git diff --check` exit `0`. `check_b12_integrity.py` still exits `1` with B12-008 XLSX/PDF hash+size drift only; baseline intentionally not rewritten. | PASS (tests/gates); B12 integrity HOLD unchanged |

Current publication boundary remains unchanged: B12-002/005/008/010 are
`NOT_GRANTED`; no listing action was taken. `FACTORY_LIVE_PUBLISH=false` was
not changed; no commit or push was made.

## Addendum 3 - 2026-10-22 release-identity resolution (B12-002 / B12-008)

Scope unchanged: `TOTAL_NEW_SPEND=$0`, no publication, no account change, no
finance write, no price change, no listing action. Evidence for both rows is in
`reports/B12-002/IDENTITY_AND_PRICE_PROVENANCE_2026-10-22.json` and
`reports/B12-008/FILE_IDENTITY_RESOLUTION_2026-10-22.json`.

| ID | Item | Evidence | Status |
|---|---|---|---|
| T-51 | B12-002 PDF identity and Git line-ending corruption | The worktree PDF `2f047f5a...` / 11,503 B is an exact CRLF conversion of the gate-tested HEAD PDF `273e05c5...` / 11,360 B: 143 LF became 143 CRLF, and replacing CRLF with LF reproduces `273e05c5...` byte-for-byte. Extracted text is identical (4 pages, 1,738 words) and the gate/QA/phase8/product-pipeline records all point to `273e05c5...`; the extra CR bytes left the PDF xref offsets stale, which explains pypdf's incorrect-startxref warning. Root cause: `core.autocrlf=true` plus no `.gitattributes` rule marking PDFs non-text. The PDF was restored to `273e05c5...` / 11,360 B and `reports/CYCLE104/LISTING_PAYLOADS_B12.json` was regenerated locally (0 network calls, 0 publications); pypdf now parses without the warning and `tests/test_b12_listing_payloads.py` passes 9/9. This was not a new product version. | PASS - canonical artifact restored |
| T-52 | B12-008 file-identity baseline | Current PDF `76907497...` / 17,945 B / 7 pages / 3,288 words and XLSX `89cc4704...` / 17,408 B / 7 sheets / 130 formulas match `FINAL_RELEASE_RECORD_2026-10-20.json`, `GATE_FINAL_2026-10-20.json`, and `WORKBOOK_QA_2026-10-22.json`. The old `246bc6fc...` / 17,339 B / 6 pages and `48225a83...` / 16,860 B / 129 formulas baseline predates the late Cycle-106 review repairs. `scripts/check_b12_integrity.py` was re-baselined only after that proof; it now returns `B12 integrity: OK (10 prep items, 5 baselines)`. No product file was overwritten. | PASS - drift resolved as stale baseline |
| O-05 | B12-008 current state | Identity portion is closed by T-52. The live `$18` vs `$29` price decision, stale registry/prep/phase8 state, and absent founder authorization remain HOLD under T-39/FQ-07. | HOLD - founder price/state decision only |

T-50's statement that `check_b12_integrity.py` still exits 1 is superseded by
T-52. The previously reported focused test results remain valid for the code
they exercised; `scripts/check_b12_integrity.py` exit 0 is the new current
result. B12-002, B12-005, B12-008, and B12-010 remain `NOT_GRANTED`.

The Git-wide condition still exists for any repository without binary
attributes. In this worktree a parallel 2026-10-22 change added `.gitattributes`
marking PDF/XLSX/DOCX/ZIP/image/font types `binary`, and normalized the tracked
PDFs back to their committed LF bytes. That fix is not this pass's change, but
it changes the identity facts below.

| ID | Item | Evidence | Status |
|---|---|---|---|
| T-53 | B12-005/B12-010 CRLF identity correction | After the `.gitattributes` normalization, B12-005 is `246268d4...` / 20,146 B and B12-010 is `b7ad0849...` / 45,453 B, both byte-identical to `HEAD`. Their former `a7b11fbc...` / 20,365 B and `96468130...` / 45,838 B files were CRLF conversions: 219 and 385 inserted CR bytes respectively. `reports/CYCLE104/LISTING_PAYLOADS_B12.json` was regenerated to the canonical hashes. `reports/B12-005/QA_FACTS_2026-10-22.json` already covers both byte variants and explicitly identifies the canonical LF blob, so B12-005's QA identity is valid. `reports/B12-010/MANIFEST_2026-10-19.json`, `reports/B12-010/QA_FACTS_2026-10-21.json`, and `tests/test_b12_010_workbook.py` still cite the CRLF hash and must be re-bound before B12-010 is authorized. `tests/test_b12_010_workbook.py` currently fails one canonical-artifact assertion (`45,453 != 45,838`) for exactly this reason. No content, price, or publication change was made. | HOLD - B12-005 QA valid on canonical; B12-010 manifest/QA identity refresh required |

The focused suite in this pass therefore reports `176 passed, 1 failed` (the
B12-010 stale-hash assertion), not a clean 177. The failure is a known identity
bookkeeping gap, not a content regression and not caused by B12-002.

## Addendum 4 - 2026-10-22 stale-reference audit, O-02 closure, test classification

Scope unchanged: `TOTAL_NEW_SPEND=$0`, no publication, no account change, no
finance write, no product file changed, no price or listing action. Only
`config/reality.json` was edited (schema completion below). This addendum
supersedes `T-33`/`T-34`'s hash claim, `O-02`, and `T-53`'s B12-010 item; the
earlier rows are retained as history.

| ID | Item | Evidence | Status |
|---|---|---|---|
| T-54 | Four "stale reference" audit | `reports/CYCLE104/LISTING_PAYLOADS_B12.json` has one commit (`b1a8ffb`) and never contained `2f047f5a...` or `a7b11fbc...`, so `T-33`/`T-34`'s claim that those values matched a manifest sync is **false** and is superseded by `T-51`/`T-53`. `reports/CYCLE105/ARTIFACT_QA.json` is a dated scan (`generated_at 2026-10-21T09:51:14Z`); its hashes were the true worktree bytes at scan time, so it is a historical snapshot, not a current-state claim, and is left unchanged. `reports/B12-005/QA_FACTS_2026-10-22.json` (untracked, hand-authored) recorded a true pre-normalization observation; its `checks.worktree_is_crlf_normalization_of_committed_blob` is no longer a true current-state assertion after the `.gitattributes` normalization, but its identity conclusion (canonical LF blob `246268d4...`) remains correct, so it is left unchanged and explained here. `data/operational_history.json` is a generated current-state file consumed by `doctrine_review.py`, `handoffs.py`, and `business_arms.py`; regenerating it would also rewrite `registry_state` (B12-001/003/004 to `PUBLISHED_AND_VERIFIED`, products 5-8 to `QA_FAIL__NOT_LOCAL_READY`), importing unverified publication state that contradicts `config/reality.json`'s `published_books: []`. It is left **unchanged (HOLD)**; its two hash strings are stale but its regenerator is currently unsafe to run | PASS (audit); T-33/T-34 superseded; `operational_history.json` HOLD |
| T-55 | O-02 content depth | The scored rule is `price x 100` words (`src/quality/quality_enforcer.py`, `WORDS_PER_DOLLAR`), not a 1,900-2,900 range. Current PDFs, measured with `pypdf`: B12-006 3,352 words vs 2,900; B12-007 2,808 vs 1,900; B12-008 3,288 vs 2,900; B12-009 2,766 vs 1,900. The Cycle-106 rebuild (`reports/CYCLE106/B12-006_REPAIR_2026-10-19.md`, `B12-007_008_009_REPAIR_2026-10-20.md`) recorded `content_quality PASS 100` on all four, and `tests/test_b12_006_repair.py` / `tests/test_b12_007_008_009_repair.py` pass (73 tests). The `233-273 words` figures were pre-repair Cycle-104 snapshots | CLOSED - PASS; no product file changed in this pass |
| T-56 | `config/reality.json` required fields | Added the nine fields governance requires, as honest absence states only: `commercial_proof: UNKNOWN`, `scale_level: 0`, `repeatability: UNPROVEN`, `pmf/predictable_revenue/recurring_revenue/saas_validation: UNKNOWN`, `scale_authorization/portfolio_expansion: NOT_GRANTED`, plus `_commercial_state_note`. Pre-edit SHA-256 `1d7393c6...` / 634 B (`HEAD` bytes); post-edit `a9cfa4e7...` / 1,286 B. `data/verified_transactions.jsonl` does not exist, `published_books` is still `[]`, and no field asserts a sale, PMF, repeatability, or authorization. `tests/test_production_wiring.py` now passes. The untracked `backup_recovery_visibility.py::PROTECTED_BASELINE` was already stale (`1918bdc6...` vs live `1d7393c6...`) and its test suite was already 4-failed before this edit; refreshing that baseline belongs to its owner | PASS (schema); protected-file baseline for its owner to refresh |
| T-57 | Pre-existing failing test groups classified | (a) `test_genome_finds_registered_product` — DATA ABSENCE: `PROD-5214fb83a464299d` appears in neither the worktree (5,917 rows) nor `HEAD` (5,053 rows) `books/_generation_log.jsonl`; the artifact is Claude-authored (ADR-022), so a pipeline log entry never existed. (b) `test_market_evidence_not_gf_sale` — DATA DRIFT: 0 of 3,097 decision snapshots carry `payment_evidence`; the test's lowercase niche also does not match the recorded title-case niches; the 3 real records live in `data/market_evidence.jsonl`. (c) `test_no_autopublish_path` — UNTRACKED PARALLEL WORK: `affiliate/publish_queue.py` is untracked (`??`), has no importer anywhere, and is marked "create-then-enable (parallel-owned)" at `scripts/first_sale_orchestrator.py:1416`; its `retry_queue()` calls `create_product` + `enable_product` with no gate. Left unchanged because it is another session's in-flight file; flagged as a P0 safety finding (the standing `.env` `FACTORY_LIVE_PUBLISH=false` and the module's zero callers are the only current protections). (d) `tests/test_production_wiring.py` failures — CLOSED by T-56 | (a)(b) PRE-EXISTING, unchanged; (c) PRE-EXISTING, owner action required; (d) CLOSED |
| T-53 | B12-010 stale identity | Superseded by parallel uncommitted work: `tests/test_b12_010_workbook.py` now passes 22/22, and `reports/B12-010/QA_FACTS_2026-10-21.json` (untracked) cites canonical `b7ad0849...` / 45,453 B while retaining `96468130...` as historical. Neither file is part of this pass | CLOSED (parallel work); pending that work's own commit |

The publication boundary is unchanged: B12-002/005/008/010 remain `NOT_GRANTED`,
`FACTORY_LIVE_PUBLISH=false` was re-read and not changed, and no commit or push
was made in this addendum.
