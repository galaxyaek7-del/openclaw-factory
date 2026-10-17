# B12-001 — Zero-Spend Demand Validation Plan

Prepared 2026-10-17. Nothing in this plan has been executed externally.
External publishing/contact requires founder authorization. `TOTAL_NEW_SPEND=$0`.

## Hypothesis
Freelancers who set their own rates will give their email / click through to
evaluate a **free minimum-rate calculator**, and a meaningful fraction will
then consider the paid full product ($29).

## Target customer
Solo freelancers / solo consultants who bill clients for their time and set
their own rates (matches `data/product_batch_12.json` audience and the
Reddit evidence in `DEMAND_EVIDENCE_2026-10-17.json`).

## The smallest free experiment
A **free mini version of the Inputs sheet** ("Minimum Rate Calculator") offered
as a free download, with the full 4-sheet product as the paid upgrade.

| Element | Choice | Why |
|---|---|---|
| Channel | Galaxy Forge public site (`customer_site/`, served at `/site/`) + one honest community post | Existing, free, permitted; no paid ads |
| Demonstration | Free 1-sheet minimum-rate calculator (derived from B12-001 `Inputs`) | Proves value before the ask; mirrors the free competitor |
| Destination | A B12-001 landing page with the honest offer + "$29" CTA | Single measurable conversion point |
| Tracking | Real click counts, real checkout attempts, real completed sales; GSC impressions/CTR | All already instrumentable; no fabrication |
| Assets reused | `reports/B12-001/cover.png`, `LISTING_PACKAGE.md`, `customer_site/` static hosting | Avoids new infrastructure |

## Outcome thresholds (decide, don't linger)
- **SUCCESS** — ≥1 completed, externally verified sale. → advance: keep price, scale the same channel.
- **INCONCLUSIVE / FAIL** — measurable traffic (≥100 qualified visits) but 0 sales. → reprice toward the $12–19 field OR strengthen differentiation.
- **NO TRAFFIC** — <100 qualified visits after a real distribution attempt. → bottleneck is reach, not price; do NOT reprice on zero data.
- **BLOCKED** — channel/account restriction prevents the test. → document the exact restriction; pick the fallback channel.

## Next action per outcome
| Outcome | Next action |
|---|---|
| SUCCESS | Verify repeatability before scaling; raise confidence in the offer |
| INCONCLUSIVE | A/B a lower price ($19) against $29 on the same page |
| NO TRAFFIC | Invest in distribution/audience discovery, not product changes |
| BLOCKED | Record restriction; choose fallback channel |

## What can be prepared autonomously (no external effect)
- The free mini-calculator as a local XLSX/HTML artifact.
- The landing-page draft (static HTML, not deployed).
- Tracking hooks already exist (click/checkout counters).

## What requires founder authorization
- Publishing the landing page or posting to any community.
- Changing the live price.
- Any account/credential action.

---

## Prototype built (CYCLE 84, 2026-10-17)
- Calculator: `prototypes/b12_001_rate_calculator/calculator.py`
  (pure, dependency-free; transparent formulas; validation; declared limitations).
- Landing draft: `prototypes/b12_001_rate_calculator/landing.html`
  (local only; checkout disabled; no testimonials/reviews/claims).
- Tests: `tests/test_rate_calculator_prototype.py` — **17 passed**.
- The draft page accurately describes the deliverables and states the $29 price
  is an unvalidated hypothesis.

## Definition of qualified buyer intent (evidence grading)
| Signal | Grade | Counts as demand? |
|---|---|---|
| Page visit / impression (incl. GSC) | weak | No |
| Free mini-calculator download / email | medium | No (interest only) |
| Clicks a live "$29 buy" button | strong | Partial (intent) |
| Completes checkout + pays | definitive | Yes |
| Refund / complaint | definitive | Yes (negative) |

Only "completes checkout + pays" counts as a **sale**. Record every event with
timestamp, channel, and result — no personal data beyond what the form requires.
No test is "successful" until one completed, externally verifiable payment exists.

## Recording evidence without unnecessary personal data
Append-only local log (clicks, submissions, sales) storing: timestamp, channel,
event type, result. Email only if the user chooses to submit it; never inferred,
never enriched, never shared.

