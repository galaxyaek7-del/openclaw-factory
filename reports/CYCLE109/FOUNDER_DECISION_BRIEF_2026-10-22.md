# Founder Decision Brief — 2026-10-22 (Cycle 109)

One page, three decisions. Nothing has been applied: no price change, no
license added, no listing created, no publish, no spend. O-02 is evidence-only
and needs no approval.

## O-02 — Content depth (CLOSED, no decision needed)

| Product | Actual words | Required | Result |
|---|---:|---:|---|
| B12-006 | 3,353 | 2,900 | PASS |
| B12-007 | 2,817 | 1,900 | PASS |
| B12-008 | 3,280 | 2,900 | PASS |
| B12-009 | 2,729 | 1,900 | PASS |

Content-quality score: **100 PASS**. Overall B12 batch status remains
`BLOCKED_MISSING_DATA` because `market_reality` is still missing for the batch;
that is a market-evidence gap, not a content-depth failure. No content change
is proposed.

## O-05 — B12-008 price (DECISION)

Conflicting records:

| Record | Price | State |
|---|---:|---|
| `data/product_batch_12.json` | $29 | `QA_FAIL__NOT_LOCAL_READY` |
| `data/product_batch_12_gumroad_prep.json` | $29 proposed | `QA_FAIL__NOT_LOCAL_READY` |
| Phase 8 listing package | $29 | — |
| Final release record | $18 | `READY_FOR_AUTHORIZATION` |
| Gate at $18 | — | APPROVED, market 70 |
| Gate at $29 | — | NOT_READY, `market_reality 40 < 65` |

Direct probes: $18.00 and $18.70 pass; $18.71 and $19.00 fail. The gate script
hardcodes `SUPPORTED_PRICE=18.0`, so $18 is supported but not proven maximal;
$18.70 is the highest tested passing value.

Options:

- **A. $18.00 — recommended.** Gate-approved, integer, already present in the
  final release record.
- **B. $18.70.** Highest tested pass, but not recorded as approved anywhere and
  breaks the integer-price convention.
- **C. $29.00.** Do not list; fails current market reality.

If A is approved, the registry and Gumroad prep must be corrected to $18.00 and
the stale `QA_FAIL__NOT_LOCAL_READY` state must be updated from the existing
QA evidence. That is a state correction, not a new claim.

## O-06 — License terms (DECISION)

Current product-specific evidence: B12-002 `UNKNOWN_NO_TERMS`; B12-005
`PARTIAL_RESTRICTION_ONLY` ("do not resell or redistribute the files");
B12-008 none; B12-010 no terms. No product has a complete license.

Draft for review only — **not legal advice, not applied**:

> **License and permitted use.** Purchase grants one individual a
> non-exclusive, non-transferable right to use the delivered files for that
> individual's own personal or internal professional work. You may print or
> store the files for your own use. You may not resell, redistribute, publish,
> sublicense, share, or transfer the files, or include them in a product or
> service offered to others. No ownership of the underlying content is
> transferred. The files are provided for informational and operational
> planning purposes and are not legal, tax, or financial advice.

Decision requested: approve as-is, edit, or keep on HOLD. If approved, the same
text must be added to all four B12 products, recorded in a `license` field, and
followed by artifact QA because the delivered bundle changes.

## Required order after approval

1. Set the approved price in registry + Gumroad prep + Phase 8 package.
2. Correct the stale registry state; re-run `scripts/check_b12_integrity.py`.
3. Add the approved license text; re-run artifact QA.
4. Obtain explicit listing authorization for the exact new artifact hashes.
5. Only then enable a live listing — still blocked by
   `FACTORY_LIVE_PUBLISH=false` and the write gate until separately authorized.

## Current status

`HOLD_FOUNDER_PRICE_AND_TERMS_DECISION`. No sale is possible today, and no
customer-facing claim of a final price or license has been made.
