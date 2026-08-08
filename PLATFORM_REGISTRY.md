# Galaxy Forge — Platform Registry (Commercial Operations)

**Date:** 2026-08-08 | ADR-216, Phase 26, Sections 2-3. `global_commercial_operations_engine.platform_registry()` — reuses `business_development.py::PLATFORM_REGISTRY` (ADR-188) verbatim, never a second registry.

---

## The 21 named fields, checked

| Field | Real coverage |
|---|---|
| Platform ID, Platform Name | Real — all 21 platforms |
| Platform Type | Real via `OPPORTUNITY_TYPES` |
| Country, Currency | Mostly global/USD-only — see `MULTI_TENANCY`/currency findings |
| API Availability, API Status | Real for Paddle (live), disclosed for others |
| Commission Model, Platform Fees | Real for Paddle/Gumroad tiers (`economics.py`); `Unknown -- not yet researched` for most others |
| Payout Method, Payout Schedule | `Unknown -- not yet researched` for 19 of 21 |
| Refund Rules | Real: 0 real refunds ever occurred |
| Affiliate/Partner Capability | Real via `OPPORTUNITY_TYPES.affiliate`/`.partnership` |
| Automation Capability | Real via `evaluate_platform()`'s `automation_potential` field |
| Risk, Status | Real — `evaluate_platform()`'s own `risk`/`current_stage` |
| Last Verification, Source, Confidence | Real: 2026-08-07 WebSearch, per-entry cited |

## Section 3 — Platform Categories

15 named categories (Digital Marketplaces through Other) — this factory's 21 real platforms map onto ~6 of the 15 with real coverage (Digital Marketplaces, E-commerce, Affiliate Networks, Software Marketplaces, B2B Marketplaces, Direct Store via Paddle). **Not every platform is assumed suitable for every product** — enforced by `platform_fit()`'s real, per-product classifier (see `PLATFORM_FIT_ENGINE.md`).

---

*See also: `GLOBAL_COMMERCIAL_OPERATIONS_ENGINE.md`, `PLATFORM_FIT_ENGINE.md`.*
