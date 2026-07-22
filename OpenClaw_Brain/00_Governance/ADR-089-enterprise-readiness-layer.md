# ADR-089 — Enterprise Readiness Layer

**Date:** 2026-07-22
**Status:** Adopted. Built, tested (993 Python / 199 JS, zero regressions), live-verified, one real bug found and fixed live.

---

## The directive, and the two decisions the founder made before any code was written

The founder ordered a permanent Enterprise Readiness Layer across the factory: 10 named product reviews, an 8-part opportunity risk register, full documentation requirements, a Risk Intelligence Engine, a Business Continuity Engine, and a Customer Trust Layer — nothing enters production without passing every gate.

This is a large enough directive that two real tensions with the founder's own "never fabricate, never estimate" instruction were surfaced and resolved by him directly before any code:

1. **Legal/security/privacy reviews** — this factory employs no lawyer, security professional, or privacy officer. The founder confirmed: build these as **honest, clearly-labeled proxy checks** (deterministic, real signals), always disclosed as not a genuine expert review — never silently presented as one.
2. **Retroactive scope** — applying "nothing enters production without passing every gate" literally would have immediately flagged all 5 already-shipped, checkout-ready products (none has had a real legal/security/customer-success/support review). The founder confirmed: **prospective only**. The 5 products keep an honest, permanent `PRE_GATE` status, never a silent retroactive rejection.

## What was built — `enterprise_readiness.py`

**Part 1 — Product Review Gate (10 reviews).** 5 reuse real, already-computed Executive Quality Gate (ADR-087) fields directly (operational, financial, scalability, competitive moat, plus legal as a disclosed proxy). 2 are new, real, deterministic checks: **security** (a content scan for insecure-practice phrases — no penetration test exists, none is claimed) and **support** (a real boolean: does a published support contact and refund policy exist — correctly `FAIL`s today, matching the Commercialization Audit's confirmed finding that neither exists anywhere in this factory). **Maintenance** is a real check against `data/product_changelog.jsonl` — correctly `FAIL`s for all 5 pre-gate products, since they were generated directly rather than through the changelog-tracked dossier pipeline, an honest finding, not papered over. **Customer success** auto-consumes the Market Learning Loop (ADR-088), honestly `UNKNOWN` while zero real customer interaction has been logged for a niche.

**Part 2 — Opportunity Risk Register.** Pure re-presentation of real Executive Quality Gate fields under the 8 named risk headers (market/technical/regulatory/competitive/execution risk) — zero new scoring. Exit criteria and kill-switch conditions are real, evidence-triggered rules, reusing the same discipline as the Kill-Test Verdict's decision framework (2026-07-22) — never a predicted probability.

**Part 3 — Documentation completeness**, product-type-aware and honest: for the static-PDF blueprints this factory actually ships, admin/disaster-recovery/incident-response documentation are marked `NOT_APPLICABLE` — there is no admin panel and no live infrastructure to have an incident about. Fabricating these documents to fill a checklist was explicitly rejected as worse than marking them honestly not applicable.

**Part 4 — Risk Intelligence Engine**, on-demand only (this factory has no scheduler — CLAUDE.md, reaffirmed again here rather than quietly violated). Real signals: competitor changes (via `competitor_discovery.py`'s cache, live refresh only on explicit request), customer complaints (Market Learning Loop). **Four categories — regulation changes, pricing changes elsewhere in the market, technology disruption, demand decline — have no real, funded data source in this factory and are reported as permanent, disclosed gaps**, never faked with a shallow check dressed up as real intelligence.

**Part 5 — Business Continuity Engine.** Not reimplemented: `run_backup_now()` is a thin wrapper over the already-existing `recovery/snapshot.py` (Unified Recovery System §7, built 2026-07-18). `check_dependency_health()` is a real, honest config-presence check for Groq/Paddle/Telegram — confirms a key is configured, not that the live service is currently reachable (a heavier, separate on-demand action).

**Part 6 — Customer Trust Layer.** Quality score reuses `inspectors.py`'s real Dual Inspection result directly. Evidence score is a real known/unknown ratio from a real gate run — never a fabricated 0–100 number. Trust score is an honest aggregate of three already-real signals, not one invented metric. The transparency report composes the gate's own real written explanation plus real market evidence — zero new narrative generated. Source verification is a real, new check: an attributed claim ("according to...") with no real cited source is a genuine `FAIL`. Audit trail formalizes real, already-existing logs (`data/decisions.jsonl`, `books/_generation_log.jsonl`, `data/product_changelog.jsonl`) rather than building a new one.

## A real bug found and fixed via live testing, not assumption

The first live run of the master gate against a real, already-shipped product (`workflow automation system for logistics companies`) came back `pre_gate_product: False` — wrong. The real Paddle product title ("Workflow Automation System for Logistics Companies") and the real `market_hunter` seed niche text it was scored under differ only in case. An exact string match silently failed to recognize an already-shipped product as pre-gate, which would have incorrectly reported it `REJECTED` instead of its honest `PRE_GATE` status — precisely the outcome the founder's second decision was meant to prevent. Fixed with case-insensitive matching; a live re-run confirmed `pre_gate_product: True`. Two regression tests added.

## Verification

- 36 new unit tests covering every review, the risk register, documentation completeness by product type, the Risk Intelligence Engine's honest gaps, Business Continuity wrapping, and the Trust Layer.
- Live-verified: the real support review correctly fails against this factory's actual current state (no refund policy, no support contact exist); real dependency health checks pass against the real `.env`; the master gate correctly reports `PRE_GATE` for a real shipped product after the fix above.
- Full suite: 993 Python tests (up from 957), 199 JS tests, zero regressions.

## Impact

- `enterprise_readiness.py` (new) — the permanent core layer.
- `mission_control_api.py`: new `enterprise_readiness_gate` and `risk_intelligence_scan` endpoints.
- `server.js`: new `enterprise-readiness-gate` and `risk-intelligence-scan` Mission Control actions.
- **What this ADR does not do, by design:** it does not un-publish, re-flag, or otherwise act on the 5 real shipped products — their `PRE_GATE` status is a real, honest record, not an automatic trigger for further action. Any decision to actually re-review them against this new gate is the founder's, separate and deliberate.
