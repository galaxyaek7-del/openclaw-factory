# GF-6H — New Markets Product Factory: Acceptance Report

**Mission:** `GF-6H-NEW-MARKETS-PRODUCT-FACTORY-01`
**Date:** 2026-10-20
**Window opened:** 2026-10-20T13:31:13+01:00
**Verdict:** `HOLD` — no product built, because no candidate passed the differentiation gate.
**States kept separate:** `BUILD_COMPLETE` = none · `QA_PASS` = none · `READY_FOR_AUTHORIZATION` = none · `PUBLISHED_VERIFIED` = none · `FIRST_SALE_VERIFIED` = 0

---

## A. Mandate and baseline

The mission was to run one bounded cycle: establish a baseline, discover genuinely new niches with traceable evidence, score them against a 25-point gate (floor 18), enforce a differentiation check against both the market and the existing catalogue, and only then build, QA, and prepare for authorization.

Baseline verified before any work:

| Item | Value |
|---|---|
| Branch | `main` |
| Remote `main` | `fb69405d078ea2847184152aa1a76716175ce029` (in sync) |
| Working tree | 2,134 dirty entries, pre-existing parallel-track surface |
| Factory loop | live (`factory_loop.log`, `data/factory_state.json`) — not disturbed |
| Spend this round | $0.00 |
| New external accounts, credentials, or connections | none |
| Gate thresholds, scopes, approvals weakened | none |
| `FACTORY_LIVE_PUBLISH` | unchanged at `false` |

The mission's own rules were applied literally: no paid accounts, APIs, ads, leads, or scraping; no fabricated research, evidence, tests, or sales; no publication of an unverified deliverable; no silent price or payout change; `git add .` never used.

---

## B. What was discovered

Three candidate niches were probed. Selection was deliberate: each sits in a document-heavy, deadline-or-money-at-stake workflow that a spreadsheet genuinely suits, and each is adjacent to work this factory can execute deterministically.

| Candidate | Buyer | Why it looked promising |
|---|---|---|
| Security deposit disposition tracker | small landlord | Two documented five-figure tenant disputes, deadline mechanics, itemization failure mode, paid products already in market |
| Commercial lease CAM reconciliation and audit | small commercial tenant | Tenants facing $59k–$60k retrospective charges, real professional audit market, genuine multi-step arithmetic |
| Subcontractor COI compliance tracker | small GC / property manager | Expiry-driven, penalty-prone, limits-versus-requirement logic, clear failure mode |

All evidence is recorded with URL and an evidence state in `DISCOVERY_2026-10-20_MARKET_SATURATION.json`. Every entry is `OBSERVED` — read from a real, reachable page during this window — not `INFERRED` or `ESTIMATED`.

The relevant finding is not that demand is absent. Demand is real and documented in all three. The finding is that **supply is already there, and it is free.**

- **Security deposits.** Quire Paper sells a $12 workbook that is a near-exact implementation of the candidate: 40-deposit ledger, itemized deductions, return-deadline engine with days-left and overdue highlighting, dashboard, status lifecycle, dated history. A $39.50 Etsy landlord suite already bundles a deposit tracker, and a $4.99 worksheet already does move-out deductions by room. The mechanisms that would have constituted differentiation — prorated replacement value, deposit-return templates — are separately available free.
- **CAM reconciliation.** CapVeri publishes a complete formula template free, including pro-rata share, gross-up, cumulative and non-cumulative caps with carry-forward, exclusions, prior-year cap validation, and 20 tenants. Sheet Chief published a five-sheet paid tracker on 2026-08-13 that implements almost exactly the candidate specification. Lextract ships a 12-step audit workbook.
- **COI compliance.** Six free templates, one a 51-column seven-sheet engine with a 0–100 compliance score and five-stage escalation, all published as lead magnets for SaaS products.

---

## C. Scoring and verdicts

Rubric, applied identically to all three, out of 25:

`demand 0–5 · willingness-to-pay 0–4 · differentiation vs market 0–5 · differentiation vs catalogue 0–3 · buildability & verifiability 0–3 · risk 0–3 · evidence traceability 0–2`

| Candidate | Demand | WTP | Diff. market | Diff. catalogue | Build | Risk | Trace | **Total** | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| Security deposit tracker | 3 | 4 | **1** | 2 | 3 | 2 | 2 | **17** | REJECTED |
| CAM reconciliation / audit | 4 | 4 | **1** | 3 | 3 | 1 | 2 | **17** | REJECTED |
| COI compliance tracker | 4 | 2 | **0** | 2 | 3 | 3 | 2 | **16** | REJECTED |

