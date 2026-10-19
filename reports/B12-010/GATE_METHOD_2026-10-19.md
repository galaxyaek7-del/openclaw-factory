# B12-010 Gate Method — what "APPROVED 100/100/70 at $15.00" actually means

**Recorded:** 2026-10-19 (Cycle 101)
**Engine:** `src/quality/quality_enforcer.py::inspect(stage="full")`
**Product:** B12-010 Nonprofit Grant Pipeline Tracker

This document exists because a score without its definition is not evidence. Every
number below is reproduced from the shipped code, not from memory or from an ADR.

## 1. The three quality layers

`THRESHOLDS = {"core_value": 70, "content_quality": 70, "market_reality": 65}`.
A layer passes at or above its threshold. Anything other than `APPROVED` blocks —
there is no override argument in `inspect()`.

### Layer 1 — Core Value (pre-production, weighted booleans)

| Check | Weight | What makes it true |
|---|---|---|
| `audience_specific` | 25 | audience present, at least 3 words, not a generic phrase |
| `problem_stated` | 25 | problem has at least 6 words |
| `outcome_stated` | 25 | outcome/description has at least 6 words |
| `title_specific` | 15 | title is 3–60 words |
| `priced` | 10 | price is a positive number |

Score = sum of passing weights. **B12-010 = 100/100** (all five true).
`core_value < 40` is `KILL`, regardless of other layers.

### Layer 2 — Content Quality (post-production, files on disk)

| Check | Weight | What makes it true |
|---|---|---|
| `files_open_cleanly` | 30 | every file passes `file_testing_engine.test_file()` |
| `depth_sufficient` | 40 | text words ≥ price × 100; and, when a workbook is present, ≥ 2 sheets and ≥ 5 formulas |
| `no_placeholders` | 10 | no `_PLACEHOLDER` match in the extracted text |
| `no_mojibake` | 10 | zero mojibake hits |
| `instructions_present` | 10 | text matches how-to-use / instructions / getting started / quick start / readme / step 1 |

A broken file fails the layer **regardless of score**.
**B12-010 = 100/100**: 8,198 PDF words + 8,324 including sheet text against
$15.00 × 100 = 1,500 required; 9 sheets; 427 formulas; 0 placeholders; 0 mojibake.

### Layer 3 — Market Reality (evidence, weighted booleans)

| Check | Weight | What makes it true |
|---|---|---|
| `payment_evidence` | 40 | `market_evidence.get_payment_evidence(niche)` returns at least one record |
| `three_sourced_competitors` | 10 | ≥ 3 competitors with a numeric price **and** an http(s) source URL |
| `two_sourced_competitors` | 15 | ≥ 2 such competitors |
| `one_sourced_competitor` | 15 | ≥ 1 such competitor |
| `price_within_market` | 30 | price ≤ 1.10 × the highest sourced comparable |

**B12-010 = 70 points against a threshold of 65.** Nine sourced competitors (a
tenth page was opened but rendered no price and is recorded `NOT_READ`); no
payment evidence exists for this niche, so the 40-point `payment_evidence` check
is the only miss (10 + 15 + 15 + 30 = 70). That absence is disclosed in the gate
record and in the listing copy; it is not inferred or fabricated.

## 2. What "passes all mandatory gates" adds beyond the three layers

`quality_enforcer` alone does **not** apply market realism, and
`economics.evaluate()` alone does **not** fold market realism in. The pricing rule
requires **all three** of:

1. `quality_gate.verdict == "APPROVED"` (every layer that ran passed), and
2. `economics.evaluate(...).approved == True` — on this run net profit after the
   0.90 royalty must clear the configured floor ($2.50 in the recorded gate), and
3. `economics.market_realism_check(price, page_count=17, platform="gumroad_digital")`
   must return `(True, ...)`.

The page policy is the binding constraint here: at 17 pages the ceiling is
`min($1.00 × 17, $15.00)` = **$15.00**. At $17.99 and $19.97 the quality layers
are identical (100/100/70), economics still approves, and market realism alone
rejects them. `schemas/product.py::from_jsonl_record()` would silently re-price
such a manifest to $15.00 on the auto-distribution path, so the cap is enforced
deliberately here rather than bypassed by the first-sale path.

## 3. How the price was chosen

Candidates tested: `$19.97, $17.99, $15.00, $14.99, $12.99`.

| Price | core | content | market | economics | market realism | Passes all |
|---|---|---|---|---|---|---|
| $19.97 | 100 | 100 | 70 | PASS ($17.97 net) | FAIL (ceiling $15.00) | no |
| $17.99 | 100 | 100 | 70 | PASS ($16.19 net) | FAIL (ceiling $15.00) | no |
| **$15.00** | 100 | 100 | 70 | PASS ($13.50 net) | PASS | **yes** |
| $14.99 | 100 | 100 | 70 | PASS | PASS | yes |
| $12.99 | 100 | 100 | 70 | PASS | PASS | yes |

Rule: **highest price that passes every mandatory check**. That is $15.00.

Two honest notes:

- The policy ceiling is not the only support for $15.00. A comparable with roughly
  981 visible reviews sits at exactly $15.00 in the observed cluster
  ($6.98–$19.97 for single-file workbooks). The price stands without appealing to
  the ceiling.
- Reaching 30 pages would raise the ceiling, but would need roughly 6,000 more
  words. Padding a guide to unlock a price is prohibited. $15.00 is the honest
  price for a 17-page guide with 8,198 words.

## 4. What the gate does not prove

- **No payment evidence for this niche.** The 40-point check is honestly empty.
  Demand is inferred from listed comparables and visible review counts, not from
  a recorded purchase of this specific product.
- **No sale, no customer, no review.** `config/reality.json` still records
  `published_books: []` and verified revenue is $0.00.
- **Google Sheets import is unverified.** The workbook is Excel-native and its
  formulas were recalculated by real Excel 16.0 (Cycle 101,
  `reports/B12-010/NATIVE_RECALC_EXCEL_2026-10-19.json`); per-version Sheets
  import behaviour has not been tested and is disclosed in the listing copy.
- **Founder authorization is absent.** `price_usd` here is derived by the standing
  rule; `GATE_FINAL.founder_decision.price_usd` is `null`.
