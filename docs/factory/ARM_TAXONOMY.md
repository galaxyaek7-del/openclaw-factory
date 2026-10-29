# Arm taxonomy: reconciliation (2026-10-29)

Mission GF-FACTORY-WIDE-RECONSTRUCTION-AND-BUILD-v1 names ten business activities and two
control capabilities. The repository already uses **four** different "arm" schemes. None is
renumbered, merged or deleted here; this page states which one is authoritative for which
question and how they map. Re-derive the live statuses with `python business_arms.py --write`
(also run by the daily registry rebuild) and read them on the CEO dashboard, section
"الأذرع والقدرات" (data: `data/business_arms_state.json`).

## The four existing schemes (OBSERVED)

| # | Scheme | Defined in | What an "arm" means there | Authoritative for |
|---|---|---|---|---|
| T1 | Eight business arms | `OpenClaw_Brain/00_Governance/PERMANENT_OPERATING_DOCTRINE.md` §5, `business_arms.py` (2026-10-19) | a line of business with READY / PARTIAL / PLANNED / BLOCKED / REVENUE_VERIFIED status from evidence | business-line status (doctrine for Cycle 103 on) |
| T2 | Capability arms P0-P3 | `MASTER_ARCHITECTURE_STATUS_2026_08_27.md` §3-8, `ARM7_*`/`ARM8_*` reports | an internal capability (Protection, Economics, Pain Mining, Attribution, Reputation, Distribution...) ordered by dependency | build order of platform capabilities |
| T3 | Numbered directive arms | `ARM_10_FINAL_REPORT.md` (Customer Acquisition & Distribution Intelligence, ADR-190), `ARM_11_FINAL_REPORT.md` (Revenue Activation, ADR-191) | one founder directive's work package | history of those directives only |
| T4 | Departments / divisions | `gfos.py::department_registry()` (12 departments, ADR-147), Mission Control V3 (17 divisions, ADR-151), `channels/registry` (publishing "arms": gumroad, payhip, etsy, paddle, x, kdp) | an organisational or channel unit | Mission Control panels; distribution channels |

The word "arm" therefore means four different things. T3 numbers (10, 11) collide with T2's
numbering and must not be read as business lines. In new work, "business arm" means T1 only;
a publishing channel is a "channel" (T4), not an arm.

## Ten portfolio activities -> T1 arms (code: `business_arms.PORTFOLIO_ACTIVITIES`)

| Activity | T1 arm | Note |
|---|---|---|
| Digital Products | `digital_products` | status now derived from `data/product_registry.json` (live Gumroad catalog) |
| Productized AI Services | `productized_ai_services` | PLANNED: no implementation evidence |
| Micro-B2B Products and Solutions | `micro_b2b` | one delivery engine (`services/spreadsheet_normalization/`) |
| RaaS / recurring operational services | none (nearest `micro_b2b`) | no recurring, outcome-priced service exists; reported PLANNED from its own evidence |
| Research-as-a-Service | `research_data_services` | shares the arm with Data Products |
| AI Operations | `ai_operations` | PLANNED: internal orchestration only, no customer offer |
| Affiliate Intelligence | `affiliate_intelligence` | BLOCKED: no affiliate account/tag |
| Data Products and Analytics | `research_data_services` | no dataset packaged for sale |
| Content and Media (incl. children's studio) | `childrens_media_studio` (+ `content_distribution`) | animatic only; voices/font are founder decisions |
| Distribution, Marketing, Partnerships | `content_distribution` | Pinterest/TikTok via Metricool; X blocked by spend; LinkedIn/Instagram not connected |

Every T1 arm is reachable from at least one activity (pinned by `tests/test_arm_portfolio.py`).

## Control capabilities (code: `business_arms.CONTROL_CAPABILITIES`)

Not business arms; they carry no revenue status.

| Capability | Authoritative modules | Rule |
|---|---|---|
| Predictive Intelligence | `profit_oracle.py`, `decision_engine/`, `goos.py` (support: `growth_stages.py`, `capital_allocation_engine.py`, `multi_source_intelligence/`) | recommends only; scores are ESTIMATED; acceptance still goes through `decision_engine` and the founder gates |
| Treasury Control | `revenue_truth.py`, `channels/ledger.py`, `commercial_reconciliation.py` (support: `revenue_os.py`, `asymmetric_wallet.py`, `scripts/poll_sales.py`) | visibility and reconciliation only; nothing initiates a payment, payout or transfer |

## Revenue attribution per arm

`REVENUE_VERIFIED` stays unreachable for every arm except Digital Products: a sale on a
Gumroad listing is that arm's own transaction evidence (registry `sales_count`), and the arm is
promoted only when the reconciled finance record (`revenue_truth`, status PASS) also shows
revenue. Other arms still have no per-arm attribution (backlog B22).
