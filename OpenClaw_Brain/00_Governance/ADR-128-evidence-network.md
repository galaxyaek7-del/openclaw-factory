# ADR-128 — Galaxy Forge Evidence Network

**Date:** 2026-07-25
**Status:** Adopted.

---

## The directive

Founder decision: scoring is no longer the priority — building Galaxy Forge's Evidence Network is. Every UNKNOWN criterion must declare which evidence source could resolve it. An extensible Evidence Connector architecture: each connector exposes source, reliability, refresh frequency, cost, latency, confidence contribution. Never hard-code scoring logic around one source — evidence sources must be modular. Mission Control must display Evidence Coverage, Evidence Freshness, Unknown Count, Research Queue, Top Missing Signals. Move toward proactive evidence collection. Every new connector must increase long-term intelligence for every future opportunity. "The competitive advantage is not better scoring. The competitive advantage is owning a richer evidence network than competitors."

## What was built

**`evidence_network.py`** (new module) — a real, extensible `EvidenceConnector` registry. Each connector declares `source`, `reliability`, `refresh_frequency`, `cost`, `latency`, `confidence_contribution`, `status` (`REAL` or `DISCOVERY`), and `criteria_resolved`. Same "real data only, `DISCOVERY` otherwise" discipline `ai_capability/registry.py` (Technology Investment Council) already established: no field is a fabricated numeric score — every `reliability`/`cost`/`latency` value is a real, verifiable, structural fact about a real API (documented rate limits, auth requirements, real measured behavior), or an honest `"Unknown — no real connector exists"` for a `DISCOVERY` entry.

**8 connectors registered — 2 real, 6 honestly `DISCOVERY`:**

| Connector | Status | Resolves | Real source |
|---|---|---|---|
| `competitor_discovery` | REAL | Difficult to Copy | GitHub Search API + HN Algolia (cached) |
| `customer_pain` | REAL | Pain Severity | GitHub Issues + HN + Stack Overflow (now cached, see below) |
| `job_posting_scanner` | DISCOVERY | Proof of Payment | Indeed/LinkedIn — not built |
| `pricing_page_scanner` | DISCOVERY | Proof of Payment, Premium Pricing | Competitor pricing pages — not built (extraction-reliability risk already documented in `market_intelligence_engine.py`) |
| `marketplace_listing_scanner` | DISCOVERY | Proof of Payment | Etsy/Gumroad/Amazon — not built |
| `patent_search` | DISCOVERY | Difficult to Copy | USPTO/Google Patents — not built |
| `enterprise_demand_signal` | DISCOVERY | High Commercial Value | Crunchbase/PitchBook — real known blocker, paid subscription required |
| `product_iteration_tracker` | DISCOVERY | Continuous Improvement Potential | No real per-opportunity concept of this exists anywhere in this factory yet |

Every one of the founder's own 10 named conditions (ADR-126) now has at least one declared source in this registry — including the ones this factory genuinely cannot query yet, satisfying rule 1 literally rather than only for the 2 criteria that happen to already be real.

**Modularity, not hard-coded dispatch (rule 3).** `evidence_completeness.acquire_missing_evidence()` (ADR-127) was rewritten: it no longer contains `if criterion == "difficult_to_copy": call competitor_discovery` — it asks `evidence_network.resolve_criterion(criterion, niche, **kwargs)`, which looks up the registry and dispatches to whichever real connector (if any) is registered for that criterion. Registering a new connector tomorrow requires zero changes to `evidence_completeness.py` — proven by test (`test_registry_declares_a_source_for_every_criterion_even_unbuilt_ones`). The same registry also now generates `RESEARCH_ACTIONS` (the human-readable recommendation shown for every Unknown criterion) live, rather than as a second, separately-maintained hard-coded dict.

**Real, persistent caching for the second connector — "every new connector must increase long-term intelligence" (rule 6), not just claimed.** `market_intelligence_engine.analyze_customer_pain()` was a real but **uncached** live search on every call (flagged as a known limitation in ADR-127). It now caches to `data/pain_evidence_cache.json`, mirroring `competitor_discovery.py`'s own `load_database()`/`save_database()`/`MAX_AGE_DAYS_DEFAULT` pattern exactly (`db_file`/`max_age_days`/`force` parameters, same names, same semantics) — a 14-real-day window (longer than competitor data's 7, since pain signals move slower). A second real call for the same niche within 14 days is now a genuine cache hit, not a repeated live query: the first real search becomes proprietary, accumulated intelligence instead of a one-off lookup.

