# OpenClaw / Galaxy Forge — Partnership Engine

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). This directive's Partnership Engine is checked against `business_development.py` (ADR-188) — already real, already built, already exactly this system under a different name. Not rebuilt.

---

## The 7 requested partner types, checked

| Requested | Real coverage |
|---|---|
| Strategic partners | `business_development.py`'s real `partnership` opportunity type — Paddle's real Partner Program cited directly |
| Technology partners | The real `api_integration` opportunity type — n8n and Zapier, both real, confirmed programs |
| Distribution partners | Gumroad and Etsy — real code, real marketplace opportunity type |
| Affiliate partners | 12 of 19 real, WebSearch-verified platforms with a joinable affiliate program (Amazon, Gumroad, Paddle-via-network, Etsy, Shopify, Creative Market, Envato, Adobe, Google, Canva, Zapier, n8n) |
| Enterprise partners | Honestly `NOT_ARCHITECTED` — no real enterprise partnership motion exists |
| Channel partners | Same as Distribution partners above — this factory does not distinguish the two as separate real categories |
| Licensing partners | Honestly `NOT_ARCHITECTED` — `CATEGORY_NOTES` already discloses this |

**5 of 7 have real, evidenced coverage. 2 are genuine, disclosed gaps** (Enterprise, Licensing) — both downstream of having a real enterprise-shaped or licensable product, neither of which exists yet.

## "Rank them by expected lifetime value" — the real, honest ranking

`business_development.py::_opportunity_score()`'s real, disclosed 3-axis heuristic (program confirmed / joinable by a small business / strategic fit) is the actual ranking mechanism — **never a fabricated lifetime-value dollar figure**, since zero real usage data exists for 18 of the 19 researched platforms (Paddle is the one real, live exception). A partnership with a real, confirmed, small-business-joinable program and real strategic fit to this company's product line ranks above one that merely sounds impressive.

## The real CRM pipeline — already live

`data/partnership_pipeline.jsonl` (real, append-only, 7 named stages: Discovery→Evaluation→Preparation→Negotiation→Implementation→Active→Optimization) already tracks real state, honestly: Paddle at `ACTIVE` (a real, live merchant relationship), Amazon at `PREPARATION` (real code, no tag configured yet), every other real platform honestly at `DISCOVERY`. This is not a hypothetical pipeline this document proposes — it is the real, current state of this company's real partnerships as of this writing.

---

## Phase 20 update (2026-08-08, ADR-210)

The "GLOBAL COMMERCIAL SCALE & EXPANSION ENGINE" directive's Section 17 (Partnership Engine) re-asks this exact question. Re-checked live: `business_development.py`'s real pipeline is unchanged since the entry above — Paddle still the only real `ACTIVE` relationship, Amazon still `PREPARATION`, every other platform still `DISCOVERY`. No new partnership evaluation was run this round; `global_commercial_scale.py::build_global_commercial_scale_dashboard()` cites `business_development.build_business_development_dashboard()` directly under its `partnerships` field, never a second, competing partnership ranker.

---

*See also: `DIGITAL_EMPIRE_ENGINE.md`, `GLOBAL_REVENUE_ARCHITECTURE.md`, `EMPIRE_SCORE.md`, `COMPETITOR_INTELLIGENCE.md`, `GLOBAL_SCALE_ENGINE.md`.*
