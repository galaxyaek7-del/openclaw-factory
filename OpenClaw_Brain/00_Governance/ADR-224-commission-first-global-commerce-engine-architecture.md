# ADR-224 — Commission-First Global Commerce Engine: Full Architecture (documentation only, zero code)

**Date:** 2026-08-08
**Status:** Documented. **Zero new commission-engine code built, by explicit founder decision** (via `AskUserQuestion`, selecting "Document architecture only, zero new commission-engine code") — the same resolution ADR-148 (GCID) and ADR-152 (Global Affiliate Commerce Engine) already established for this exact class of directive.

---

## The directive (summarized — full text in the founder's Phase 31.5 message)

"Galaxy Forge will adopt a COMMISSION-FIRST commercial strategy... DISCOVER → QUALIFY → MATCH → REFER/SELL → TRACK → COLLECT COMMISSION → VERIFY → LEARN → SCALE." Golden Hunter becomes the "Commission Opportunity Hunter." Asks for: a commission-opportunity schema (Section 2), a Commission Economics scoring engine (Sections 4-5), a `COMMISSION_PARTNER` abstraction spanning affiliate networks/SaaS partner programs/agency programs/marketplaces/B2B referral/reseller/creator programs (Section 6), customer-problem matching (Section 7), a 14-stage deal pipeline (Section 8), auditable outreach automation (Section 9), a commission ledger (Section 10), a Mission Control "Commission Command Center" (Section 11), a Golden Hunter daily loop redesign (Section 12), and a long-term "sell → learn → build proprietary product" flywheel (Sections 14-15).

## The real conflict, verified before any code was written

Flagged via `AskUserQuestion` before any implementation began — this directive collides directly with two of the founder's own standing decisions, both still in force:

1. **ADR-150's Phase 2 gate** (Affiliate Commerce, 2026-07-30): before any expansion beyond the one real, narrow Phase 1 slice (Amazon Associates, one category, real click tracking), it requires a real confirmed conversion, sustained real click-through data, and a real tag configured. Verified directly this round: `AMAZON_ASSOCIATE_TAG` is still unset in `.env`; `data/affiliate_clicks.jsonl` does not exist (0 real clicks, ever).
2. **ADR-152's own recorded founder words**, from the same day: *"No further expansion of Affiliate Commerce should occur until a real affiliate account is approved and connected."* This directive's ask — a full multi-platform commission engine with outreach automation, a deal pipeline, and a commission ledger — is a materially larger expansion than the one ADR-152 already declined.
3. **Real, substantial overlap with already-built work**: `business_development.py` (ADR-188, 2026-08-07) already has a real, WebSearch-researched 21-platform registry (`PLATFORM_REGISTRY`) with real, evidence-cited program status per platform, and a real, persisted, append-only partnership pipeline (`data/partnership_pipeline.jsonl`) — the closest real analog to this directive's `COMMISSION_PARTNER` abstraction and deal pipeline already exists, just under a different name and a narrower, already-proven scope (partnership/integration opportunities generally, not commission-tracking specifically).

**The founder's answer, via `AskUserQuestion`: document the complete architecture now, build zero new commission-engine code.**

## Relationship to ADR-148, ADR-149, ADR-150, ADR-152, ADR-188

- **ADR-148 (GCID)**: deferred the full "Global Commerce Intelligence Division" vision — zero code, zero roadmap, because the factory had zero real dollars. Still true today (`AUDIT/COMMERCIAL_REALITY.md`, Phase 30.5: $0 real revenue, confirmed again as of Phase 31).
- **ADR-149/150**: the real, narrow Affiliate Commerce Phase 1 build (Amazon Associates) plus a 4-phase roadmap, each phase gated on real evidence.
- **ADR-152**: the detailed architecture for Affiliate Commerce's own Phase 3/4 (multi-network) — zero code, same resolution as this ADR.
- **ADR-188 (Global Business Development Division)**: the founder's own explicit Golden Rule override for a *general* partnership/affiliate/integration discovery engine — real, built, tested. This directive's `COMMISSION_PARTNER` concept is, in large part, a commission-specific re-framing of what `business_development.py` already does generally.
- **This ADR (224)** is the detailed design for what a genuine commission-first engine would look like *on top of* `business_development.py`'s real foundation — it does not move any of ADR-150's gates, and it does not duplicate ADR-188's real registry.

## Architecture (design only — every section below describes what would be built, not what has been built)

### 1. Primary Commercial Model (directive Section 1)

