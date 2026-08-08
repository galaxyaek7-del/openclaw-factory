# Galaxy Forge — Enterprise Problem Registry

**Date:** 2026-08-08 | ADR-214, Phase 24, Sections 2-4. `enterprise_transformation_engine.enterprise_problem_registry()` + `roi_model()`.

---

## Sections 2-3 — Discovery + Registry

Real citation over the 5 named integrations (Golden Hunter, Customer Intelligence, Market Intelligence, Revenue Intelligence, Innovation Engine) — never a second discovery engine. The 20-field schema (Opportunity ID through Status) is real and ready; **0 real entries exist** (0 real customers).

## Section 4 — Business Impact Model

The 11 named impact fields (Hours Saved, Employees Affected, Cost Reduction, Revenue Opportunity, Error Reduction, Risk Reduction, Response-Time, Decision-Time, CX Improvement, Operational Visibility, Automation Potential) all route through `roi_model()`'s real evidence-tier tagging — see below. **Never invents monetary savings**: any value supplied without a real, verified source defaults to `ESTIMATED`, never `VERIFIED`.

## Section 5 — ROI Engine

5 named evidence tiers (`ROI_EVIDENCE_TIERS`: VERIFIED / CUSTOMER_PROVIDED / ESTIMATED / PROJECTED / UNKNOWN). `roi_evidence_tier(value, source)` is a real, deterministic tagger — a missing value is always `UNKNOWN`, never silently `0`; a provided value defaults to `ESTIMATED` and is never auto-upgraded to `VERIFIED` without an explicit re-tag. Verified by 3 regression tests.

---

*See also: `ENTERPRISE_TRANSFORMATION_ENGINE.md`, `ENTERPRISE_QUALIFICATION_ENGINE.md`.*
