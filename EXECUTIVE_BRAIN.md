# OpenClaw / Galaxy Forge — Executive Brain

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). This document names something that already exists under this exact name: `executive_brain.py` (ADR-144, 2026-07-30) is the real, working Executive Brain. Phase 2 does not create a new one — it documents the real one and closes the small, genuine gaps between what it already does and what this directive asks for.

---

## What the Executive Brain is

**It does not execute code. It arbitrates.** `executive_brain.py::build_executive_directive()` calls four already-real systems exactly once each — `strategic_intelligence_core.build_executive_brief()`, `global_opportunity_exchange.py`, `capital_allocation_engine.py`, `evolution_queue.py` — plus `channels/ledger.py::revenue_trend()`, and produces **one** arbitrated recommendation per cycle: the single highest-priority real action across the entire company, never a list of competing suggestions.

**It tags, it doesn't invent.** Every real candidate action surfaced by those four systems is tagged with the founder's own named Priority tier (1 System Stability → 5 Self Evolution, extended to Tier 2 Opportunity Discovery and Tier 3 Premium Product Creation as real new candidate sources were added — `goos.py::rank_build_candidates()`, ADR-178; `product_marketing_engine.py`, ADR-180). A genuine same-tier tie is honestly reported as `SPLIT`, never resolved arbitrarily — the same discipline `galaxy_council.py` (`EXECUTIVE_COUNCIL.md`) uses for genuine multi-member disagreement.

**It never executes an irreversible action itself.** `requires_founder_approval` is always `True` in every real directive record. It never calls `evolution_queue.approve_proposal()`, never reallocates capital, never publishes, never retires a business — the four permanently human-gated actions named in `INTEGRITY_RULES.md` §3 are untouched by this module, by design, verified by direct code inspection, not assumed.

## How it answers the directive's 6 primary questions

| Question | Real answer, cited |
|---|---|
| What should the company do next? | The single arbitrated `current_mission` field — real, dated, in `data/executive_directives.jsonl` |
| Why? | The candidate's own real evidence citation, threaded through unchanged from its source system |
| What should be ignored? | Every candidate below the arbitrated top pick — visible in the full candidate list, not hidden |
| What generates the highest long-term value? | `capital_allocation_engine.py`'s real `top_roi_initiatives`, one of the Brain's 4 real inputs |
| What creates unnecessary complexity? | `enterprise_executive_brain.py::_detect_duplicated_work()` — real, mechanical, department-import-overlap detection |
| What increases enterprise value? | The same 4-input arbitration, framed against `COMPANY_DNA.md`'s own mission (proving evidence before building) |

## The real, disclosed limits

- **Cost:** a fresh call chains 3 full-portfolio scans, measured at ~59 seconds live. `CEO Home` (`ceo_home.py`, ADR-184) and the `EOS Decision Feed` (`eos_decision_feed.py`, ADR-186) deliberately read the Brain's own daily ledger entry instead of re-triggering this live — a 60-second-glance page that itself takes 59 seconds defeats its own purpose.
- **Cadence:** the real, deliberate one — `factory_loop.js`'s daily tick calls `_generate_daily_executive_directive()` once per calendar day. The live Mission Control view (`_executive_brain_directive()`, `record_ledger=False`) never grows the permanent ledger on a mere page refresh — a real bug this exact distinction was built to fix (found and corrected the same round the Brain shipped).
- **What it is not:** a second, competing judgment engine to any of its 4 real inputs. It has never once, in this company's real history, produced a recommendation those systems didn't already surface.

---

*See also: `EXECUTIVE_COUNCIL.md` (the 10 named virtual executives the Brain's own strategic inputs already draw on), `DECISION_PROTOCOL.md`, `PRIORITIZATION_ENGINE.md`, `EXECUTIVE_MEMORY.md`, `SELF_REVIEW_PROTOCOL.md`.*
