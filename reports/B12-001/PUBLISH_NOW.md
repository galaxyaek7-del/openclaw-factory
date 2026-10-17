# B12-001 — Publish now (founder steps, about 15 minutes)

**Freelancer Rate & Raise Calculator, $14.99.** Quality gate: **APPROVED**. See `reports/B12-001/GATE_FINAL_2026-10-17.json` (core value 100, content 100, market reality 70).

Before you start:
- The factory does not publish (FACTORY_LIVE_PUBLISH=false). You publish by hand on Gumroad.
- The gate in `PUBLISH_GATE.md` stays LOCKED until you say "APPROVE B12-001 PUBLISH".

## 1. Create the draft
1. Go to gumroad.com/products and click **New product**. Choose a digital product.
2. **Name:** copy the title from `reports/B12-001/LISTING_PACKAGE.md` (section PRODUCT TITLE).
3. **Price:** `14.99` USD.
4. **Description:** copy the FULL DESCRIPTION section from the same file.
5. **Cover:** upload `reports/B12-001/cover.png` (1280×720).
6. **Content:** upload `books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx`. This is the file buyers download.
7. **Tags:** `freelancing, pricing, rate calculator, consultant, spreadsheet, raise, excel template, solo consultant`
8. **URL slug:** try `rate-calculator`. If it is taken, keep what Gumroad gives you, and record the real one.
9. **Save as draft. Do not publish yet.**

Button names are approximate; they were not checked against today's dashboard.

## 2. Check before going live
- The preview shows the right title, $14.99, the cover, and the description without broken formatting.
- The file is attached and opens: download it from the preview, then open it in Excel or Google Sheets.
- `reports/B12-001/gumroad_qa.md` has the full checklist.

## 3. Go live
- Send the draft link here for a quick review, then say **"APPROVE B12-001 PUBLISH"** and click Publish on Gumroad.
- Then reply with the live URL. The factory records it, and the read-only sales check (`scripts/check_gumroad_sales.py`) starts counting real sales.

## What is true today
- **Verified competitor prices:** $19.00, $4.99, €28 (≈$31.46), in `data/evidence/b12_competitors.json`. Please also confirm these links yourself.
- **Proof of payment:** none yet. The first real sale is the evidence the market layer is still waiting for.
- **Sales on the account:** 0 (Gumroad API read, 2026-10-17, `data/revenue/check_2026-10-17.json`).
