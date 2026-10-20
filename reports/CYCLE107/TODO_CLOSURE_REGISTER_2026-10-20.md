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
