# ADR-106 — Global Market Learning Engine (Market Memory + Commercial Evolution)

**Date:** 2026-07-23
**Status:** Adopted.

---

## The directive

"OpenClaw must become smarter after every sale, every failure, every visitor, every refund, and every opportunity." Build a permanent Market Memory layer capturing 17 named commercial dimensions per real event; wire every verified event into 7 named systems (Opportunity Queue, Profit Oracle, Revenue Engine, Executive Board, Mission Control, Knowledge Base, Strategic Investment Layer); track 10 minimum regions plus a China-specific intelligence domain; produce a monthly Commercial Evolution report; generate autonomous recommendations. Explicit constraint stated by the founder: "No synthetic data. No assumptions. Only verified commercial evidence."

## Scope alignment (confirmed with the founder before building)

Three explicit choices were confirmed via AskUserQuestion before any code was written, because this mission ran directly into ground the 2026-07-23 system integration audit had just covered:

1. **Sequencing**: `poll_sales.py` still couldn't link a real sale to a niche (confirmed in that audit) — nothing in this mission could produce a single real event without that fixed first. Confirmed: fix it first.
2. **Market Memory scope**: real capture schema + real read-only wiring into the 7 named systems, with evidence-gated recommendations that output nothing until real thresholds are met. Confirmed.
3. **10 regions + China Specialization**: this repeats ADR-103's (2026-07-22) already-deferred Global Market Expansion ask verbatim, for the identical reason (zero real local data connectors, zero real sales, conflicts with CLAUDE.md's own golden rule). Confirmed: reaffirm the deferral, build nothing regional. **Not built in this ADR — see ADR-103 for the standing reasoning, unchanged.**

## What was found before building anything

