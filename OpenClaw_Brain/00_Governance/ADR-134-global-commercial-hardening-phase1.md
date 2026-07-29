# ADR-134 — Global Commercial Hardening, Phase 1: Marketplace Publish Protection Layer + Executive Safety Principles

**Date:** 2026-07-29
**Status:** Adopted.

---

## The directive

"GALAXY FORGE — EXECUTIVE DIRECTIVE — Phase: Global Commercial Hardening": Galaxy Forge is becoming an autonomous global digital enterprise; every improvement must increase Safety, Intelligence, or Revenue, or it is not built. Five priorities: (1) a Global Marketplace Protection Layer (cooldowns, throttling, daily/hourly limits, pre-publish risk scoring, automatic delay on suspicious behaviour, per-platform adaptive profiles, a global emergency stop, a complete audit trail — across Amazon KDP, Etsy, Gumroad, Payhip, Shopify, AliExpress, and future channels); (2) a Global Partner/Affiliate Engine (partner registry, commission engine, approval workflow, revenue attribution, commission history, partner analytics, partner trust score, contract lifecycle, multi-partner support); (3) Executive Safety Principles (permanent neutrality — no political/religious/ethnic-classification/hate/manipulation/privacy-violation/government-interference content); (4) upgrade Self-Evolution from event-driven into continuous analysis across customer behaviour, marketplace behaviour, partner performance, support requests, revenue trends, operational bottlenecks, publishing/delivery/architecture/security quality — founder approval remaining mandatory; (5) Commercial Maturity — one shared architecture ready for subscriptions, affiliate revenue, marketplace commissions, premium services, B2B/enterprise licensing.

This directive followed directly from the Executive Gap Report delivered the same session (a 15-dimension, 4-parallel-research-pass audit), which independently ranked marketplace publish-rate/cooldown protection as the single highest-leverage next implementation, and separately found Partner/Affiliate/Commission readiness blocked on a real structural gap — no payables ledger exists anywhere in this factory's financial model.

## Scope decision: Priorities 1 + 3 + a light touch on 4 this round; 2 + 5 explicitly deferred

Three parallel research passes (channel/publish architecture; the Executive Brain's existing risk/proposal/sub-score/gate patterns; the financial-ledger architecture) confirmed Priority 1 was buildable now, entirely by extending existing, stable modules — no new financial primitive required. Priority 2, by contrast, needs a payables/liability concept that does not exist in `finance_data.json` or `channels/ledger.py` today (exactly one revenue-recognition event type pair, `publish_attempt`/`sale`, ever recorded) — building a commission engine on top of that gap inside the same cycle as a safety-critical publish-protection layer would mean inventing money-owed bookkeeping under time pressure, which is precisely the kind of rushed financial-integrity risk the directive's own "Financial Integrity" standard warns against.

This matches the founder's own established precedent for exactly this situation (CLAUDE.md's global/country-expansion section, 2026-07-23: document readiness, defer building until a real trigger — first real dollar or first real local data connector, whichever comes first, not before). Priority 2 and Priority 5 are documented here as the scoped starting point for a future round, not built now.

## What was built

**Marketplace Publish Protection Layer — `channels/publish_protection.py` (new).** A real, disk-persisted (atomic tmp-file-then-rename, same pattern as `factory_state.py`), per-arm state machine: `check_publish_allowed()` (blocks on an active global emergency stop, an open failure-cooldown, a hit daily/hourly cap, or unmet minimum publish spacing; a disclosed `risk_score` 0-100 informs how close an *allowed* publish is to being blocked, never itself a block), `note_publish_outcome()` (updates counters/cooldowns after a real attempt), `trigger_emergency_stop()`/`clear_emergency_stop()` (global, founder-only). `PLATFORM_PROFILES` covers Amazon KDP, Etsy, Gumroad, Payhip, Shopify, and AliExpress by name — even though only Gumroad/Etsy/Payhip/Paddle have a real registered `BaseArm` today (KDP/Shopify/AliExpress are genuinely greenfield, confirmed by research) — via a conservative `_default` profile, honestly generic rather than hardcoded to what exists yet.

**Integration.** `distributor.py::distribute()` calls `check_publish_allowed()` immediately before every real (non-dry-run) `arm.publish()` — a blocked arm never reaches the real platform call, isolated per-arm exactly like an unsupported product or an unregistered arm already were. Dry runs are exempt entirely (zero real-world effect, so gating them served no safety purpose and would have been an unnecessary behavior change). `channels/ledger.py::record_publish_attempt()` gained optional `risk_score`/`protection_decision` kwargs — omitted from the event when not given, so every pre-existing caller's event shape is byte-for-byte unchanged. A blocked attempt is still recorded to the existing `data/sales_ledger.jsonl` audit trail, honestly labeled `protection_decision: "blocked"`.

**Mission Control.** A read-only `publish-protection-status` panel (`SERVICE_REGISTRY`) and two founder-only sync actions, `publish-emergency-stop`/`publish-emergency-resume` (`ACTION_REGISTRY`), mirroring `pause-production`/`resume-production`'s exact `kind: 'sync'`, in-process shape — no subprocess/timeout risk on an action meant to be instant.

