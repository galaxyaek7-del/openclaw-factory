# B12-001 — final publication checklist (Cycle 88, 2026-10-17)

> **Superseded (Cycle 94):** the workbook was repaired again (input validation, guarded outputs). For the current file and the action requested, see `APPROVAL_PACKET_CYCLE94.md`.

**Publication: LOCKED.** The factory does not publish (FACTORY_LIVE_PUBLISH=false). The unlock phrase is "APPROVE B12-001 PUBLISH", and after it the founder publishes by hand.

## Draft content (from `reports/B12-001/PUBLISH_NOW.md`)
- **Title:** Freelancer Rate & Raise Calculator
- **Price:** $14.99. This is a price hypothesis, not proof of the optimal price; there are no sales yet.
- **Deliverable:** `books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx` (repaired 2026-10-17, see below).
- **Cover:** `reports/B12-001/cover.png` (1280×720).
- **Tags:** freelancing, pricing, rate calculator, consultant, spreadsheet, raise, excel template, solo consultant.
- **Description:** in PUBLISH_NOW.md, Step 4, unchanged by this cycle.

## Deliverable verification (Excel 16 recalculation on a copy; file tester; openpyxl)
- [x] **Contents:** 4 sheets exist (Inputs, ClientMix, RaisePlanner, README). No macros, no external links.
- [x] **Inputs:** the 6 inputs match the description (take-home pay, tax buffer, expenses, billable weeks, billable hours, safety margin).
- [x] **Arithmetic:** in Excel, the worked example gives $104.60/hr minimum and $120.29/hr with the 15% margin. No error cells.
- [x] **Colours:** the README's claims hold (white inputs, blue computed cells, yellow EXAMPLE rows).
- [x] **Fixed: percentage inputs displayed as 0.** Tax buffer (C3) and safety margin (C7) had format `#,##0`, so 30% and 15% showed as "0" and a buyer would likely type 30. Now `0%`.
- [x] **Fixed: RaisePlanner ignored the user's rate.** D2 was `=95*(1+C2)`, a hardcoded 95, and D3 had no formula. Both now use `Inputs!$D$10`. Verified: changing take-home pay changes the raise targets.
- [x] **Fixed: gross revenue (D8) was unformatted** (120285.714…); now shown in $.
- **Original file kept:** `books/batch12/_pre_cycle88_fix/`.
- **New sha256:** `09410945234ee431bf970cb77ad2ca21424e7c0cf6a64731c04f30c03953e4d3`. GATE_FINAL_2026-10-17.json records the old hash.
- [ ] **Not tested:** LibreOffice and Google Sheets. The formulas are plain arithmetic plus one cross-sheet reference, so they should work, but this is not verified.

## Claims audit
- **Description (PUBLISH_NOW Step 4):** no claim about customer outcomes. "No sales recorded yet, no reviews" is true.
  - "Rank every client…" relies on the README's step "sort by Effective rank"; the sheet computes the score, and the buyer sorts.
- **Unverified line:** "Support: reply to your Gumroad receipt email." Whether replies reach you depends on your Gumroad settings. Please confirm.
- **Fixed in `listing_content.md`:** it called $120.29 the "computed minimum … plus a margin" (the margin counted twice). It now says $104.60 minimum and $120.29 with the margin.
- **Fixed in `affiliate_kit.md` (draft post, not posted):** "I ran my costs through this sheet" was a testimonial built on example defaults, with the wrong minimum. It now says "worked example" and uses the correct figures.
- **`measurable_value`:** stays UNKNOWN in `data/product_batch_12.json`. No measured customer outcome exists.

## What "100 / 100 / 70" means (src/quality/quality_enforcer.py)
- **Core value, 100:** five checks, all passed, with weights 25 + 25 + 25 + 15 + 10 = 100:
  - audience is specific (≥ 3 words, not "everyone");
  - problem is stated (≥ 6 words);
  - outcome text is stated (≥ 6 words);
  - title is specific (≥ 3 words, ≤ 60 chars);
  - price > 0.

  These are presence and length checks, not a judgement of value.
- **Content quality, 100:** five checks, all passed:
  - files open cleanly (30);
  - depth (40): for a spreadsheet, ≥ 2 sheets and ≥ 5 formulas;
  - no placeholders (10);
  - no mojibake (10);
  - instructions present (10).

  This structural check **passed even with the display and RaisePlanner bugs above**. It doesn't test usability.
- **Market reality, 70 out of 100 (threshold 65):** what passed: three, two and one sourced competitor prices (10 + 15 + 15), and the price is within 1.10× the highest sourced price (30). What did not: **proof of payment (40), which is absent.**

  This shows comparable products exist at comparable prices. It does not show that anyone buys B12-001.
- **Verdict APPROVED:** every layer is at or above its threshold (70 / 70 / 65).

## Before going live (founder)
- [ ] Confirm the three competitor links in `data/evidence/b12_competitors.json`.
- [ ] Confirm that support replies to Gumroad receipts reach you.
- [ ] Create the draft (PUBLISH_NOW.md), using the **repaired** xlsx and the 1280×720 cover. Send the draft link for review.
- [ ] Say "APPROVE B12-001 PUBLISH", then publish by hand.
