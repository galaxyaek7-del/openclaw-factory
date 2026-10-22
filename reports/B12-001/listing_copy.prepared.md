# B12-001 — Prepared listing copy (NOT yet sent to the live listing)

Status: **PREPARED / UNAPPLIED**. Applying this to the live listing is a live write and requires authorization.
Product id: `W9FpZXpQB-fNiVCteT6Cow==` — https://aekraft.gumroad.com/l/blayvb
Prepared: 2026-10-18. Every factual claim below is drawn from the real workbook (`books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx`, 4 sheets, 10 formula cells) and the approved price ($14.99).

---

## `description` (ready to send)

Stop guessing your rates. This spreadsheet computes YOUR minimum hourly rate from your own numbers — not from an average pulled off the internet, and not from a rate you picked because someone else charges it.

You enter five things: the take-home pay you actually want, a tax buffer, your real business expenses, your billable weeks per year, and your realistic billable hours per week. The workbook turns those into a floor: the lowest rate you can charge and still hit your target. It then adds a safety margin, because scope creep and late payers are normal, not exceptions.

Four sheets do the work:

- **Inputs** — your figures in, your computed minimum rate out. Change one number and watch the rate move; that is the whole point.
- **ClientMix** — rank every client by revenue per unit of hassle, so you can see plainly which relationships earn their keep and which ones to stop renewing first.
- **RaisePlanner** — raise your prices only when a trigger you logged in advance is met (delivered results, a capacity limit, a new service line). Never on feelings, never on a bad week.
- **README** — a four-step setup, so you are working in a minute, not an afternoon.

It works in Excel, in LibreOffice Calc (free), and in Google Sheets (free upload). Instant XLSX download the moment you buy. Support is by reply to your Gumroad receipt email.

**Straight talk.** This is a new product from Galaxy Forge: no sales recorded yet, no reviews. What it is: arithmetic on your own inputs, done once so you stop re-deriving it every quarter. What it is not: financial advice, tax advice, or a promise about what any client will pay. Confirm tax figures with your accountant.

If your problem is "I still don't know my number," this is the fastest honest fix we could build. If you already have a defensible floor you never cross, you do not need it.

## `tags` (ready to send)

`freelancing, pricing, rate calculator, consultant, spreadsheet, raise, excel template, solo consultant`

## Cover (blocked — not attachable by code today)

A canonical cover exists at `reports/B12-001/cover.png` (1280×720, 30,643 B). The live draft currently has **no** cover (`covers: []`).
**UNKNOWN:** no cover-upload/attach route is documented anywhere in this repo, and this factory does not invent endpoints. Until that is confirmed from Gumroad's docs, attaching the cover is a **dashboard** action (or a documented API path to be found first). Do not fabricate an endpoint.

## What applying this would change (live writes, each needs authorization)

1. `update_product(id, description=<above>)`
2. `update_product(id, tags=[the 8 above])`
3. cover attach — path UNKNOWN (dashboard fallback)

Then, separately: `enable_product(id)` to publish.