**Executive Brain integration (Priority 4, light-touch).** `tool_intelligence/proposals.py` gained a 5th dynamic generator, `_marketplace_protection_proposal()` — fires only on a real active emergency stop or a real arm showing repeated failures/an open cooldown, honestly `None` otherwise. `executive_score.py` gained a `publishing_safety` sub-score (`_real`/`_unknown`, informational only — an active emergency stop is a real, directly-measured 0, not "Unknown"). `founder_console.py::build_founder_queue_partial()` surfaces an active emergency stop as a real pending-decision item, same integration style as its existing DEFERRED-decisions/evolution-proposals counts. Most of "continuous analysis" (customer behaviour, revenue trends, operational bottlenecks) was already built this session's Autonomous Evolution Engine work (ADR-133) — this round only adds the one genuinely new signal source.

**Executive Safety Principles.** `executive_quality_gate.py::check_content_neutrality_risk()` — a new named hard-reject criterion (added to `REJECT_IF_FAIL`), exact shape of `check_brand_reputation_risk()` (real phrase-list content scan, honestly `UNKNOWN` with no content given). `OpenClaw_Brain/00_Governance/EXECUTIVE_SAFETY_PRINCIPLES.md` records the founder's nine-category "never evolve toward" list verbatim as permanent policy.

## What was explicitly deferred (documented, not built): Partner/Affiliate/Vendor/Commission Engine + Commercial Maturity

Confirmed by research: zero real scaffolding exists today (one placeholder catalog entry, `growth_engine.py`'s `_CHANNEL_CATALOG`, unset credential env var). A future round building this would need:

- A payables/liability concept added to `finance_data.json`, plus a new `commission_accrued`/`commission_paid` event type in `channels/ledger.py` (today: `publish_attempt`/`sale` only).
- A `source`/`origin` field on `decision_engine/types.py::Decision` to distinguish a partner-submitted opportunity from an internally-discovered one (today: `decision_path` only distinguishes evaluation *method*, not submitter identity).
- A revenue-split/counterparty-share field somewhere in `profit_oracle.py`'s pricing output (today: single-party by design).
- A Partner Trust Score reusing `ai_capability/registry.py`'s real REAL/DISCOVERY-over-time pattern (never invented) — backed by a new `data/partner_*_log.jsonl`.
- A new `data/commission_history.jsonl` following this factory's standard append-only convention (same pattern as `data/decisions.jsonl`).

One genuine bright spot found, needing no rework at all: `customer_pipeline.py::fulfill_manually()` already accepts any real local file or `https://` URL with zero assumption Galaxy Forge itself produced the item — a vendor-fulfilled order could flow through the existing pipeline today unmodified.

This is the documented starting point for that future round — revisited when either a real trigger fires (first real partner interest) or the founder explicitly asks to build it anyway, matching this factory's own established country-expansion precedent.

## Validation

New/updated tests: `tests/test_publish_protection.py` (new, 16 tests — full state-machine coverage, injected temp state paths), `tests/test_distributor.py` (+4, the pre-publish gate integration; all 4 pre-existing tests re-verified with zero regressions), `tests/test_ledger.py` (+2, the new optional kwargs' backward compatibility; all 14 pre-existing tests re-verified), `tests/test_mission_control_api.py` (+4, the three new dispatch endpoints, mocked), `tests/test_executive_score.py` (+3, the `publishing_safety` sub-score), `tests/test_tool_intelligence.py` (+5, the marketplace-protection proposal generator), `tests/test_founder_console.py` (+2, the emergency-stop signal, plus 3 existing tests updated for isolation), `tests/test_executive_quality_gate.py` (+5, `check_content_neutrality_risk()`; all 34 pre-existing tests re-verified with zero regressions), `tests/test_enterprise_readiness.py` (all 38 pre-existing tests re-verified with zero regressions). Full regression: `tests/test_api_contract.js` (29/29) confirms the new `publish-protection-status` service responds correctly through the real authenticated server.

Live E2E: verified the pre-publish gate blocks a real (mocked) arm's `publish()` call outright under an active emergency stop, that the block is honestly recorded to the ledger, and that an allowed arm publishes and updates its real counters — all via `distributor.distribute()` directly, exactly the call path a real production run uses.

## What's still honestly Unknown / not built

`publishing_safety` stays `Unknown` until at least one real (non-dry-run) publish attempt has ever been recorded for any arm — true today, since KDP/Shopify/AliExpress have no registered arm and Etsy/Payhip/Paddle remain dry-run only pending real credentials/Paddle's own onboarding gate. `check_content_neutrality_risk()`'s phrase list is a real, cheap, non-exhaustive first pass — not a substitute for human judgment, same honest limitation `check_brand_reputation_risk()` already discloses about itself. The Partner/Affiliate/Commission Engine and Commercial Maturity (Priorities 2 and 5) remain fully undeployed by design, per the scope decision above.