**Mission Control surfaces (rule 4).** Two new real services, reusing the ADR-125 caching pattern (`runPythonServiceCached`):
- **`evidence-network-status`** → the connector registry itself (which sources are real vs. declared).
- **`evidence-coverage-status`** → `evidence_network.aggregate_evidence_report()` (real average coverage%, total Unknown count, the real Research Queue — every decision currently `RESEARCH_REQUIRED`, sorted by lowest coverage first — and Top Missing Signals, a real tally of which criteria are Unknown most often across every decision that carries an evidence snapshot) plus `evidence_network.evidence_freshness_report()` (real age stats over both real evidence caches, computed from each entry's own real timestamp).

Both wired into `mission_control_executive_v1.html` as two new sections: "Evidence Coverage & Research Queue" and "Evidence Network."

**Honest, current limitation on the aggregate report:** `aggregate_evidence_report()` only counts decisions recorded **after** ADR-127 (the ones that actually carry a persisted `evidence_completeness` snapshot). Today that's zero real decisions — the report says so plainly (`"لا قرارات مسجَّلة بعد تحمل تتبّع اكتمال الأدلة"`) rather than fabricating a number from decisions that never had this tracking. It will fill in automatically, with zero further code changes, as real `record_ladder_decision(..., evidence_report=...)` calls accumulate.

## A real, active pollution bug found and fixed mid-build

Adding a shared, default-path cache to `analyze_customer_pain()` immediately created a real risk this factory's tests already have a documented history of hitting. Every test class that calls `analyze_customer_pain()` or one of its real callers (`analyze_opportunity()`, `evaluate_and_decide()`, `hunt.run_hunt()`, `orch.run_cycle()`, `operating_mode.run_real_world_cycle()`) with a fixture niche string had **no path isolation for the new cache** — and every one of those classes' own docstrings already documents fixing the identical bug once before for `competitor_discovery.COMPETITOR_DB_FILE`. This is the same real bug class recurring for a second real cache, not a new kind of mistake.

Caught live across **three** separate full-suite regression runs, each run surfacing a class this fix hadn't reached yet:
1. `test_decision_engine.py`'s `TestEvaluateAndDecide` wrote `"a reproducibility test niche"`.
2. `test_golden_hunter.py`'s `TestRunHuntEndToEnd` and `test_orchestrator.py`'s shared `_IsolatedRunCycleTestCase` base (4 subclasses) wrote 10 more fixture strings (`"hunt cap test 0-3"`, `"hunt test low/high"`, `"a re-evaluation allowed test niche"`, `"a dry run safety test niche"`, etc.) — reached via a deeper transitive call chain a simple direct-call-site grep missed on the first pass.
3. `test_real_world_mode.py`'s `TestRunRealWorldCycle` wrote 4 more (`"real world mode test niche one/two"`, `"safety default test niche"`, `"evidence auto update test niche"`).

Rather than keep chasing individual call chains reactively, the actual root cause was named and the fix generalized: **every test class that already patches `competitor_discovery.COMPETITOR_DB_FILE` is, by construction, a class that reaches a real evidence-gathering call chain** — the same real signal this factory's own architecture already produces (ADR-041/042's original defensibility-caching fix). `grep -rl "COMPETITOR_DB_FILE" tests/` gives the exact, closed, complete set: 6 files, no more, no fewer. All 6 (`test_decision_engine.py`, `test_golden_hunter.py`, `test_market_intelligence_core.py`, `test_market_intelligence_engine.py`, `test_orchestrator.py`, `test_real_world_mode.py`) now also redirect `market_intelligence_engine.PAIN_EVIDENCE_DB_FILE` to an isolated temp path, verified by grep count (each shows at least 1 real reference) rather than by hoping the next regression run doesn't surface a 4th wave. Each polluted (untracked, same-session) file was deleted after being found. `test_market_intelligence_core.py`'s own byte-identical-output assertion was also updated: a real cache hit's `_cache`/`cached_at` fields legitimately differ from the original cache miss's (that is the entire point of caching), so those two fields are excluded from the equality check and asserted directly instead (`hit: False` then `hit: True`).

## Validation

17 new tests (`tests/test_evidence_network.py`): every connector has all 6 required real fields, every `DISCOVERY` connector has no fetch (never fabricates a working connector), every real connector has a callable one, every named criterion has at least one declared source, dispatch resolves the real connector or honestly reports none exists, exceptions are reported not swallowed. `tests/test_evidence_completeness.py`'s acquisition tests updated to patch the real underlying functions directly (`competitor_discovery.get_or_refresh_competitors`, `market_intelligence_engine.analyze_customer_pain`) rather than a now-removed direct import path. 2 new tests in `tests/test_mission_control_api.py` for the 2 new endpoints. Full Python suite green: 1507/1507 (1486 baseline + 17 evidence_network + 1 evidence_completeness + 3 mission_control_api), confirmed clean of any real-cache pollution on a final, third full-suite run after all 5 isolation fixes landed.

## What's deliberately not done this round

- **No proactive/scheduled evidence collection** (rule 5's "gradually move toward"). This factory's own documented "no scheduler" architecture (`CLAUDE.md`) means any real proactive collection would need to be a deliberate, manually-triggered batch job, not a background cron — not built this round; the registry and caching are the real prerequisite infrastructure for it, not the scheduler itself.
- **No 3rd, 4th, ... real connector.** The 6 `DISCOVERY` entries are honestly declared, not built — each has a real, named reason (paid subscription required, unreliable extraction risk, no metric defined yet, etc.), not a placeholder waiting on effort alone.
- **Research Queue / Top Missing Signals render as a generic nested KV block** in Mission Control, not a bespoke table UI — reuses ADR-124's existing flattening/collapsible-details rendering rather than building new dashboard components, matching "reuse before build."
