# Galaxy Forge: company portfolio (2026-10-29)

Galaxy Forge is the company; the factory is its executive engine; the eight doctrine arms are
its commercial engines. This page is the human-readable view. The live data is computed by
`business_arms.py` (evidence status per arm) and `arm_portfolio.py` (stage, model, KPIs,
dependencies, next decision), written to `data/business_arms_state.json` daily, and shown on
the CEO dashboard, tab "الأذرع والقدرات", card "محفظة الشركة". Evidence classes: OBSERVED,
DERIVED, INFERRED, UNKNOWN.

## A. Capability map (OBSERVED in the repository)

| Directive arm | Doctrine arm | Implemented today | Shared capabilities it uses |
|---|---|---|---|
| A Digital products | `digital_products` | 115 products in the registry, 109 live on Gumroad; batch pipeline with independent formula checks; per-product publication gate; delivery audit | product_engineering_qa, catalog_registry, publication_gate, site_and_search, payments, commercial_measurement |
| B Productized AI services | `productized_ai_services` | nothing customer-facing | opportunity_engine, customer_intake |
| C Micro-B2B | `micro_b2b` | spreadsheet-normalization offer + tested delivery engine (`services/spreadsheet_normalization/`) | customer_intake, site_and_search, payments |
| D Research-as-a-service | `research_data_services` | market/competitor intelligence pipelines, data-card format | opportunity_engine, customer_intake |
| E AI operations | `ai_operations` | internal: supervised loop, n8n watchdog, health checks, CI, incident memory | incident_memory, customer_intake |
| F Affiliate intelligence | `affiliate_intelligence` | click tracking with classification, commission ledger, comparison pages | site_and_search, visit_measurement |
| G Data products | `research_data_services` (shared, per doctrine) | data-card format; no packaged dataset | as D |
| H Content and distribution | `content_distribution` | Telegraph articles (live), social draft engine with UTM + QA, Pinterest queue, IndexNow | distribution_engine, experiments, site_and_search |
| I Children's media | `childrens_media_studio` | two verified animatics, rights ledger, QA checklist | publication_gate |
| J New ventures | not an arm | opportunity engine (`trend_to_product/`, `goos.py`, `decision_engine/`) proposes; a new arm needs evidence | opportunity_engine |

Shared capabilities and their state: `arm_portfolio.SHARED_CAPABILITIES`.

## B. Arm assessment (live, 2026-10-29)

| Arm | Evidence status | Stage | Why (evidence) |
|---|---|---|---|
| Digital products | PARTIAL | COMMERCIAL_TEST | 109 listings live, 0 sales; 24 listings deliver less than described (repair prepared) |
| Content and distribution | PARTIAL | VALIDATION | 131 platform views on 8 articles; no attributable click measured |
| Micro-B2B | PARTIAL | BUILD | offer and engine exist; no intake that reaches the factory |
| Children's media | PARTIAL | BUILD | 2 verified animatics; no narration; scripts await native Arabic review |
| Research and data | PARTIAL | DISCOVERY | pipelines, no offer |
| AI operations | PLANNED | DISCOVERY | internal only |
| Productized AI services | PLANNED | DISCOVERY | no implementation |
| Affiliate intelligence | BLOCKED | HOLD | no approved account or tag; 0 outside clicks; payout route from Algeria conditional |

No arm is REVENUE_VERIFIED or OPERATING. Company revenue: $0 (Gumroad, OBSERVED).

## C. Independent commercial tests (one per arm, none waits for another)

| Arm | Cheapest credible test | Success | Failure |
|---|---|---|---|
| Digital products | EXP-B16-007-LI-01: two LinkedIn posts, tracked links | 30 clicks per variant, then compare rates; any sale | INSUFFICIENT DATA after the run bounds the channel |
| Micro-B2B | service page with a before/after sample and an intake that reaches the founder | one in-scope inquiry | no in-scope inquiry in 90 days of a measured page |
| Research and data | free sample brief from an existing pipeline | requests for the full version | none after it is distributed |
| AI operations | the silent-failures guide with a tracked call to action | inquiries about monitoring | none |
| Productized AI services | deliver one internal document task end to end with customer-grade QA | quality passes without heavy manual work | it needs heavy manual work |
| Affiliate | one approved program with a payout route verified for Algeria | approval + one tagged link live | no program accepts |
| Distribution | the experiments above, measured per channel | measurable clicks | views without clicks |
| Children's media | private viewing of ep01 by a few parents | positive, specific feedback | concerns about content or fit |

