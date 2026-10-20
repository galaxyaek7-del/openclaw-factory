# Verification Report - Cycle 107

Date: 2026-10-20
Scope: B13-001 repair, discovery-gate repair, affiliate render and attribution.
Every line below was produced by a command run in this session. Nothing is
carried forward from a report that was not re-read.

## Repository

| Item | Value |
|---|---|
| HEAD | `2509aad` "Repair the discovery gate: reject before scoring" |
| Previous | `94c9bde` "Fix B13-001 all-in label and surface the drawn reserve" |
| Remote | `origin/main` = `2509aad` verified with `git ls-remote` |
| Working tree | Parallel tracks remain dirty; only named files were staged |

## Commands and results

| Command | Result |
|---|---|
| `pytest tests/test_b13_001.py tests/test_b13_001_listing_assets.py tests/test_affiliate_campaign_assets.py -q` | 55 passed |
| `pytest tests/test_native_workbook_qa.py -q` | 17 passed |
| `pytest tests/test_discovery_gate_repair.py tests/test_market_discovery_engine.py tests/test_doctrine_layers.py -q` | 89 passed |
| `pytest tests/test_render_and_attribution_integrity.py -q` | 16 passed |
| `python scripts/check_doctrine.py` | exit 0; 8 checks true; doctrine tests 53 passed |
| `python scripts/discovery_intake_retro_cycle107.py` | 3 screened, 3 rejected, 0 qualified |
| `python scripts/render_affiliate_asset.py --check` | exit 0; 2 placeholders; domain systeme.io; disclosure ok |
| `python scripts/render_affiliate_asset.py` | rendered 6,475 bytes to ignored directory |
| `git check-ignore -q drafts/affiliate/rendered/...` | exit 0 |

## B13-001

| Check | Value |
|---|---|
| Workbook | 23,894 bytes, sha256 `6a48ebc859a064ac003a9ae1dc9779ca7f9cf3972bbf7ce5ddc89e2f8ec3cf38` |
| Formula cells | 416 |
| Excel error cells | 0 |
| Workbook QA | PASS, 0 critical, 0 warning |
| Independent value check | 17 fields, 0 mismatches |
| Guide | 41,858 bytes, 15 pages, 8,298 gate words |
| Selected price | $15.00, APPROVED (core 100 / content 100 / market reality 70) |
| Publication state | LOCAL_READY__AWAITS_FOUNDER_LISTING_AUTHORIZATION |

The `Summary!B19` value remains $49,700 by design. It is "revised budget +
reserve left". The former label ("all-in plan") was false because $2,100 had
already been drawn. The fix keeps the arithmetic and the teaching point, and
adds `Summary!B20` "Contingency drawn to date" = $2,100.

## Discovery gate

Three candidates were replayed from recorded evidence, without fetching
anything. EUDR fails G3 and G4 only, with every cited URL retrieved. CBAM and
EU EmpCo fail G1, G2, G3 and G4. All three are rejected at intake with
`scoring_skipped: true`, so no score can override a missing prerequisite.

The replay also records two inconsistencies in the prior cycle rather than
resolving them by guess: "three bot-protected responses" versus "the four
Reddit URLs", and aggregate counts summing to 31 against 29 unique URLs.

## Affiliate

| Check | Value |
|---|---|
| Real commissions | 0 records, $0.00 |
| TEST records | 1, excluded from real totals |
| Clicks | 29, all with null referrer, 0 with source/UTM |
| `FIRST_REAL_DOLLAR` | False |
| Rendered asset contains the real link | Yes, in a gitignored file |
| Rendered asset committed | No |

## Safety flags (read from `.env`, unchanged this cycle)

`FACTORY_LIVE_PUBLISH=false`
`PRODUCTION_AUTHORIZED=false`
`AUTO_PUBLISH_MODE=DISABLED`

No spend, no account creation, no application, no deposit, no publication, no
outbound message.

## What this report does not prove

- That the full test suite passes. It does not; see the pre-existing failures
  listed in `TODO_CLOSURE_REGISTER_2026-10-20.md`.
- That any affiliate link produces a click, a sale, or a commission.
- That B13-001 is publishable today. It is locally ready and unauthorized.
- That a payout can be received in Algeria.