The 10 named priority categories (B2B referral, partner/reseller programs, service-provider referral, high-ticket affiliate, qualified lead-gen commissions, marketplace partner programs, SaaS referral, agency partnerships, strategic commission agreements, owned products as secondary) map directly onto `business_development.py::PLATFORM_REGISTRY`'s existing `program_type` field (`affiliate`/`partner`/`integration`/`reseller`, etc.) — no new taxonomy required, only a re-sort by the directive's own priority order once real per-category evidence exists to sort.

### 2. Opportunity Schema (directive Section 2)

The 20 named fields (`OPPORTUNITY_ID` through `STATUS`) would live in a new, real, append-only ledger (`data/commission_opportunities.jsonl`, not yet created) — modeled directly on `data/partnership_pipeline.jsonl`'s existing real schema (`platform`, `stage`, evidence citations), extended with the directive's commission-specific fields (`COMMISSION_MODEL`, `COMMISSION_RATE`, `ESTIMATED_COMMISSION`, `RECURRING_OR_ONE_TIME`). Every field would default to `UNKNOWN`/`UNVERIFIED` per the directive's own Section 3 rule — never populated speculatively.

### 3. No Fabrication (directive Section 3)

Already this factory's single most consistently-enforced discipline (`truth_first.py`'s canonical vocabulary, ADR-160; `simulation_mode.py`'s real/simulated separation, ADR-153) — this ADR commits any future real build to reuse those exact primitives rather than inventing a parallel honesty framework.

### 4-5. Commission Economics Engine + Commission-First Opportunity Score (directive Sections 4-5)

A real, deterministic scoring function (not yet created — would live in a new `commission_economics.py`) computing `EXPECTED_COMMISSION = deal_value × verified_commission_rate` and `EXPECTED_NET_VALUE = expected_commission − acquisition_cost − direct_costs`, keeping deal value/commission/revenue/profit/forecast in explicitly separate fields per the directive's own rule — the same discipline `enterprise_sales_engine.py::delivery_profitability()` (Phase 30) already established for a structurally identical calculation (and the same class of defect Phase 30.5's audit found and fixed there — a negative/unverified input must never silently produce a plausible-looking positive number). The 12-dimension opportunity score (Section 5) would reuse `goos.py::evaluate_dimensions()` and `commercial_autonomy_engine.py::commercial_opportunity_score()`'s existing decomposable-score pattern rather than a new one — verification confidence and program reliability would be new, genuine dimensions with no current real source.

### 6. `COMMISSION_PARTNER` Abstraction (directive Section 6)

The closest real precedent is `channels/base_arm.py`'s `BaseArm` contract (self-registering, credential-presence-gated, `NOT_IMPLEMENTED`-honest defaults) — a `COMMISSION_PARTNER` type would follow the identical pattern, but the directive's own named platform categories (affiliate networks, SaaS partner programs, marketplaces, B2B referral, reseller, creator, professional-service) are, today, **entirely `business_development.py::PLATFORM_REGISTRY` entries already** — 21 real, evidence-cited platforms, only 2 with any real tracked relationship (Paddle at `ACTIVE`, Amazon at `PREPARATION`, live-reconfirmed this round). No genuine new platform-discovery gap was found this round worth a fresh WebSearch pass — the existing registry is not stale relative to this directive's ask.

### 7. Customer Matching (directive Section 7)

The ICP/industry/company-size/pain-point schema would reuse `enterprise_sales_engine.py::ideal_enterprise_customer_profile()` (Phase 30) verbatim rather than a second schema — genuinely the same concept the founder already asked for and got, one phase earlier.

### 8. Deal Pipeline (directive Section 8)

