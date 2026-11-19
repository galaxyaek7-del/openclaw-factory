# B13-002 Listing Payload (2026-10-23)

**State:** `LOCAL_READY__AWAITS_FOUNDER_PRICE_DECISION_AND_LISTING_AUTHORIZATION`

- Published: **no**
- Gumroad call made: **no**
- Price: **$19.00** (planning target; not founder-approved)
- Digital net: **$17.10** against a **$2.50** floor
- Premium net: **$17.10** against a **$25.00** floor
- Gate: **APPROVED** (100/100/70)
- Guide: **30 pages**, **12,662 gate words**
- Workbook: **373 formulas**, **17 validations**, **0 Excel errors**
- Independent value check: **PASS**, 16 fields compared, 0 mismatches
- Local listing audit: **LOCAL_CHECKS_PASS__AWAITING_PRICE_AND_PUBLICATION_DECISION**, 0 problems
- Copy claims: **6/6** verified against the workbook and guide
- Observed competitor range: **$2.99–$38.95** from 6 sourced listings

## Why this is not live
No founder price decision and no listing/publication authorization exist. The
read-only gate check returned **DENY**; the Gumroad auth state was stale. This
payload is local evidence, not a publication.

## Files
- `books/batch13/B13-002_grant_endgame_nce_unspent_funds.xlsx` - 31,683 bytes
- `books/batch13/B13-002_grant_endgame_nce_unspent_funds_guide.pdf` - 69,647 bytes
- `reports/B13-002/B13-002.png` - 1280x720

## Listing copy
Full copy: `drafts/b13_002_listing_copy.txt`

Grant Endgame: No-Cost Extension & Unspent Funds Kit

Most grant budgets do not fail because the math is hard. They fail in the last 120 days, when money is spread across lines, commitments are not in the bank balance, and the no-cost-extension notice window is already close.

This kit keeps the end of the award in one place.

Inside the 11-sheet Excel workbook (373 live formulas, no macros):

- Award Profile - award number, funder, period, as-of date, notice deadline, and closeout reporting window
- Budget vs Spend - room for 40 budget lines with original budget, approved transfers, spent, committed, available, percent spent, and an over / on plan / under read on every line
- Unspent Decision - every line needs a named disposition: carry forward, rebudget, return to funder, spend down, or still unallocated
- NCE Planner - a dated task list for the one-time extension, including the notice deadline and the days remaining
- Funder Rules - a register for the funder's own terms beside the federal baseline, so a rule is never assumed from memory
- Rebudget Log - request, approval requirement, from-line, to-line, amount, dates, and status
- Closeout Checklist - 24 closeout tasks with owners, due offsets, status, and evidence
- Communication Log - a dated record of what was sent, to whom, and what came back
- Assumptions - what is excluded, where each number lives, and a note against each item
- Summary - one page with every total, the unallocated balance, overdue tasks, and twelve checks
- Start Here - the steps in order, before any number is overwritten

The workbook ships with a worked example: a $120,000 award, $91,000 spent, $15,500 committed, $13,500 available, and $12,500 of dispositions. It is illustrative, not a real award. Read it, then replace it with your own numbers.

Also included: a 30-page PDF guide. It covers the difference between a balance and an available balance, how to build a line-by-line unspent schedule, how to decide between carryforward, rebudget, return, and spend-down, how the one-time no-cost extension works under 2 CFR 200.308(g)(2), when prior approval is required, how to document a request, how to run closeout under 2 CFR 200.344, and what to do when the notice window is already tight. Worksheets A through K give you a written agenda, a funder-call script, a line-by-line schedule, a decision memo, an NCE request letter, a closeout calendar, and a final review.

Built for Excel. The workbook uses standard formulas only, no macros and no add-ins. LibreOffice Calc and Google Sheets have not been tested by me, so if anything misbehaves, reply to your receipt and I will fix it.

This is a planning and documentation tool, not legal, tax, or financial advice. Your award terms and your funder govern. A no-cost extension is not automatic and is not guaranteed.

New product from Galaxy Forge: no sales recorded yet, no reviews. Support: reply to your Gumroad receipt email.


## Honest gaps
- No payment proof exists for this niche in this factory; the market layer relies on six sourced competitors and a price inside the observed range.
- Four Etsy prices are search-index evidence because direct page loads returned HTTP 403; two non-Etsy prices were read from directly fetched product pages.
- The cover is the only preview image produced. Additional preview images are an explicit gap before a final visual review.
- LibreOffice Calc and Google Sheets are untested.
- No sale, review, or revenue is claimed.
