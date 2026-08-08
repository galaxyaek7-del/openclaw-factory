# Galaxy Forge — First Deal Prospect Specification

**Date:** 2026-08-08 | ADR-229, Phase 36, Section 10.

---

## Real, honest state: 0 real prospect candidates exist

Confirmed directly: `outreach_engine.outreach_adapter_status()`'s own real capability inventory (Phase 35) reports `lead_discovery: exists=False` — **no real lead-sourcing integration exists anywhere in this factory.** Per this phase's own explicit instructions ("Do NOT contact anyone yet. Do NOT scrape private information. Do NOT create fake leads"), this document does not invent a prospect to fill the schema below.

## The real, ready schema (per opportunity, once a real source exists)

| Field | Status |
|---|---|
| PROSPECT_ID | Not yet assigned — no real candidate exists |
| COMPANY | UNKNOWN |
| SOURCE | UNKNOWN — no real lead-discovery mechanism exists to cite |
| ROLE | UNKNOWN |
| BUSINESS_REASON | UNKNOWN |
| PROBLEM_SIGNAL | UNKNOWN |
| QUALIFICATION | Not applicable — `lead_outreach_agent.PROSPECT_PIPELINE_STATES`'s real state machine starts at `TARGET_CUSTOMER`, which requires a real prospect to transition into it |
| SOURCE_TIMESTAMP | N/A |
| EVIDENCE | N/A |
| CONFIDENCE | N/A |

## What real, safe discovery would require

A real lead-sourcing signal this factory does not currently have wired: e.g. a real, permissioned business directory search, a real inbound-interest signal (someone visiting `customer_site/`), or a real referral from an existing relationship. None of these exist as real, callable integrations today — this is a disclosed, standing gap (Phase 33-35), not something this document works around.

## Consequence for this phase's dry run (Section 23)

The end-to-end dry run (`AUDIT/PHASE_36_COMMERCIAL_LAUNCH_CONTROL_REPORT.md`'s `DRY_RUN_STATUS` section) uses one explicitly `SIMULATION_ONLY=true` synthetic prospect for this exact reason — never presented as, or confused with, a real prospect candidate.

---

*See also: `LAUNCH/FIRST_DEAL_CUSTOMER_PROFILE.md`, `COMMERCIAL/OUTREACH_POLICY.md`.*
