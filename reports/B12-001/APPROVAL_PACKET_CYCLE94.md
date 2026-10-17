# B12-001 — Founder approval packet (Cycle 94, 2026-10-17)

**What this packet asks for:** one external action, **creating an unpublished draft by hand in the Gumroad dashboard**.
- It does **not** ask you to publish. Publication remains disabled (`FACTORY_LIVE_PUBLISH=false`) and is a separate, later approval.
- Three different states: draft prepared (done, locally) → draft created (needs you) → published (needs a separate approval).

## Product
- **Name:** Freelancer Rate & Raise Calculator
- **Price:** **$14.99, PROPOSED.** It sits below both direct verified comparables ($19.00; €28 ≈ $31.46). There is no demand proof yet, so it is not a validated price.

## Deliverables (verified 2026-10-17)
| File | Size | sha256 | Checks |
|---|---|---|---|
| `books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx` | 8,922 B | `aee8fc0b100345e7abc6e8a41487ddf551b5b7f235c6f4324827d1c6ab8a092d` | Excel 16 recalculation: $104.60/hr minimum, $120.29/hr with margin; 10 formulas; no macros or external links; file tester PASS; integrity check OK |
| `reports/B12-001/cover.png` | 30,643 B | `46f7e5eb3ad447b66c1d7d431cda10d729a8c5d54222a89d47c87fcee93ec2c2` | 1280×720 RGB, looked at; no price or store address printed |

### Workbook fixes made this cycle (edge cases run in Excel 16)
| Input | Before | Now |
|---|---|---|
| Tax typed as 30 instead of 30% | $2.82/hr, silently | Validation (0–90%) plus the message "Tax buffer must be 90% or less. Type 30% (not 30)." |
| Tax ≥ 100%, negative pay | Negative rates | "Check take-home, tax % (0-90%) and expenses" |
| 0 weeks, 0 hours, text in hours | #DIV/0! / #VALUE! | "Check weeks and hours" |

The raise planner shows "Fix Inputs first" instead of an error. Defaults are unchanged ($120.29/hr).

## Listing copy (paste as is)
Copy everything between the lines:

---
Stop guessing your rates. This spreadsheet computes YOUR minimum hourly rate from your own costs: target take-home pay, tax buffer, business expenses, billable weeks and hours, plus a safety margin for scope creep and late payers.

Inside (4 sheets): Inputs (your numbers in, computed rate out), ClientMix (rank every client by revenue-per-hassle and see who to fire first), RaisePlanner (raise only on logged triggers, never on feelings), README (4-step instructions).

New product from Galaxy Forge: no sales recorded yet, no reviews. Arithmetic on your inputs — not financial advice; confirm tax figures with your accountant.

Requires: Excel, LibreOffice Calc (free), or Google Sheets (free upload). Instant XLSX download after purchase. Support: reply to your Gumroad receipt email.
---

The description does not need the store address. Gumroad shows the listing on aekraft.gumroad.com automatically.

### Claims check
| Claim | Class | Evidence |
|---|---|---|
| Computes a minimum rate from your own costs (6 inputs) | OBSERVED | Excel 16 |
| 4 sheets: Inputs, ClientMix, RaisePlanner, README (4 steps) | OBSERVED | openpyxl |
| ClientMix ranks clients by revenue per hassle | OBSERVED, with a caveat | The sheet computes the score; the README tells the buyer to sort by it |
| RaisePlanner: raise on logged triggers | OBSERVED | Follows the buyer's rate |
| Works in LibreOffice / Google Sheets | INFERRED | Plain functions (IF, AND, ISNUMBER, arithmetic); not tested |
| "Support: reply to your Gumroad receipt email" | UNKNOWN | Depends on your Gumroad settings |
| "No sales recorded yet, no reviews" | OBSERVED | Gumroad sales read: 0 |

## Competitor evidence (re-checked 2026-10-17 20:20 UTC from each page's own price metadata)
| Product | Price | Relevance |
|---|---|---|
| [Freelance Pricing & Proposal Kit](https://ysteriprime.gumroad.com/l/freelance-pricing-proposal-kit) | $19.00 | **Direct:** a rate calculator plus 50 prompts, more content |
| [Earnwise Freelance Business Toolkit](https://earnwise56.gumroad.com/l/pnrxz) | €28 (≈$31.46) | **Direct:** rate and quote calculators |
| [Complete Freelancer Business Toolkit](https://prabha02.gumroad.com/l/jmvqo) | $4.99 | **Weak:** a broad bundle |
| Etsy hourly rate calculator | — | Not evidence (HTTP 403 to automated reads) |

**Remaining uncertainty:** no proof that anyone buys B12-001 itself. A free Google Sheets alternative exists.

## Why the factory can't create the draft
- **Not a safe draft:** on 2026-09-17 a create through the API came back **published and publicly visible**.
- **No undo:** there is no delete or archive endpoint in this integration.
- **Needs the global switch:** a create requires `FACTORY_LIVE_PUBLISH=true`. One-off approvals cover only uploads and description edits.
- **So it stays manual:** the safe path is a draft you create in the dashboard, where you control the publish toggle.

## The exact action requested
In the Gumroad dashboard, create a **new product, leave it unpublished**, and fill in:
1. **Name and price:** as above.
2. **Description:** the listing copy above.
3. **Files:** upload the xlsx (check that it's 8,922 bytes) and the cover.
4. **Tags:** freelancing, pricing, rate calculator, consultant, spreadsheet, raise, excel template, solo consultant.

Then send the draft link for review. Publication is a separate decision made afterwards.
