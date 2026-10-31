# Galaxy Forge: company portfolio (updated 2026-10-31)

Galaxy Forge is the company; the factory is its executive engine; the eight doctrine arms are
its commercial engines. This page is the human-readable view. The live data is computed by
`business_arms.py` (evidence status per arm) and `arm_portfolio.py` (stage, model, KPIs,
dependencies, current experiment, next decision), written to `data/business_arms_state.json` and
shown on the CEO dashboard, tab "الأذرع والقدرات", card "محفظة الشركة". When this page and the
dashboard disagree, the dashboard is current. Evidence classes: OBSERVED, DERIVED, INFERRED, UNKNOWN.

## A. Capability map (OBSERVED in the repository)

| Directive arm | Doctrine arm | Implemented today |
|---|---|---|
| A Digital products | `digital_products` | 116 products in the registry, 109 live on Gumroad, 4 built and QA-passed awaiting publication (B16-008..010, and B17-001, a ten-country EAA penalty workbook built from the research arm's register); batch pipeline with independent formula checks; per-product publication gate with expiring approvals; delivery audit; listing-repair script (dry run passes against the live listings) |
| B Productized services | `productized_ai_services` | accessibility quick-check (`services/accessibility_check/`): fixed WCAG 2.2 rules, files or named URLs, never claims compliance; our own 118 pages: 0 errors, 22 warnings; repair script for our site prepared |
| C Micro-B2B | `micro_b2b` | catalogue clean-up engine (CSV and XLSX, ambiguous dates and mixed currencies flagged); Merchant Center feed preflight (CSV, TSV, RSS/Atom XML; rules cited from Google's spec; hostile XML refused) |
| D Research | `research_data_services` | EAA penalty register (10 countries, each figure tied to its legal text; two vendor figures contradicted); USPTO trademark fee table, checked daily against the official schedule |
| E AI operations | `ai_operations` | n8n automation audit from the customer's read-only API exports (payloads dropped); priced against observed comparable offers |
| F Affiliate intelligence | `affiliate_intelligence` | click tracking with classification, commission ledger, comparison pages (held) |
| G Data products | `research_data_services` (shared) | the two datasets above, data cards PASS |
| H Content and distribution | `content_distribution` | Telegraph articles (live, read daily), social draft engine, Pinterest queue, IndexNow |
| I Children's media | `childrens_media_studio` | two verified animatics, subtitle checks, rights ledger; private parent-feedback protocol and privacy-safe recorder |
| J New ventures | not an arm | opportunity engine; the 2026-10-29 discovery cycle is `OPPORTUNITY_DISCOVERY_2026-10-29.md` |

Shared intake, all arms: the site's mailto links (38 pages) reach the founder, and
`python inquiry_intake.py record-email ...` puts an e-mailed inquiry in the review queue. The site
cannot receive a form POST (GitHub Pages answers 405). Offer pages for B, C, D and E exist as
unpublished drafts in `drafts/services/` with an e-mail call to action.

## B. Arm assessment (live, 2026-10-30)

| Arm | Evidence status | Stage | Current experiment |
|---|---|---|---|
| Digital products | PARTIAL | COMMERCIAL_TEST | EXP-B16-007-LI-01, PENDING_APPROVAL |
| Content and distribution | PARTIAL | VALIDATION | blocked: no click or visit measurement |
| Micro-B2B | PARTIAL | BUILD | blocked: offer page awaits founder approval (e-mail route ready) |
| Research and data | PARTIAL | BUILD | blocked: offer page awaits founder approval |
| AI operations | PARTIAL | BUILD | blocked: offer page awaits approval; forum rules unread |
| Productized services | PARTIAL | BUILD | PREPARED: fix our own site, then a free 3-page check |
| Children's media | PARTIAL | BUILD | PREPARED: private parent feedback on ep01 |
| Affiliate intelligence | BLOCKED | HOLD | none until a payout route is verified |

No arm is REVENUE_VERIFIED or OPERATING. Company revenue: $0 (Gumroad, OBSERVED). No inquiry has
been recorded in any arm.

## C. What each arm's next test needs from the founder

| Arm | Founder action | Then measured by |
|---|---|---|
| Digital products | publish B16-008..010 (approvals expire 2026-11-01 20:56 UTC); approve and publish B17-001; run the listing repairs; post EXP-B16-007-LI-01 | sales; LinkedIn link clicks |
| Micro-B2B, research, AI operations, productized services | approve publishing the draft pages | e-mail inquiries recorded in the queue |
| Productized services | approve the accessibility repair of our own site | before/after report |
| Children's media | show the ep01 animatic to 3-8 parents, record answers | `record_feedback.py --summary` |
| Content and distribution | create a free analytics account (command ready) | first recorded visit |
| Affiliate | one approved programme with a verified payout route | approval and a tagged link |

## D. Measurement by revenue model

| Model | Arms | Measured (OBSERVED) | Not measured (UNKNOWN) and why |
|---|---|---|---|
| One-time digital sale | digital | listings, orders, gross (Gumroad), what each listing delivers | visits (no analytics receiver), refunds/fees/net (no feed) |
| Fixed-scope service | micro-B2B, services, AI operations | inquiries recorded in the queue (e-mail or local form) | delivery hours, margin (no engagement yet) |
| Commission | affiliate | classified clicks, ledger commissions | network conversions, payouts (no account) |
| Attention for other arms | distribution | Telegraph views (platform counter, includes bots) | outbound clicks, attributable sessions |
| Media | children's | verified renders, rights ledger, parent feedback once recorded | audience (no channel) |
| Briefs/data | research | data-card validation, daily USPTO fee check | demand (no published offer) |

## E. Dependencies, risks, decisions

- Shared gaps: visit measurement (blocks reading any page-level result) and a form receiver
  (recording stays manual through e-mail).
- Single-channel risk: every verified product sells only on Gumroad; Paddle is refused (403).
- Disk: opencode.db is 128 GB and growing; 5 GB free (founder decision).
- Seven old CI worktrees outside the project hold about 800 MB (founder decision).

## F. Truth

No arm is commercially operational; no business model is shown to work; revenue is $0. Code
existing for an arm is recorded as implementation evidence only; a draft page is not an offer
until it is published, and an offer is not demand until someone asks.
