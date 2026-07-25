# ADR-127 — Evidence Completeness Engine

**Date:** 2026-07-25
**Status:** Adopted.

---

## The directive

Founder decision: "Unknown" must never automatically behave like "False". Before rejecting an opportunity for missing evidence, the factory should try to acquire that evidence first. Every scoring criterion needs one of 4 real states (VERIFIED_TRUE / VERIFIED_FALSE / UNKNOWN / NOT_APPLICABLE), an Evidence Coverage report, a new `RESEARCH_REQUIRED` lifecycle state instead of a direct reject, confidence tied to coverage%, and every rejection should carry recommended research actions and an "estimated value if evidence becomes available." Priority: reduce uncertainty, not maximize rejections — "Galaxy Forge must become an evidence-seeking company, not merely an evidence-checking company."

## The real problem this fixes

ADR-121/122/126 already refuse to treat missing evidence as a pass ("absence of evidence is never a pass," stated identically in all three). But their gate booleans (`has_payment_evidence`, `is_difficult_to_copy`, `has_competitive_advantage`, ...) collapse two genuinely different situations into the same `False`: *"we checked and it's genuinely bad"* and *"we haven't checked yet."* That collapse is correct for the accept/reject decision itself (both situations should block acceptance) but wrong for everything the founder actually wants next — knowing whether more research would help, and what to research. This is exactly the gap the directive names.

## What was built

**`evidence_completeness.py`** (new module) — a real, parallel 4-state classification layered over `profit_oracle.ladder_opportunity_score()`'s already-computed real fields. Never recomputes scoring, never triggers a live query itself (same "no live query inside scoring" principle `_score_defensibility()`/`_score_market_signal()`/`_score_urgency()` already established) — `classify_criteria()` only reads an already-computed result.

Of the 11 real criteria this factory can name today (the founder's 10 from ADR-126, plus ADR-122's own Pain Severity gate — not literally numbered by the founder but part of the same real hierarchy and just as capable of being genuinely Unknown):

