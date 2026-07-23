# ADR-108 — Global Growth Engine (Product Multiplication + Channel Expansion)

**Date:** 2026-07-24
**Status:** Adopted.

---

## The directive

"Every successful product must automatically create more opportunities... the company must compound." For every validated winner, automatically discover 10 named variant types (premium, enterprise, subscription, bundle, regional, industry-specific, language-localized, API, SaaS, AI Agent versions). After validation, evaluate 10 named regions and 10 named channels. Every successful asset must generate new assets/customers/datasets/knowledge/opportunities/recurring revenue.

## Scope alignment

Two things were settled before writing any code:

1. **The "10 regions" Market Expansion section repeats an ask already deferred twice today** — ADR-103 (Strategic Investment Philosophy) and its reaffirmation in ADR-106 (Global Market Learning Engine), both for the same unchanged reason: zero real local data connectors, zero real sales. Applied the same standing decision a third time without re-asking — nothing has changed to unblock it.
2. **"Validated winner" needed a real definition** — this factory has zero real closed sales today. Confirmed via AskUserQuestion: evaluate for every real ACCEPTED decision (many exist), with every candidate explicitly disclosing whether it is market-validated (real `market_memory.py` evidence) or only intelligence-validated (the ladder score alone) — never presented as equally proven.

## What was found before building

Checked all 10 named variant types against real, already-built infrastructure rather than inventing a parallel system:

- **Premium version** — real. `value_engine.py`'s own `upgrade_potential` dimension (ADR-102) already computes this via `revenue_pipeline.plan.compare_ladder_variants()`. Reused verbatim. A real bug was found and fixed before it shipped: `upgrade_potential`'s "no data yet" shape is `value_engine._unknown()`'s `{"answer": "Unknown", "reason": ...}`, not the `{"value": None, ...}` shape a first draft assumed — caught by a dedicated regression test, not silently working around it.
- **Bundle opportunities** — real. `value_engine.py`'s own `bundle_potential` dimension, reused verbatim.
- **API version / SaaS version** — real. `product_families.registry` already tracks `api_products`/`micro_saas` as 2 of the 11 canonical Universal Production Engine families (`mission_control_api.py`'s own `_UPE_FAMILY_REGISTRY_NAMES`), honestly `REAL` or `NOT YET BUILT` per real adapter registration — reused directly, no new taxonomy invented.
- **Subscription version** — a real, disclosed middle case: `channels/paddle_publisher.py::create_price()` already accepts a real `billing_cycle` parameter (Paddle's own recurring-billing support), so the structural capability is genuinely real — but zero of this factory's 5 real shipped products has ever used it. Reported as `{"structurally_available": true, "real_precedent": false}`, never presented as a proven model.
- **Enterprise version / Regional versions / Industry-specific versions / Language-localized versions / AI Agent version** — no real source anywhere in this factory today. Each reports `{"available": false, "reason": ...}` with the specific, real reason (no distinct enterprise pricing tier beyond the "elite" ladder band; ADR-103's deferral; no industry taxonomy exists — `product_families` classifies file type, not customer industry; no distinct "AI Agent" product family, only the adjacent `ai_saas`/`micro_saas`).

**Channel Expansion** follows `integration_registry.py`'s already-established pattern exactly: `channels/registry.py`'s real live arms (Paddle, Gumroad, Payhip, Etsy) are referenced, never re-derived; the other 7 named channels (GPT Store, Enterprise Sales, Affiliate Network, Subscription Platform, B2B Licensing, White Label, Direct Website) are honest catalog entries — `configured` from a real environment-variable check where a credential concept exists, `None` (not `false`) where this factory's current single-storefront architecture has no separate platform to credential at all. Never a live "test connection" call, matching every other integration catalog in this factory.

**Compounding**: no new system was built for this — the mission's own named compounding effects (new assets/customers/datasets/knowledge/opportunities/recurring revenue) already have real mechanisms shipped earlier today (Knowledge Graph's `CommercialEvent` nodes, Market Memory's evidence accumulation, `scheduler.py`'s `accelerate` bucket, Decision Re-open). Building a second, competing "compounding engine" on top of those would have been exactly the duplication this factory's discipline refuses.

## What was built

`growth_engine.py` (new): `evaluate_product_multiplication(niche)` (returns `None` for a niche with no real ACCEPTED decision, matching `value_engine.compute_value_profile()`'s own scope), `evaluate_channel_expansion()` (factory-wide, not niche-specific), `build_growth_report(niche)` (combines both). Two new Mission Control actions: `get-growth-report`, `get-channel-expansion-status`.

## Verification

12 new tests (`tests/test_growth_engine.py`) plus 5 new Mission Control action tests. Full regression: highest-risk suites first (growth_engine, mission_control_api, value_engine, decision_engine), then the full repository (Python + Node), then the API contract test to confirm the 2 new server.js actions register correctly.

## What's deliberately not built

- Regional/localized/industry-specific/enterprise/AI-agent variant generation — no real data source exists for any of them; building one now would mean fabrication.
- No live "test connection" to any of the 7 catalog-only channels — matches `integration_registry.py`'s own explicit anti-fabrication discipline.
- No automatic execution of any recommended variant or channel — this ADR is evaluation and visibility only, same human-confirmation boundary every other production/publishing action in this factory already has (ADR-107).
