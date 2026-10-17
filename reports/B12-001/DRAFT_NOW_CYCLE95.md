# B12-001 — Create the UNPUBLISHED draft (manual only), Cycle 95

**This asks for one thing: create a new product as a DRAFT in the Gumroad dashboard and leave it
unpublished.** It is not a request to publish. Publishing is a separate, later approval
(`APPROVE B12-001 PUBLISH`), and the factory-wide switch stays `FACTORY_LIVE_PUBLISH=false`.

**No API.** A previous API create came back *published and publicly visible* and the integration has
no delete/archive endpoint — so the draft must be created by hand, where you control the publish toggle.

Source of truth: `books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx`
(8,922 B, sha256 `aee8fc0b100345e7abc6e8a41487ddf551b5b7f235c6f4324827d1c6ab8a092d`).

## Exact final listing fields

| Field | Value |
|---|---|
| Title | `Freelancer Rate & Raise Calculator` |
| Price | `14.99` (USD) — **proposed**, no demand evidence yet |
| Type | Digital product |
| Cover | `reports/B12-001/cover.png` (1280×720, 30,643 B, sha256 `46f7e5eb…ec2c2`) |
| Product file | `books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx` (check it is 8,922 bytes) |
| Tags | `freelancing, pricing, rate calculator, consultant, spreadsheet, raise, excel template, solo consultant` |

> Cover note: two candidate covers exist. Use **`reports/B12-001/cover.png`** (the packet cover).
> Do **not** use `books/covers/B12-001.png` (44,649 B) — that is the file the automated gate would pick.

## Description (paste exactly)

```
Stop guessing your rates. This spreadsheet computes YOUR minimum hourly rate from your own costs: target take-home pay, tax buffer, business expenses, billable weeks and hours, plus a safety margin for scope creep and late payers.

Inside (4 sheets): Inputs (your numbers in, computed rate out), ClientMix (rank every client by revenue-per-hassle and see who to fire first), RaisePlanner (raise only on logged triggers, never on feelings), README (4-step instructions).

New product from Galaxy Forge: no sales recorded yet, no reviews. Arithmetic on your inputs — not financial advice; confirm tax figures with your accountant.

Requires: Excel, LibreOffice Calc (free), or Google Sheets (free upload). Instant XLSX download after purchase. Support: reply to your Gumroad receipt email.
```

## Steps (about 10 minutes)

1. Open **gumroad.com** and log in.
2. Go to **Products → New product → Digital product**.
3. A new product opens in the editor **as a draft** (not publicly visible yet).
4. Set **Name** and **Price** from the table above.
5. Paste the **Description** above.
6. **Content/Files:** upload the `.xlsx`; confirm the size reads **8,922 bytes (8.92 KB)**.
7. **Cover/Thumbnail:** upload `reports/B12-001/cover.png`.
8. Add the **tags** above; set the product type to Digital product.
9. **Save only.** Do **NOT** click **Publish**, **Save and publish**, or any button that makes it live.
   If the editor offers only "Save and continue", use it; if the only button is "Publish", stop and tell me.
10. Leave the page open at the saved draft.

## The precise UI state that proves it is unpublished

A saved draft that is **not** public must satisfy all of:
- The product list (`gumroad.com/products`) shows this product **without** the "Published" state
  (typically shown as a draft / not-published indicator, and the row is not in the public store).
- The editor's publish control is still the **Publish** prompt (i.e. it has not flipped to "Unpublish").
- Opening the product's own public URL (`gumroad.com/l/<permalink>`) in a private window shows it as
  **not available / not for sale**, not a live buy page.

If any of those is not true, the product is live — **unpublish it immediately** (Edit → Unpublish) and tell me.

## What to send back

- The **draft link** (the dashboard/product URL), and
- The **visible publication status** (e.g. "Unpublished/Draft"), and
- (optional) a screenshot of the product list row.

I will not treat the draft as created until you confirm the link and status.

## Honesty notes carried into this draft

- Price `$14.99` is **below** the two verified direct comparables ($19.00; €28 ≈ $31.46) and is a
  **proposal**, not a validated price — there is no demand evidence for B12-001 itself (0 sales).
- Competitor prices are **not** demand validation for this product.
- The description states "no sales recorded yet, no reviews" — keep that sentence; do not add scarcity.

## Status of the automated gate (not used for a manual draft)

The internal 5-gate auto-publisher currently returns **HOLD (3/5)**: G1 content-quality 60 < 70 and
G2 has no accepted price-basis/demand-evidence. That gate governs the *automated* live path only; this
manual draft does not call it. Publishing still needs the separate founder approval phrase.
