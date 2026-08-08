# Galaxy Forge — Lead Engine

**Date:** 2026-08-08 | ADR-218, Phase 28, Sections 6-7. `global_growth_engine.lead_registry()` + `lead_qualification()` — genuinely new this round.

---

## Section 6 — Lead Registry

**Real insight**: `customer_pipeline.py`'s real intake requests already ARE this factory's real lead registry — every request is a real lead before real conversion. `lead_registry()` reuses `list_pipeline_overview()` directly, never a second, competing lead database. **Never fabricates a lead** — a 0-lead count is honestly reported if that is what the real pipeline shows.

## Section 7 — Lead Qualification (6 named levels)

`lead_qualification(request_id)` — a real, deterministic classifier over the request's real pipeline stage: `NEW` → `UNQUALIFIED`; `QUALIFIED`/`PROPOSED`/`APPROVED` → `QUALIFIED`; `AWAITING_PAYMENT` through `FOLLOWED_UP` → `HIGH_VALUE`. **`ENTERPRISE`/`STRATEGIC` are never auto-assigned** — verified by a dedicated regression test — both require a real founder judgment call.

---

*See also: `CAC_ENGINE.md`, `GLOBAL_GROWTH_ENGINE.md`.*
