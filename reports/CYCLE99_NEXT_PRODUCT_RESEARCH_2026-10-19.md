# Cycle 99 — Next product research & selection (2026-10-19)

**Founder instruction this round:** keep B12-005 unpublished and research the next product.
**Spend:** $0 (live web search + read-only page inspection only). No listing created, no account touched, no price charged.
**Authorized scope:** research and selection. Nothing here publishes, spends, or changes any founder-gated system.
**Method:** live web search, then inspection of the listings themselves. Every comparable is cited by its
live URL with a verbatim snippet; any page that rendered no price is recorded as `NOT_READ` rather than guessed.
Evidence files: `data/evidence/b12_00{7,8,9,10}_competitors.json`, plus
`reports/B12-010/DEMAND_EVIDENCE_2026-10-19.json` for the recommended product.

---

## 1. The comparison (real observed prices only)

| Candidate | Planned price | Priced comparables found | Observed USD span | Strongest real demand signal | Recommendation |
|---|---|---|---|---|---|
| **B12-007** Digital Declutter & Backup: 30-Day System | $19.00 | 7 | $0–$14.99 (paid: $3.00–$14.99) | 21 ratings (4.8) on a **$0+** checklist | **No** |
| **B12-008** Moving House 8-Week Planner | $29.00 | 8 | $2.24–$29.00 (single product: $2.24–$12.00) | long-lived Etsy listings; review counts not captured on the market page | **No** |
| **B12-009** Pet Sitter Handover Kit | $19.00 | 6 | $1.39–$10.00 | 1 review on a $4.00 single sheet | **No** |
| **B12-010** Nonprofit Grant Pipeline Tracker | $39.00 | 10 | $6.98–$111.25 (single file: $6.98–$19.97) | **982 reviews** at $15.00, **137** at $19.97, **35** at $6.98; a separate comparable states **203 sales** | **YES — recommended** |

Full per-comparable detail, including the exact verbatim quotes and the `NOT_READ` entries, is in the four
evidence files. Nothing in the table is estimated: every number was read off a live page on 2026-10-19.

## 2. Why B12-010

1. **It is the only candidate with volume evidence.** 982 reviews on the exact same product concept and file
   format (a grant-tracker spreadsheet), 137 more at $19.97, 35 at $6.98 — and a comparable that publishes a
   sales count (203 sales, 4.9 from 27 ratings, 1 year on Etsy). The other three candidates top out at
   "someone sells this at a low price".
2. **The price band is where our deliverable can actually live.** Sustained $15.00–$19.97 single-file price
   points, in three formats (Excel, Google Sheets, Notion), including one Gumroad workbook bundle
   (`GRANTFLOW`, $15.92) whose shape — workbook + written guides + sample data — is almost exactly what this
   factory's `build_batch12_*` pipeline already produces.
3. **There is budget above the template tier.** `GrantCompass` sells a 17-resource grant bundle at $67 and
   anchors it against "Hire a Grant Writer $2,000+". Buyers in this niche demonstrably pay for depth.
4. **The category's own disclosure norm matches ours.** `GRANTFLOW` states "This template does not submit
   applications or guarantee funding." We will ship the same class of non-promise, because the market
   already expects it.
5. **The differentiation is computable, not cosmetic.** The most-reviewed entry is a plain tracker. A
   deadline/report-cadence engine with real conditional logic (the same technique B12-005's Pipeline and
   Metrics logic uses) is something a small seller can still win on, and it is verifiable by tests.

## 3. Why not the others — and what would change that

- **B12-007 (declutter/backup).** Paid comparables cluster at $3.49–$14.99, with a large free/PWYW tier, and a
  live product already carries a near-identical title ("The 30-Day Digital Declutter"). The planned $19.00 is
  above every observed paid comparable. *What would change it:* repositioning onto the restore-tested backup
  half, which no observed comparable sells, plus a gated price in the $10–$15 band.
- **B12-008 (moving planner).** A commodity printable: single-product prices $2.24–$12.00, and the only $29.00
  point in the whole category is a **bundle of three** products. Planning $29 for one plan plus one tracker is
  not supported. *What would change it:* bundling 3+ distinct artifacts, priced as a bundle.
- **B12-009 (pet sitter kit).** The cheapest ceiling of the four: $1.39–$10.00, with the deepest observed
  product (a 4-edition binder) at $10. The planned $19.00 has no support at all. *What would change it:* a
  fundamentally deeper product (health records, multi-trip history) priced at ~$10–$12.
- **B12-006 (home-office deduction).** Not compared here: it is **founder-gated** on a tax/legal scope
  decision that has not been made. Researching its market before that decision would not have been actionable,
  so it was deliberately left alone rather than half-researched.

## 4. Price honesty for B12-010

- The manifest price of **$39.00 is not supported** by this evidence. No observed single-file comparable
  sustains $39; the honest comparable band is **$15–$20**, with $67 reachable only as a multi-resource bundle.
- **No price is proposed, derived, approved, or charged now.** The Cycle 99 pricing rule derives the final
  price only after the deliverable is rebuilt to the deep-QA bar and the factory's own gates are run — and the
  page/depth market-realism policy will bind hard for a workbook-plus-guide product.
- The $111.25 Etsy listing (0 sales) is recorded as a caution, not a target: in this niche, price without
  reputation does not sell.

## 5. Defects found and corrected in this round (disclosed, not hidden)

1. **Five future-dated timestamps in code I committed earlier the same session.** `data/product_pipeline.json`
   (top level + the B12-005 record) and three B12-005 gate/QA files carried `2026-10-19T11:10Z` /
   `10:40Z` / `11:05Z` / `10:55Z` — all *later* than real UTC at commit time (the commit was made at
   `2026-10-19T09:57:49Z`). Cause: local system time (+01:00) was labelled as UTC. Corrected to real,
   re-derived UTC values, and each file now carries a `timestamp_corrections` block that **retains the
   original wrong value** so the record is auditable rather than silently rewritten. Note for any future
   automated timestamp scan: those retained originals are intentionally future-dated strings inside that
   block; no live field is future-dated any more.
2. **A BOM in the last commit subject** (`\ufeffB12-003: …`). Cause: PowerShell 5.1 `Set-Content -Encoding UTF8`
   writes a BOM. Cosmetic only, and already pushed; fixing it would require an amend plus a force-push, which
   is not done without explicit instruction. All files written since are BOM-free.

## 6. What this report does NOT claim

- No Galaxy Forge sales and no revenue. `VERIFIED_REVENUE` remains **$0.00**.
- All demand evidence is **other sellers'** listings, not our own traction.
- The 982 figure is a displayed review count (accumulated), not a monthly sales rate.
- Two listings were displayed only in JPY (geo-served pages). No USD conversion is asserted for either, and
  both are excluded from the USD spans above.
- One comparable per candidate could not be read (`NOT_READ`) — recorded explicitly rather than guessed.

## 7. Next steps

1. Rebuild **B12-010** to the deep-QA bar: a written method guide (PDF) plus a workbook whose pipeline,
   deadline and reporting-cadence fields are computed with real conditional logic and sample data — carrying
   the same "does not submit applications or guarantee funding / not legal or financial advice" disclosure the
   category expects.
2. Deep QA → gate → derive the price from the rule (expect the $15–$20 band; $39 only if the rebuild's real
   depth justifies it).
3. Listing package + customer page, then stop. **No publication without a separate, explicit authorization
   for B12-010.**
4. Founder-only items still waiting: B12-005 publication authorization (any time), B12-002 publication,
   B12-006 tax/legal scope decision.