## D. Backlog across arms (ranked by value, evidence, effort, risk, dependency)

| # | Task | Arms unlocked | Owner | State |
|---|---|---|---|---|
| 1 | Visit measurement (free analytics receiver) | digital, micro-B2B, affiliate, distribution | founder (account) | BLOCKED (B6) |
| 2 | Public intake that the factory records (today: Pages answers 405; contact form relays e-mail, activation UNKNOWN) | micro-B2B, research, AI operations, AI services | factory + founder | OPEN |
| 3 | Apply listing repairs (5 files, 32 descriptions) | digital | founder | PASS, waiting |
| 4 | Run EXP-B16-007-LI-01 | digital, distribution | founder | PENDING_APPROVAL |
| 5 | Micro-B2B offer page with sample | micro-B2B | factory | TODO |
| 6 | Sample research brief | research | factory | TODO |
| 7 | One verified affiliate program | affiliate | founder | BLOCKED |
| 8 | Native Arabic review of scripts | children's media | founder | BLOCKED |

## E. What changed in this session (OBSERVED)

- `arm_portfolio.py` (new): profiles for all eight arms, stage checked against evidence status, KPIs marked OBSERVED or UNKNOWN, cross-arm bottlenecks; written into `data/business_arms_state.json` by `business_arms.write_state()`.
- `business_arms.py`: the children's studio state is derived from its own verify records (was fixed text saying "one animatic").
- Dashboard: portfolio card with stage, model, measurable KPIs, next decision and the shared bottlenecks (working copy of `dashboard.html`, part of the uncommitted dashboard redesign).
- Tests: `tests/test_arm_portfolio_profiles.py` (10), existing arm tests still pass.

## F. Dashboard

The existing CEO dashboard (`dashboard.html` + `lib/ceo_command_center.js`) remains the one
dashboard. Company-wide revenue and the funnel are in "القمع والتجارب"; per-arm state, stage
and next decisions in "الأذرع والقدرات". Every figure carries its source; unknowns stay UNKNOWN.

## G. Measurement by revenue model

| Model | Arms | Measured (OBSERVED) | Not measured (UNKNOWN) and why |
|---|---|---|---|
| One-time digital sale | digital | listings, orders, gross (Gumroad), what each listing delivers | visits (B6), refunds/fees/net (no feed) |
| Fixed-scope service | micro-B2B, AI services, AI operations | inquiries where the local server receives them | public inquiries (no recording intake), delivery hours, margin |
| Commission | affiliate | classified clicks, ledger commissions | network conversions, payouts (no account) |
| Attention for other arms | distribution | Telegraph views, drafts prepared | outbound clicks, attributable sessions |
| Media | children's | verified renders, rights ledger | audience (no channel) |
| Briefs/data | research | data-card completeness | demand (no offer) |

Digital, service, commission and media economics are not combined into one figure; company
revenue is the sum of verified transactions only.

## H. Dependencies, risks, decisions

- Two shared gaps block most arms: visit measurement (4 arms) and recorded public intake (4 arms).
- Single-channel risk: every verified product sells only on Gumroad; Paddle is refused (403).
- Founder decisions open: listing repairs, experiment approval, analytics account, affiliate program, Arabic review and narration route, Pinterest board, disk space (opencode.db 127.5 GB).

## I. Next priorities

1. Visit measurement: turns the funnel diagnosis from "A or B or C" into a fact for four arms.
2. Recorded public intake: the only way the service arms can receive their first inquiry.
3. Listing repairs: protects the one arm already in a commercial test.
4. The LinkedIn experiment: the first two-arm test on a free channel.
5. Micro-B2B offer page: the cheapest test of a second, non-Gumroad revenue path.

## J. Truth

No arm is commercially operational; no business model is shown to work; revenue is $0.
Code existing for an arm is recorded as implementation evidence only.
