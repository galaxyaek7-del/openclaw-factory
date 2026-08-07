# Galaxy Forge — Platform Intelligence

**Date:** 2026-08-08 | Phase 16, Section 8. Extends `PLATFORM_RELIABILITY_REPORT.md` (Phase 13) with the specific commercial-intelligence fields this section names.

---

| Platform | Gross Rev | Net Rev | Fees | Conversion | Refund Rate | Customer Quality | Operational Reliability | Automation Reliability | Support Burden | Strategic Value | Recommendation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Paddle** | $0 (real, live-verified) | $0 | $0 (real, `fees: []`) | N/A — 0 real visitors | 0% (real — 0 refunds ever) | N/A — 0 customers | **High** — real 6/6 exact product match, 0 discrepancies, live-proven this round | High — real retry/idempotency (ADR-204) | N/A | **High** — the only credentialed platform | **INVESTIGATE** (checkout blocked — not a platform defect, an account-onboarding gap) |
| Gumroad | $0 | $0 | N/A | N/A | N/A | N/A | Real, correctly reports `UNAVAILABLE` (no credential) | N/A | N/A | Medium (real code exists, real archived-priority status per `channels/gumroad_arm.py`'s own docstring) | **MAINTAIN** (dormant, ready, no action needed) |
| Etsy | $0 | $0 | N/A | N/A | N/A | N/A | Real `UNAVAILABLE` | N/A | N/A | Low-medium (OAuth2 friction, real, documented) | **MAINTAIN** |
| Payhip | $0 | $0 | N/A | N/A | N/A | N/A | Real `UNAVAILABLE`; real, twice-verified "no product API" limitation (ADR-025) | N/A | N/A | Low (structural API limitation) | **MAINTAIN** (manual-only, by founder decision) |

## Platform concentration

**100%** of real commercial capability depends on Paddle — confirmed again this round (`global_opportunity_exchange.py::concentration_risk_report()`'s real platform axis honestly reports `NOT ENOUGH EVIDENCE` since 0 real sales exist to compute a percentage from, but the qualitative fact — 1 of 4 arms credentialed — is unambiguous and unchanged since Phase 13).

## Recommendation for Paddle specifically

**INVESTIGATE**, not EXPAND/MAINTAIN/REDUCE/PAUSE — the platform itself is real, reliable, and correctly integrated; what needs investigation is external (the account's own onboarding completion status), not this factory's code.

---

*See also: `PLATFORM_RELIABILITY_REPORT.md` (Phase 13), `MARKET_EXPANSION_ENGINE.md`.*
