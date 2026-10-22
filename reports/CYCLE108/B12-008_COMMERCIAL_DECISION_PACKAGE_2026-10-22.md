# B12-008 Commercial Decision Package - 2026-10-22 (Cycle 108, Phase 7)

One candidate, chosen from existing evidence. Nothing was published, priced,
licensed, or written to a catalog. This package only assembles facts that
already exist and states the founder decisions needed to unblock a sale.

## Why B12-008

| Criterion | Evidence |
|---|---|
| Delivery capability | PDF + XLSX exist and match `FINAL_RELEASE_RECORD_2026-10-20.json` |
| Technical quality | PDF technical + brand checks PASS; native workbook QA PASS at `89cc4704...`, 130 formulas, 0 critical/warning |
| Content depth | 3,280 words vs 2,900 required at $29 (and 1,800 at $18) - PASS |
| Market evidence | Gate market score 70 at $18; 40 at $29 (`market_reality 40 < 65`) |
| Current state | Not in `products.html`, not in `data/catalog.json`; dedicated page is notify-only, marked DRAFT, "proposed, not charged" |
| Legal state | No license/terms anywhere for this product |

B12-002/B12-005/B12-010 are also ready but have no comparable price-gate
evidence. The EU AI Act toolkit has stronger market evidence but is blocked
on Paddle onboarding, which is outside this session's authority.

## The blocker is a decision, not code

| Record | Price | State |
|---|---:|---|
| Registry (`data/product_batch_12.json`) | $29 | `QA_FAIL__NOT_LOCAL_READY` |
| Gumroad prep | $29 | `QA_FAIL__NOT_LOCAL_READY` |
| Phase 8 listing package | $29 | - |
| Final release record | $18 | `READY_FOR_AUTHORIZATION` |
| Gate at $18 | - | APPROVED, market 70 |
| Gate at $29 | - | NOT_READY, market 40 |

Direct read-only probes: $18.00 and $18.70 pass; $18.71 and $19.00 fail.
The gate script hardcodes `SUPPORTED_PRICE=18.0` and does not search, so $18
is gate-supported but is **not proven to be the maximum**. $18.70 is the
highest tested passing price.

The registry state is stale: it still reflects the pre-repair 273-word /
1-formula QA result. Current content is 3,280 words with 130 formulas.

## Decision 1 - price

Options:

- **A. $18.00** - clean integer, gate-approved, conservative. Recommended for
  a first listing because it is already the value in the final release record.
- **B. $18.70** - the highest tested passing price, but not recorded as the
  approved price anywhere and breaks the integer-price convention.
- **C. $29.00** - fails market reality today (score 40). Do not list at $29.

Recommendation: **A ($18.00)**. It is the only price that is both
gate-supported and already present in an existing release record.

## Decision 2 - registry state

If the price is approved, correct `QA_FAIL__NOT_LOCAL_READY` to reflect the
current evidence (native workbook QA PASS, 130 formulas, content depth PASS).
This is a state correction backed by existing reports, not a new claim.

## Decision 3 - license terms (O-06)

No product-specific terms exist. B12-005 has one restriction only ("do not
resell or redistribute the files"). Draft below is a proposal for founder
review - it is not legal advice and has not been applied to any product.

### Draft: Single-User License (v0.1, for review only)

> **License and permitted use.** Purchase grants one individual a
> non-exclusive, non-transferable right to use the delivered files for that
> individual's own personal or internal professional work. You may print or
> store the files for your own use. You may not resell, redistribute, publish,
> sublicense, share, or transfer the files, or include them in a product or
> service offered to others. No ownership of the underlying content is
> transferred. The files are provided for informational and operational
> planning purposes and are not legal, tax, or financial advice.

If approved, the same text should be added to all four B12 products and
recorded in a `license` field so listings cannot silently omit it.

## What would happen after approval (not done now)

1. Set the approved price in registry + Gumroad prep + phase-8 package.
2. Correct the registry state and re-run `scripts/check_b12_integrity.py`.
3. Add the approved license text; re-run artifact QA because the delivered
   bundle changes.
4. Obtain explicit listing authorization for the exact new artifact hashes.
5. Only then enable a live listing - still blocked by
   `FACTORY_LIVE_PUBLISH=false` and the write gate until separately authorized.

## Honest current status

`HOLD_FOUNDER_PRICE_AND_TERMS_DECISION`. No sale is possible today, and no
customer-facing claim of a final price or license has been made.
