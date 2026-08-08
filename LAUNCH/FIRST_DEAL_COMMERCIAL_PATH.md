# Galaxy Forge — First Commercial Path Model

**Date:** 2026-08-08 | ADR-229, Phase 36, Section 13. Every real function cited below was live-tested this session (Phases 33-36).

---

| Step | Input | Output | Owner | Evidence | Failure State | Audit Event |
|---|---|---|---|---|---|---|
| Golden Hunter | Real market signal (HN, GitHub, etc.) | Real niche decision record | `market_hunter.py` | `data/decisions.jsonl` (2,074 real records) | Honest `REJECTED` on insufficient evidence | Real decision append |
| Partner Intelligence | Real registry entry | Verification status | `partner_intelligence_agent.py` + `commission_engine._derive_verification_status()` | `data/commission_opportunities.jsonl` | `THIRD_PARTY_ONLY`/`UNVERIFIED`, never fabricated `VERIFIED` | None yet (read-only classification) |
| Verified Opportunity | `CO-n8n-affiliate` (this round's real selection) | Real dossier | `commission_engine.select_first_launch_opportunity()` | `LAUNCH/FIRST_DEAL_OPPORTUNITY_DOSSIER.md` | `FIRST_LAUNCH_OPPORTUNITY=NONE` if no candidate qualifies | None (deterministic function, no side effect) |
| Commercial Deal Agent | Opportunity + customer profile | `deal_priority_score()` | `commercial_deal_agent.py` | Live-tested this round, 7/11 factors known | `EXPECTED_VALUE=UNKNOWN` without real economics | `data/commission_pipeline_events.jsonl` (once a real transition occurs) |
| Customer Profile | Real segment definition | ICP document | `LAUNCH/FIRST_DEAL_CUSTOMER_PROFILE.md` | This document, hand-authored, disclosed as a profile not a fabricated individual | N/A (static document) | N/A |
| Qualified Prospect | **BLOCKED** — 0 real prospects exist | N/A | `lead_outreach_agent.py` (real pipeline exists, no real input) | `LAUNCH/FIRST_DEAL_PROSPECT_SPECIFICATION.md` | Honestly empty — `lead_discovery` capability confirmed absent | N/A |
| Outreach Draft | Opportunity + (absent) prospect | `DRAFT_ONLY` message | `outreach_engine.draft_outreach_message()` | `data/outreach_log.jsonl`, `LAUNCH/FIRST_DEAL_OUTREACH_DRAFT.md` | Never auto-advances past `DRAFT` | Real `DRAFTED` event |
| CEO Approval | Draft + real approver identity | `APPROVED`/`REJECTED` | `outreach_engine.approve_outreach()`/`reject_outreach()` | Requires a real, non-empty `approved_by` | Refuses anonymous approval | Real `APPROVED`/`REJECTED` event |
| Outreach Adapter | Approved draft | Send attempt | `outreach_engine.send_outreach()` | `outreach_adapter_status()` = `NO_CREDENTIAL` | **BLOCKED — real, structural, unchanged** | Real `SEND_ATTEMPT_BLOCKED` event |
| Prospect Response | Real inbound reply | N/A | **Does not exist** — no real response-capture mechanism | `outreach_adapter_status()`'s own real capability inventory | Confirmed absent, honestly disclosed | N/A |
| Deal | Real response | Pipeline transition | `lead_outreach_agent.record_prospect_transition()` | Real, tested state machine | Rejects any unnamed state | Real event |
| Partner Tracking | Real referral click/signup | n8n's own real dashboard | **External to this factory** — no real API integration exists for n8n specifically | N/A | N/A | N/A |
| External Sale | A real n8n subscription | Real transaction | **External** | N/A until n8n reports it | N/A | N/A |
| Commission | Real, externally-confirmed commission | Ledger record | `commission_ledger.record_commission(environment="REAL", evidence=...)` | Hard `AntiFabricationError` guard, adversarially tested this session | Raises rather than fabricating | Real ledger append |
| Payout | Real PayPal transfer from n8n | Ledger `PAID` status | `commission_ledger.py` | Requires a real `external_transaction_id` | Cannot be `PAID` without one | Real ledger append |
| Finance Truth | Real payout | `real_commission_summary()` | `commission_ledger.real_commission_summary()` | Only counts `CONFIRMED`/`PAID` `REAL` records | $0 until proven otherwise | N/A |

## Where the real path is currently blocked

**Qualified Prospect → Outreach Draft → CEO Approval → Outreach Adapter**: the chain is real and tested up through Outreach Draft, then genuinely blocked at 2 points simultaneously — no real prospect exists (Lead Discovery gap) and no real sending credential/adapter exists (Outreach Adapter gap). Both are honestly disclosed, neither is bypassed.

---

*See also: `LAUNCH/GALAXY_FORGE_FIRST_DEAL_CHECKLIST.md`, `AUDIT/PHASE_36_COMMERCIAL_LAUNCH_CONTROL_REPORT.md`.*