The directive's 14 named stages (`DISCOVERED` → `PAID`) would relabel `data/partnership_pipeline.jsonl`'s real existing stages — the **4th** such relabeling this session of a real underlying pipeline (after Phase 25's 11-stage `LIFECYCLE_MAPPING`, Phase 30's 13-stage enterprise sales pipeline, and `business_development.py`'s own `STAGE_V2_MAPPING`) — never a 5th competing pipeline. Today, real data supports only the first 2-3 stages for the 2 real tracked relationships; everything from `OUTREACH_SENT` onward is unpopulated.

### 9. Outreach (directive Section 9)

**Zero outreach automation exists in this factory today** (confirmed by direct grep — no email/CRM-send integration anywhere), and none is built by this ADR. The directive's own "auditable, never spam, never impersonate" constraints would need a real, disclosed audit-log mechanism before any outreach code is written — a genuinely new capability class this factory has never had, not a relabeling of existing code.

### 10. Commission Ledger (directive Section 10)

A new, real, append-only ledger (`data/commission_ledger.jsonl`, not yet created), modeled on `channels/ledger.py`'s existing real event-append discipline, with the 8 named statuses (`EXPECTED` → `UNKNOWN`). Only `CONFIRMED`/`PAID` would ever count toward real commercial revenue — matching `AUDIT/COMMERCIAL_REALITY.md`'s already-established "only an independently verified real payment counts" rule, extended from direct sales to commission income.

### 11. Mission Control Commission Command Center (directive Section 11)

Would follow `commercial_activation.py`'s (Phase 31) real precedent for separating REAL/FORECAST/TEST/SIMULATION explicitly per field, never blended — but has nothing real to display today (0 real opportunities in the not-yet-created `data/commission_opportunities.jsonl`, 0 real ledger entries).

### 12. Golden Hunter Daily Loop (directive Section 12)

The 8-stage loop (`MARKET SCAN` → `CEO RECOMMENDATION`) would extend `market_hunter.py`/`profit_oracle.py`'s existing real daily hunt — provider discovery and commission-program discovery are the 2 genuinely new stages, requiring real, per-provider WebSearch verification (the same discipline `business_development.py` already established) before any opportunity could honestly carry a non-`UNKNOWN` commission rate. The directive's own explicit "must not automatically launch outreach" constraint is already this factory's default posture for every commercial action (autonomous_operations.py's Level 5/6 gates) — would require zero new authorization logic, only a citation.

### 13. First Commission Target / KPIs (directive Section 13)

`TIME_TO_FIRST_COMMISSION`/`COST_TO_FIRST_COMMISSION` would be new, real, honestly-`UNKNOWN`-until-earned KPIs — directly analogous to `enterprise_sales_engine.py`'s own `contract_value_tracker()` (Phase 30), which already established the identical "0 real records, honest empty state" pattern for a structurally identical first-deal metric.

### 14-15. Product Strategy Flywheel (directive Sections 14-15)

Already this factory's real, documented strategic philosophy in spirit — `CLAUDE.md`'s own "شركة استثمار رقمي" (digital investment company) framing and the Golden Rule ("no expansion before first dollar") are the existing real analogs. The specific "sell commission product → learn → build proprietary product" loop has no real trigger condition defined yet (would need a real "repeated expensive problem with no adequate existing provider" signal — a genuinely new pattern-detection capability, not yet built anywhere).

### 16. Quality and Trust (directive Section 16)

Restates this factory's already-real, already-enforced standing discipline (`truth_first.py`, `brand_dna.py::TRUST_PRINCIPLES`, `AUDIT/COMMERCIAL_REALITY.md`'s "$0 means $0, not simulated" rule) — no new enforcement mechanism needed, only a future commission-engine build inheriting what already exists.

## What this ADR does NOT authorize

No code. No new Python module (`commission_economics.py`, a `COMMISSION_PARTNER` class, `data/commission_opportunities.jsonl`, `data/commission_ledger.jsonl` — none created). No outreach automation of any kind. No Golden Hunter code changes. No Mission Control panel. This ADR is a complete design reference for when ADR-150's real gates clear (or the founder explicitly overrides them again for this specific initiative) — not a build authorization.

## Re-trigger conditions

Identical to ADR-152's, since this directive's core ask is a superset of what ADR-152 already covers:

- **Any real build here** requires ADR-150's own Phase 2/3 gate: a real completed Amazon (or any other real network's) conversion, confirmed via that network's own postback/reporting mechanism, plus sustained real click-through data.
- **The Mission Control Commission Command Center**: only meaningful once real commission-ledger data exists — building it against zero real entries would either duplicate existing panels or force fabricated fields.
- **Outreach automation specifically**: requires its own, separate founder authorization even after the above gates clear, given it is a genuinely new capability class (external human-facing communication) this factory has never had, with its own distinct risk profile from product-side commerce.
- **Full re-opening of this directive**: either (a) ADR-150's gate clears naturally (a real Amazon conversion), or (b) the founder explicitly overrides these gates again for this specific initiative, as already happened once for Affiliate Commerce Phase 1 (ADR-149).

---

*See also: `ADR-148-gcid-deferred.md`, `ADR-152-global-affiliate-commerce-engine-architecture.md`, `ADR-188` (Global Business Development Division, `business_development.py`), `AUDIT/COMMERCIAL_REALITY.md`.*
