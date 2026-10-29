# Research brief (sample): what a US trademark costs a do-it-yourself filer

Sample deliverable for the Research and Data arm. Retrieved 2026-10-29. Not legal advice.
Data product: `data_products/releases/uspto-trademark-fees/2026-10-29/` (CSV, data card PASS).

## Findings

| Finding | Evidence | Class |
|---|---|---|
| One class costs $350 to file electronically, $850 on paper | USPTO fee schedule, codes 7017 / 6001 | OBSERVED |
| Surcharges: $100 insufficient information, $200 free-form goods/services text, $200 per extra 1,000 characters | codes 7018, 7019, 7020 | OBSERVED |
| Intent-to-use path adds $150 for the statement of use and $125 per six-month extension (electronic); $250 and $225 on paper | codes 7003, 7004, 6003, 6004 | OBSERVED |
| Year 5-6 and 9-10 maintenance: $325 per class each (electronic) | codes 7205, 7201 | OBSERVED |
| The schedule page states "Effective January 19, 2025 (Last revised August 14, 2026)"; law-firm alerts give January 18 | USPTO page vs Reed Smith / Mondaq alerts | OBSERVED (discrepancy recorded, not resolved) |
| A careful one-class intent-to-use filing with one extension costs $350 + $150 + $125 = $625 in fees before year 5 | arithmetic on the rows above | DERIVED |
| A careless one with free-form text and an insufficient-information surcharge adds $300 to that | arithmetic | DERIVED |

Source register: USPTO fee schedule,
<https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule>, read
2026-10-29, public domain; secondary (cross-check only): law-firm fee alerts from Reed Smith,
Mondaq and Perkins Coie (January 2025).

## What a buyer would receive

This brief (one page), the CSV with fee codes, both filing methods and source/date per row, and
a change note whenever the USPTO revises the schedule.

## Honest assessment of the offer

- Free alternatives exist and are good: the USPTO page itself and law-firm alerts (OBSERVED).
  A paid brief on fees alone is weak.
- What is not free in one place: the fee table kept current as data, with change history,
  in a form a tool or a seller's cost planner can read. That is the data-product angle.
- The factory already found a real defect with this exact data: one of its own live guides
  quoted paper fees where electronic ones apply (repair prepared, 2026-10-29).

## Pricing hypothesis (UNKNOWN, no buyer evidence)

Free CSV with a paid change-alert subscription ($3-5/month) for template sellers and legal-tech
builders. No price observation exists for a comparable feed; this is a hypothesis to test.

## Zero-spend demand test

Publish the CSV and this brief free on the site (founder approval), with one field: "e-mail me
when the schedule changes". Count sign-ups over 60 days. Continue at 20+ sign-ups; stop below 5.
(Requires the recorded public intake that does not exist yet.)

## Recurring work

Check the schedule page monthly: about 15 minutes, plus a re-release when a fee changes
(INFERRED; no history yet). The data card's refresh interval is 30 days, so a stale release is
flagged automatically.