- **5 are always real/deterministic and never Unknown** — Competition, Premium Pricing, Global Scalability, Long-Term Strategic Value, High Profit Margin. Each is backed by a saved report, a passed external signal, or a deterministic keyword/ladder-constant computation that always produces a real number (confirmed by reading `_score_competition()`/`_score_margin()`/`butter_price()`'s own source — none of them can return `None`).
- **3 can be genuinely Unknown** — Proof of Payment (zero evidence recorded ≠ confirmed no market — this factory has no negative-search-confirmation mechanism), Pain Severity (no `external_signal` passed), AI-Significant-Advantage (zero keyword matches either direction in the niche's own text).
- **2 are permanent, honest gaps** — High Commercial Value, Continuous Improvement Potential. No real per-opportunity signal exists anywhere in this factory (ADR-126's own audit). Always `UNKNOWN`, never gated, never fabricated.

`NOT_APPLICABLE` is part of the enum (required by the directive) but is never actually produced by today's 11 criteria — every one of them genuinely applies to every opportunity. Documented rather than forced into use.

**Evidence Coverage report** (`evidence_coverage_report()`) — real counts: `coverage_pct` (verified + not-applicable, over total), `verified_count`, `unknown_count`, `missing_evidence` (the real list of Unknown criterion names). **Confidence** (`confidence_from_coverage()`) is deliberately the coverage percentage itself — the simplest honest mapping (confidence IS how much real evidence exists), not a second, separately-invented curve.

**`RESEARCH_REQUIRED` lifecycle state** — `assess()` decides the real final status: `ACCEPTED` if the ladder gate already accepted; `RESEARCH_REQUIRED` if rejected AND coverage is below `DEFAULT_RESEARCH_THRESHOLD_PCT` (80%, roughly "more than 2 of 11 criteria still Unknown" — disclosed, not tuned against any real outcome data yet) AND at least one Unknown criterion has a real, automatable acquisition path not yet attempted; otherwise a real, final `REJECTED` — honest, because deferring a decision that has no real way to gather more evidence would never actually resolve. `decision_engine.record_ladder_decision()` gained an optional `evidence_report` parameter that, when passed, uses this real lifecycle status instead of the plain accepted/rejected binary; omitting it (every existing caller) reproduces the exact prior behavior, byte for byte (regression-tested). `decision_engine/types.py`'s `STATUSES` now documents `RESEARCH_REQUIRED` as a 4th real value.

**Real, honest acquisition scope.** Of the 3 criteria that can be Unknown, only 2 have a genuine automated acquisition path today:
- **Difficult to Copy** → `competitor_discovery.get_or_refresh_competitors()` — real, cached GitHub+HN search. Fires without a separate opt-in (bounded real cost — a cache hit is nearly free, a real refresh is one bounded search).
- **Pain Severity** → `market_intelligence_engine.analyze_customer_pain()` — real, but **uncached**, live GitHub Issues + HN + Stack Overflow search every call. Opt-in only (`gather_pain=True`), same cost-consciousness ADR-122 already established for declining to auto-wire this into every `hunt_market()` candidate (~30 real external calls per hunt otherwise).
- **Proof of Payment** — genuinely has no automated path (no job-posting/pricing-page/marketplace scraper exists anywhere in this factory). `acquire_missing_evidence()` reports this honestly instead of fabricating a search, with a concrete recommendation: manual research, then `market_evidence.record_evidence()`.

**"Estimated value if evidence becomes available"** — not a new projection. Gates never change `ladder_score`/`price`, only accept/reject — so the real answer to "what would this be worth if the Unknowns resolve favorably" is the exact same already-computed `ladder_score`/`price` this niche already has, explicitly conditioned on which criteria are still Unknown (`estimate_value_if_verified()`). Proven by test to never return a different number than the real input.

**A CLI** (`python evidence_completeness.py <niche> --ladder=X [--acquire] [--gather-pain]`) for manual/deliberate invocation — mirrors `market_evidence.py`/`competitor_discovery.py`'s own standalone-module convention.

## Validation

29 new tests (`tests/test_evidence_completeness.py`): every classification rule proven (the core "real weak signal ≠ Unknown" and "zero evidence ≠ confirmed false" distinctions each get a dedicated test), coverage math, `estimate_value_if_verified()` never inventing a number, all 3 `assess()` lifecycle branches (accepted / research-required / honest-final-reject), acquisition opt-in behavior for both real connectors (mocked), and one real end-to-end acquisition test against an isolated `db_file` (never the real shared `data/competitor_database.json`). `record_ladder_decision()`'s backward-compatibility (omitting `evidence_report` reproduces prior behavior exactly) is explicitly regression-tested. Live-smoke-tested via the CLI against a real known niche (`workflow automation system for logistics companies`) — correctly returns `RESEARCH_REQUIRED` at 54.5% coverage instead of a flat reject, and correctly performs a real competitor-discovery acquisition when `--acquire` is passed.

## What's deliberately not done this round

- **Not wired into `market_hunter.hunt_market()`'s automatic tick.** Auto-running evidence acquisition on every real hunt candidate would repeat ADR-122's own declined tradeoff (real, uncontrolled external-API cost growth) — this stays a deliberate, explicit, per-niche capability a caller invokes when they want the deeper research pass, matching the founder's own "whenever economically justified" framing rather than "always."
- **No Mission Control dashboard surface yet.** The Coverage/Verified/Unknown/Missing-evidence report the founder described ("For every opportunity display: Coverage: 92%...") is a real, ready-to-render JSON shape (`assess()`'s own output) but wiring a new panel into `mission_control_executive_v1.html` is a separate, scoped follow-up, not bundled into this already-large round.
- **`DEFAULT_RESEARCH_THRESHOLD_PCT = 80.0`** is a disclosed starting point, not validated against real outcome data (no real accepted-after-research case exists yet to calibrate against) — revisit once real RESEARCH_REQUIRED → RESEARCH_COMPLETE cases accumulate.
- **No automatic re-scoring loop** ("RESEARCH_COMPLETE → FINAL_SCORING" from the founder's own pipeline diagram) — today a caller re-runs `ladder_opportunity_score()` + `assess()` manually after acquiring evidence; a scheduled/automatic re-check was not requested explicitly and would need its own scoping (matches this factory's "no scheduler" architecture, documented in CLAUDE.md).