The decisive dimension in every case is differentiation against the market, and the scores are low for the same reason: a free, formula-complete incumbent already does the job. Demand was scored down where the need is already met, not where it is absent. For COI, willingness-to-pay is scored 2 rather than 4 because the visible price anchor is $0 and the free templates exist specifically to be outgrown into a subscription.

No candidate reached 18/25. **No build was authorized by the rubric.**

---

## D. What was built

Nothing. This is the deliberate outcome, not an omission.

Building a fourth tracker in a category where three free incumbents already exist would have produced an artifact with no defensible capability gap. The gate exists precisely to prevent that, and the honest output of a discovery cycle that finds nothing is a recorded no-build.

This is also consistent with the standing rule that a build must be preceded by Proof of Payment evidence for the specific product (ADR-121). That evidence was not gathered for any replacement candidate, so even a favourable score would not have authorized generation.

---

## E. Verification performed

| Check | Method | Result |
|---|---|---|
| Baseline and remote parity | `git rev-parse`, `git ls-remote` | in sync at `fb69405` |
| Competitor existence and feature set | direct page reads, live during window | OBSERVED, 16 cited sources |
| Prices | read from live product pages and listing pages | OBSERVED, not estimated |
| Buyer pain | live forum threads with quotations | OBSERVED |
| Differentiation verdict | mechanical comparison of incumbent feature list against candidate specification | failed in all three |
| Spend | no paid service invoked | $0.00 |
| Side effects | no writes to product artefacts, ledgers, or inventory | none |
| Existing test/gate state | unmodified this round | no change |

Limitation, stated plainly: differentiation was assessed from published feature descriptions and product pages, not from downloading and inspecting competitor files. A competitor could be less capable than its marketing claims. That possibility was not verified, and it is the one assumption in this report that a follow-up could test if a founder wanted to pursue one of these categories anyway.

---

## F. Governance and authorization status

Unchanged by this round.

- Publication remains `BLOCKED_BY_AUTHORIZATION`: `create_product` and `enable_product` are outside the scopable operation set, `FACTORY_LIVE_PUBLISH=false`, the Gumroad auth state is stale (2026-10-19T08:03:23), no active scope exists, and all six founder approvals remain `PENDING`.
- Purchasability of every listed product remains `UNKNOWN` — three listings are byte-verified, but completion has never been observed.
- Revenue is unchanged: `data/sales_ledger.jsonl` holds 135 publish-attempt rows and zero sales; `finance_data.json` holds `sales: []`; 82 live Gumroad products, 79 published, 0 sales.
- The market-realism price ceiling remains unresolved across five products at $7.00 policy versus $19–$29 listed. Not touched this round.
- The Python-side claim that KDP is greenfield is stale relative to `channels/kdp_arm.py`; not relevant to this round, not changed.

---

## G. Learning capture and next action

**Structural finding (`DERIVED`).** Single-purpose operational trackers for small businesses are not viable paid digital products in 2026. The category is served by free, formula-complete templates published by SaaS vendors as acquisition funnels. The free template is frequently more feature-complete than a plausible paid alternative, and its commercial purpose is to make the spreadsheet feel insufficient. Competing in that format means competing with free, using the same format, on features the incumbent already has.

**What a paid product must do instead.** It must deliver something a template cannot replicate:

1. assembled interpretation of a dated obligation the buyer cannot safely assemble alone, or
2. a decision the buyer is not equipped to make, or
3. distribution and brand strong enough to overcome a $0 anchor.

The factory's only product with real Proof-of-Payment evidence — the EU AI Act Compliance Toolkit — is in lane 1. That is not a coincidence; it is the only lane in this catalogue where the buyer is paying for judgment, not for a grid.

**Recommended next action.** Direct the next build round at a single dated regulatory or contractual obligation, gather real Proof-of-Payment evidence before any generation, and keep the deterministic-worksheet component as the supporting instrument rather than the product. Do not open a fourth tracker probe; the answer is already established across three independent categories.

**Explicitly not recommended.** Lowering the differentiation floor to 18-minus-one so that a rejected candidate becomes buildable. That converts the gate into decoration.

**Continuation point.** No product is half-built. The next round starts clean at DISCOVERY with a regulatory candidate, and the scoring rubric and gate behavior validated here can be reused unchanged.

---

### Artefacts

- `reports/CYCLE106/DISCOVERY_2026-10-20_MARKET_SATURATION.json` — all three probes, 16 cited sources, scores, verdicts, structural finding
- `reports/CYCLE106/GF-6H_NEW_MARKETS_REPORT_2026-10-20.md` — this report