- `channels/ledger.py::record_sale()`'s own docstring already stated the real reason `niche` was never auto-derived: this factory has never seen a real completed sale, so the real response shape needed to map one to a niche safely was unverified. This explained, rather than excused, the gap.
- A real, tested, already-built sale→niche matcher already existed: `decision_engine/feedback.py::sync_outcomes()` (ADR-050) — product_id → publish_attempt → niche-substring-in-title, honest "unmatched" when no real match exists, never guessed. It already runs automatically on every real production cycle (`orchestrator/types.py`'s `EXECUTION_ORDER` includes a `"learning"` stage). It just never told `market_evidence.py`, so the Executive Quality Gate never received what it already knew — two entirely separate, unconnected real pipes.
- Paddle's real API (`channels/paddle_publisher.py`) was checked directly for what commercial dimensions are actually available: real price/time/country-via-billing-address/refund-via-adjustments-API are genuinely obtainable; device/conversion/customer-feedback/traffic-source have no real source anywhere in this factory today (no web analytics, no checkout-time UTM tagging, no feedback channel).
- `economics.py`'s platform fee table has **no `paddle` entry** — a real, previously-undisclosed gap: this factory's highest-value live channel has no real profit formula configured. Found while wiring Market Memory's `profit` dimension; documented, not silently worked around with a guessed fee percentage.

## What was built

**Prerequisite fix — `decision_engine/feedback.py::sync_outcomes()`:** a matched sale now also calls `market_evidence.record_evidence(niche, "closed_sale", ...)`, reusing the exact same already-proven matcher — no new matching logic invented. `orchestrator/engines/learning.py` threads a new `evidence_path` context key through for test isolation. Best-effort: a market_evidence write failure can never lose the real Outcome record itself.

**`market_memory.py` (new)** — the real Market Memory layer, checked field-by-field against what this factory can actually observe:
- Real: `product`, `platform`, `selling_price`, `time`, `season` (pure computation from time), `purchase_frequency` (real count of a stable customer identifier — Gumroad's real `email` field, Paddle's real `customer_id` field — reappearing in the sales ledger), `product_family` (when the originating decision recorded one).
- Real only when a fee model is configured: `profit` (reuses `economics.net_profit()` directly — never a second formula; honestly `None` + a stated reason for Paddle today).
- No real source anywhere in this factory, always `{value: None, reason: ...}`, never guessed: `bundle`, `customer_country`, `customer_language`, `traffic_source`, `acquisition_channel`, `device`, `conversion`, `refund`, `customer_feedback`.
- `niche_commercial_profile(niche)` — real aggregate (sample size, total/average revenue, platforms, seasons), honestly empty until real sales exist.
- `monthly_evolution_report()` — the founder-named monthly report, gated on `MIN_SAMPLES = 3` (matching `decision_engine/learning.py`'s existing convention). Sections with no real data source in this factory (bundles, LTV customers, country/channel ROI) stay honestly `None`, never fabricated to look populated.
- `recommend_actions()` — evidence-gated autonomous recommendations. Only two real, narrow recommendation types exist today (`increase_investment` when a niche has ≥3 real sales with positive real profit; `review_pricing_model` when real sales exist but no real fee model can compute a profit verdict) — an empty list is the correct, honest output while evidence is scarce, not a bug.

**Wiring into the 7 named systems** — one new real hook each, reusing existing consumers rather than inventing 7 separate integrations:
- **Knowledge Base**: `knowledge_graph/build.py` gained a 6th real source — `CommercialEvent` nodes from `market_evidence.jsonl`'s `closed_sale` events, linked to their `Niche` via a `sold_as` edge. Directly closes the 2026-07-23 audit's "knowledge_graph is write-only, doesn't compound" finding for this one real data path.
- **Strategic Investment Layer / Profit Oracle / Executive Board / Revenue Engine / Mission Control**: `value_engine.py::compute_value_profile()` gained a real `market_memory` field, and `_financials()`'s `estimated_lifetime_value` now uses real closed-sale revenue the moment it exists for a niche (labeled "revenue to date," never a forecast) instead of always `Unknown` — closing the 2026-07-23 audit's roadmap item #2 (Value Engine never read real reconciled sales data) using the exact same new data source. Because Executive Board, Revenue Pipeline, and Mission Control already consume `compute_value_profile()` (ADR-102), this single hook fans out to all four without touching those modules.
- **Opportunity Queue**: `decision_engine/ranking.py` gained `rank_queue_with_commercial_context()` — the existing queue, informational-only market memory attached per item, never re-ranked by it.
- **Mission Control**: 3 new real, non-stub actions (`get-niche-commercial-profile`, `get-monthly-market-evolution-report`, `get-commercial-recommendations`).

## Verification

50 new tests across 5 files (`tests/test_market_memory.py` — new, 19 tests; `tests/test_decision_engine.py` — 4 new: the evidence-wiring fix + the ranking wiring; `tests/test_knowledge_graph.py` — 3 new + 9 existing tests updated for `evidence_path` isolation; `tests/test_value_engine.py` — 2 new; `tests/test_mission_control_api.py` — 5 new). One real test-assumption bug found and fixed along the way (a purchase-frequency test called `build_commercial_event()` before appending the sale itself to the ledger, not matching the real production call order) — corrected the test, not the source.

Full regression: highest-risk suites first (`test_decision_engine.py`, `test_value_engine.py`, `test_knowledge_graph.py`, `test_market_memory.py`, `test_mission_control_api.py`, `test_market_evidence.py`, `test_executive_board.py`, `test_revenue_pipeline.py`, `test_opportunity_pipeline.py`, `test_orchestrator.py`, `test_factory_orchestrator.py`, `test_enterprise_readiness.py` — 326 tests), then the full repository (Python 1223/1223, Node 272/274 — the 2 non-failures are the pre-existing `tests/fixtures/always_crash.js`/`crash_n_times.js` crash-simulation fixtures, unrelated), then a data-drift check.

**A real test-isolation leak was found and fixed during that drift check**, the same recurring bug class this session has hit before: one pre-existing test (`test_real_sale_matched_via_product_id_and_niche_substring`, `tests/test_decision_engine.py`) exercises a real matched sale through `sync_outcomes()` without overriding the new `evidence_path` parameter — every run wrote a real line into the live `data/market_evidence.jsonl`. Caught via `git status --short` before committing (not by the test suite itself, which has no assertion against the real file). Fixed by threading `evidence_path=self.evidence_path` through all 4 pre-existing calls in that test class; the 3 leaked lines were removed from the real file before commit.

## What's deliberately not built

- **10 regions + China Specialization**: reaffirms ADR-103's deferral, unchanged reasoning, nothing new to unblock it since yesterday.
- **Refund tracking**: Paddle's real adjustments API exists but `scripts/poll_sales.py` only ever calls `get_sales()` — adding a second live API integration this session was judged out of scope without a real account to verify the response shape against (same caution `channels/ledger.py`'s own docstring already applied to the niche-matching problem this ADR fixed).
- **Traffic source / acquisition channel**: real going forward (Paddle's `custom_data` checkout field already exists and is used for one other purpose) but requires a new checkout-link tagging convention this session did not introduce — flagged, not built.
- **Country/language/device/conversion**: no real data source anywhere in this factory; building any of these would mean either a new live integration (a real address/geolocation lookup) or fabrication. Left honestly `None`.
