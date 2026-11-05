# Batch 18: ten higher-value products (2026-11-05)

Founder order (in-session, 2026-11-05): ten products on Gumroad, production, review, publication and pricing, a full cycle, learning from the earlier mistakes, higher value and clearly different from the earlier batches.

## Result (OBSERVED)

All ten are live on aekraft.gumroad.com. Each passed the dry-run audit (every product check PASS), then the live publisher (create, publish, cover, public page, tags all ok). The registry, rebuilt from the live platform, shows all ten as `PUBLIC_LISTING_VERIFIED` at the intended price. The read-only delivery audit shows each has one zip attached, matching the local bundle size, with no thin-deliverable and no missing-promise flag.

| ID | Product | Price | Recalculated cells checked | Guide pages | Workbook bytes | Guide bytes | Listing |
|---|---|---|---|---|---|---|---|
| B18-001 | Contractor Job Costing & WIP Schedule (Over/Under Billing) | $49 | 79 | 6 | 14,830 | 12,652 | https://aekraft.gumroad.com/l/ytaqjk |
| B18-002 | Owner-Operator Cost per Mile & Load Profitability Model | $39 | 90 | 6 | 14,975 | 12,227 | https://aekraft.gumroad.com/l/ryzoro |
| B18-003 | Small Business Valuation & Offer Price Model (SDE, DCF, Assets) | $49 | 30 | 6 | 9,126 | 13,183 | https://aekraft.gumroad.com/l/duzghq |
| B18-004 | Agency Utilization & Capacity Planner (Billable Hours, Bench Cost, Hiring Trigger) | $39 | 107 | 6 | 15,371 | 11,966 | https://aekraft.gumroad.com/l/atynt |
| B18-005 | Equipment Lease vs Buy Model with MACRS Depreciation & Tax Shield (US) | $39 | 93 | 6 | 10,548 | 12,679 | https://aekraft.gumroad.com/l/pgoxt |
| B18-006 | Retirement Drawdown Stress Test: Sequence-of-Returns Scenarios | $39 | 395 | 6 | 12,704 | 12,020 | https://aekraft.gumroad.com/l/rwrcw |
| B18-007 | Brick-and-Mortar Store Opening Feasibility & Break-Even Model | $39 | 205 | 6 | 11,341 | 12,824 | https://aekraft.gumroad.com/l/ogypx |
| B18-008 | Small Farm Crop Enterprise Budget & Break-Even Planner | $29 | 60 | 6 | 11,406 | 12,153 | https://aekraft.gumroad.com/l/zzudjn |
| B18-009 | Wholesale Price Waterfall & Channel Margin Stack Calculator | $29 | 84 | 6 | 14,033 | 12,060 | https://aekraft.gumroad.com/l/yzmmz |
| B18-010 | Digital Course Launch Break-Even Model (Pessimistic, Base, Optimistic) | $29 | 43 | 6 | 9,455 | 11,860 | https://aekraft.gumroad.com/l/joytjk |

Total checks: 1186 independent recalculations (lib/xlsx_eval.py against a separate Python model of the same math).

## Why these products and these prices

- **Different:** earlier batches were calculators ($9-24) and compliance kits ($29-99). Batch 18 is multi-sheet decision models for trades the catalogue did not cover (contractor WIP, trucking, business valuation, agency utilisation, equipment lease vs buy with MACRS, retirement stress test, store opening, farm crop budgets, wholesale channel margins, course launch).
- **Higher value:** $29-$49. This is a tier above the $9-24 calculators, justified by sheet count, scenario analysis and a longer guide. **The price is NOT validated by buyers or by external listings** (see below).

## Mistakes of earlier batches and what was done about each

| Earlier mistake | Source | This batch |
|---|---|---|
| Thin guides (4 pages), 22 thin paid deliverables | delivery audit 2026-10-22 | Guides are 6 pages with worked scenarios, a routine, a checklist, mistakes, glossary and FAQ; the build fails below 6 pages. |
| Numbers typed by hand into guide text | found during this batch | Three guide paragraphs had wrong figures (an SDE of $177,000 instead of $253,000; a retirement stress test where no scenario ever failed; a shop that could never reach break-even). All three examples were corrected and the scenario text is now generated from the model. |
| A formula that counted -24 jobs | caught by the recalculation QA | `COUNTA - COUNTIF("")` replaced; also fixed in the first product, where the cell had no check. |
| Pricing copied from comparables without saying so | batch 14 note | `pricing_evidence` states plainly: no external price was read for this batch (NOT MEASURED); demand WAITING FOR REAL DATA. |
| "$0+" listings that still take money | 2026-10-28 | Every product is priced above zero and pay-what-you-want is false (audit). |
| Listing promises not matched by files | delivery audit | Audit: no PROMISES_* or THIN_* flag on any of the ten. |
| Covers missing | 2026-10-24 | Covers built from each workbook's own example data, pushed to the public repo (only those ten PNGs, one commit), attached by the publisher. |
| 10 products per rolling 24 hours | Gumroad limit | 0 of 10 were used before this batch; all ten now used until the window rolls. |

## Honest limits

- **Sales: 0.** No product in this account has sold, so none of these prices is validated. Whether the new tier sells better than the $9-24 tier is UNKNOWN until a buyer pays.
- **No external price check** was made for this batch (NOT MEASURED).
- **Central Quality Gate was not consulted:** the batch publisher calls the Gumroad publisher directly with a per-product founder approval (recorded in-session from the founder's order). The approvals are in the git-ignored local file `data/publication_approvals.json`.
- **Not built:** per-product site pages (`customer_site/tool-*.html`) and Pinterest pins for batch 18. `data/catalog.json` has not been refreshed, so the registry reports 10 `live_missing_from_catalog` until the daily catalog step runs.
- The guides are written in plain English for a US/UK audience; tax, valuation and retirement products carry a not-advice disclaimer and ask the buyer to verify with a professional.

## Reproduce

`python books/_batch18_src/run.py` (sources are git-ignored: they are the paid product), `python scripts/publish_batch14.py --batch batch18` (dry audit), `--live --only <ids>` after approvals.
