# ADR-111 — Real World Commercial Expansion (Priorities 3-5: Premium Products, Commercial Intelligence, Commercial Execution)

**Date:** 2026-07-24
**Status:** Adopted.

---

## The directive

"Transform OpenClaw from an intelligent operating system into a real revenue-generating digital company." Priority order: (1) Global Market Expansion — country profiles for USA/Europe/China/Japan/Korea/Middle East/Latin America; (2) China Commercial Division — WeChat, Alipay, Xiaohongshu, Douyin, Chinese AI ecosystem, Chinese payment preferences, Chinese localization, Chinese market intelligence; (3) Premium Digital Products Division ($100–$5000 products); (4) Commercial Intelligence Engine (demand, willingness to pay, competition, price ranges, buying behavior, regional differences, product opportunities, customer pain); (5) Commercial Execution (every opportunity automatically becomes Research → Validation → Business Case → Product Candidate → Production Queue → Publishing Queue → Marketing Queue → Revenue Tracking → Learning Loop). Explicit engineering rule: "No fake data. No placeholders... Verified evidence only."

## Scope decision: Priorities 1-2 not built, confirmed with the founder

This directive escalated Global Market Expansion and the China Commercial Division to the literal top two priorities — a real change from earlier the same day, where the identical ask appeared as one section among several and was deferred (ADR-103, reaffirmed ADR-106/108/110). That escalation warranted a fresh check rather than silently reapplying the old decision, because something concrete had changed: a real, mechanical conflict inside this directive's own text.

Priority 2 names WeChat, Alipay, Xiaohongshu, and Douyin workflows — this factory holds zero real credentials for any of them (no merchant account, no API access, confirmed against `.env` and every integration catalog in this repo). Priority 1 names 7 regions, including non-China ones — this factory has zero real country-level customer data from any real channel, including Paddle, its one real live payment processor (confirmed repeatedly, most recently in ADR-106). Building either priority would necessarily mean placeholder code or fabricated demonstration data — exactly what this same directive's own engineering rule forbids two sections later. Confirmed via AskUserQuestion: build Priorities 3-5 now (no missing-credential blocker), revisit Priorities 1-2 the moment real credentials or a first real sale exist — the same real trigger condition CLAUDE.md's own "الفلسفة الاستراتيجية" section already names.

## What was found before building

Priority 4's 8 named signals were checked against real, already-shipped intelligence before writing anything: `opportunity_pipeline.annotate_decision()` already computes real `market_size` (demand), `competition` (cached `competitor_discovery.py` snapshot), `pain_level` (customer pain), and `estimated_selling_price`. Only 2 of 8 signals were genuinely missing: willingness to pay (`market_evidence.get_willingness_to_pay_signal()`, real, already built, just never assembled into one report) and buying behavior (`market_memory.niche_commercial_profile()`, built earlier the same day). Priority 5's 9 named stages were checked against `execution_status.py`'s existing 10-stage lifecycle tracking (ADR-105/107) and found to already cover Research (`research_department.py`), Validation (`decision_engine`), Business Case (`business_dossier.py`), Product Candidate (Product Laboratory), Production/Publishing Queue (`scheduler.py`'s buckets, `distributor.py`), Revenue Tracking (`revenue_pipeline`), and Learning Loop (`market_memory.py`, `decision_engine/learning.py`) — all real, all already wired, all already visible per-opportunity via `execution_status.build_execution_status()`. Marketing Queue remains real but thin (`lib/publisher_seo.js`, SEO metadata only, already disclosed in ADR-108). Priority 5 was not rebuilt — doing so would have been exactly the duplication this whole session has refused throughout.

## What was built

**`commercial_intelligence.py` (new)** — `build_commercial_intelligence_report(niche)`, the real, unified view across all 8 named Priority 4 signals: 6 reused verbatim from `annotate_decision()`/`market_evidence.py`/`market_memory.py`/`growth_engine.py`, 1 new small aggregation (`price_ranges`, from `profit_oracle.py`'s real, documented ladder price bands), and `regional_differences` always honestly `{value: None, reason: ...}` — the same real gap Priorities 1-2 ran into, disclosed consistently rather than silently dropped from the report. Returns `None` (never fabricated) for a niche with no real decision at all — deliberately a wider scope than `value_engine`'s ACCEPTED-only view, since demand/competition/pain intelligence is real and useful pre-decision too.

**`growth_engine.py::premium_product_catalog_status()`** — the real status of the 7 founder-named Priority 3 categories against this factory's actual `product_families` adapters (5 map to a real family — automation_systems, micro_saas, professional_templates, knowledge_bases; 2, Vertical AI Assistants and Decision Platforms, have no distinct real family and say so honestly rather than being folded into an adjacent one). **A real, disclosed finding surfaced, not silently acted on**: `profit_oracle.py`'s real, documented elite price band (ADR-027/`ELITE_ASSET_DOCTRINE.md`) caps at $497 — far below this mission's own stated $5000 ceiling. Raising `MAX_BUTTER_PRICE_ELITE` is a real pricing-policy decision tied to a real, named ADR, not a bug fix; it is reported here as a clear finding for the founder to act on, not changed unilaterally.

Both wired into Mission Control: `get-commercial-intelligence-report` (per niche), `get-premium-product-catalog-status` (factory-wide).

## Verification

18 new tests (`tests/test_commercial_intelligence.py` — 9, `tests/test_growth_engine.py` — 4 new, `tests/test_mission_control_api.py` — 4 new, plus 1 explicitly confirming the pricing constant was read, not changed). Full regression: highest-risk suites first, then the full repository (Python + Node), then the API contract test.

## What's deliberately not built

- Priorities 1-2 in full — see the scope decision above; the real trigger to revisit is unchanged from CLAUDE.md's own standing philosophy (first real dollar, or a real local data connector, whichever comes first).
- `MAX_BUTTER_PRICE_ELITE` was not raised — a real pricing-policy decision surfaced for the founder, not made here.
- Priority 5 was not rebuilt — already real and already shipped (ADR-105/107/109/110); this ADR only confirms and documents the mapping.
