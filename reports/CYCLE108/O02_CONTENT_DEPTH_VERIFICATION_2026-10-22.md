# O-02 Content-Depth Verification - 2026-10-22 (Cycle 108, Phase 4)

O-02 is re-verified against the current artifacts with the **production
enforcer itself**, not a separate text splitter. Read-only: `save=False`, no
file, ledger, price or report was written.

## The rule

`src/quality/quality_enforcer.py`:

- `WORDS_PER_DOLLAR = 100` (line 63)
- `need = int(price * WORDS_PER_DOLLAR)` (line 231)
- word tokenizer: `re.findall(r"[^\W_]+", text)` (line 73-74)

There is a **minimum only**; no upper bound exists in the code.

## Authoritative measurement

Command: `quality_enforcer.inspect(product, files=[...], stage="full",
save=False)` with registry prices from `data/product_batch_12.json`.

| Product | Registry price | Required words | Measured words | text_depth_ok | Content-quality layer |
|---|---:|---:|---:|---|---|
| B12-006 | $29 | 2,900 | 3,353 | PASS | PASS 100 |
| B12-007 | $19 | 1,900 | 2,817 | PASS | PASS 100 |
| B12-008 | $29 | 2,900 | 3,280 | PASS | PASS 100 |
| B12-009 | $19 | 1,900 | 2,729 | PASS | PASS 100 |

Overall verdict is `BLOCKED_MISSING_DATA` for all four, caused by the
`market_reality` layer (no payment evidence attached to these products), not
by content depth. The content-quality layer is the one O-02 concerns; it is
PASS 100 on every product.

At the gate-supported B12-008 price of $18 the requirement is 1,800 words;
the current 3,280 passes either price.

## Methodology correction

The Cycle 107 register quoted 3,352 / 2,808 / 3,288 / 2,766. Those came from a
whitespace split of `pypdf` text, not from the enforcer's tokenizer. The
enforcer counts 3,353 / 2,817 / 3,280 / 2,729. The difference is a few tokens
(punctuation handling) and does not change any conclusion. The enforcer's
numbers above are the authoritative ones.

## Pricing consistency

The word requirement is derived from the price passed to the enforcer. The
enforcer was run with the same registry prices used in
`data/product_batch_12.json`. The B12-008 $18-vs-$29 conflict is a separate,
unresolved founder price decision (see
`reports/CYCLE108/B12-008_COMMERCIAL_DECISION_PACKAGE_2026-10-22.md`), not a
content-depth failure.

## Status

`O-02: CLOSED` - rule identified, current artifacts pass it, methodology
disclosed, no upper bound assumed.
