# Company Integration Map (Strategic Phase, 2026-07-19)

**Supersedes** `OpenClaw_Brain/00_Governance/COMPANY_INTEGRATION_AUDIT_20260718.md` for the opportunity-to-cash trace and the connectivity picture (that file predates `commercial_execution/`, `product_families/manifest.py`, and everything below — kept for its historical record, not deleted). This file exists because the founder asked, before any new code: review every completed subsystem, verify it's connected, find the real gaps, prioritize before building. This is that review, plus what was actually built from it.

## What was found (audit, before any code)

- **"Pioneer"** — undefined anywhere in the repo. Scoped this session as real, novel-candidate discovery (below).
- **"Researchers"** — a named-but-deliberately-unbuilt concept (`HIGH_VALUE_STRATEGY.md`, 2026-07-12): real per-product web research, explicitly gated on a manual founder request each time, not automated. Left as-is — this is a standing decision, not a gap.
- **The one real structural gap**: two separate, manually-invoked dispatch paths existed — `factory_loop.js`'s tick (discovery + decision only) and `orchestrator.run_cycle()` (the only path reaching production→publishing→learning). Neither triggered the other; nothing walked the full chain automatically. `orchestrator.py`'s own docstring confirmed this was a *deliberate* prior decision, not an oversight.
- **Mission Control** showed nothing from `commercial_execution/` or the Product Definition Registry (both built the day before) — real capabilities invisible in the actual dashboard.
- **`quality_doctor.py`** — a live, reachable endpoint (`/api/qa-check`) that fabricates its "fixes_applied" list; zero real callers; sat alongside the real QA gate (`inspectors.py`) as a silent, false-confidence risk.
- **`multi_source_intelligence/`'s 9 connectors** — real, tested, still zero live callers (confirmed unchanged from the prior audit).
- Time-series analytics, A/B testing, and customer support: real absences, not urgent (zero sales yet).
- The real sale → `decision_engine.learning` feedback loop: genuinely wired, just zero real throughput to date.

## What was built from it (this phase, in priority order)

### 1. The modern pipeline now has a real, gated trigger

`orchestrator.run_cycle()` gained `existing_decision=` — when a real decision already exists (e.g. `market_hunter.py`'s daily `record_ladder_decision()` call), `market_intelligence`/`decision` are skipped and reused instead of re-evaluated. **This is the safety mechanism that makes auto-wiring possible**: without it, calling `run_cycle()` from an automatic trigger would silently record a second, independent decision (and therefore a second `production_id`) for the same real opportunity — the exact duplicate-publishing risk every other layer of this factory already guards against.

`orchestrator/orchestrator.py` gained a real CLI (`python -m orchestrator.orchestrator --run-ladder-opportunity`, JSON in/out via stdin, same convention as `book_generator.py --json`). **Must be invoked with `-m`** — `orchestrator/types.py` shadows Python's own stdlib `types` module if run as a raw script path (same class of bug as Roadmap Step 3's `packaging/` → `product_packaging/` rename).

`factory_loop.js`'s `huntGolden()` now routes ladder-tagged opportunities through this CLI instead of the legacy `triggerGenerateBook()` — reusing the **exact same `FACTORY_AUTO_PRODUCE` gate** `AUTO_PRODUCE_ACTIVATION_CHECKLIST.md` already documents (no new env var, no new review process; that checklist's 2-day dry-run observation window still applies before the founder ever sets it to `true`). Non-ladder opportunities keep using the legacy path unchanged.

**Result**: the moment `FACTORY_AUTO_PRODUCE=true` (a decision that was already gated and documented, just never yet exercised against the modern pipeline), a real accepted opportunity now flows discovery → decision → production (Product Definition Registry) → publishing (Commercial Execution Layer, respecting each family's manifest) → learning, with zero manual step in between and zero risk of a duplicate decision/production.

### 2. Pioneer: real discovery upstream of Golden Hunter

`golden_hunter/pioneer.py` — real, novel-candidate discovery with no niche pre-specified (the genuine gap `market_hunter.py`'s own `ADR-028` comment already named: "the current source doesn't generate anything new"). v1 source: Hacker News's real, free, keyless Firebase API (`/v0/topstories.json`), a different endpoint from `competitor_discovery.py`'s existing Algolia *search* API (which needs a query already). Candidates feed into `market_hunter.hunt_market()`'s existing, unchanged scoring/recording loop — Pioneer never scores or accepts anything itself.

**Honest limits, not silently skipped**: Reddit needs registered app credentials not present in `.env` (`multi_source_intelligence`'s own Reddit connector is honestly `unavailable` for the same reason). Product Hunt/Google Trends aren't wired to any discovery-mode endpoint in this codebase yet. Both are real next steps for a v2, not claimed as done.

### 3. Mission Control now shows what it's missing

A new "التنفيذ التجاري" (Commercial Execution) tab surfaces real approval gates (which marketplaces are autonomous vs. need founder action, and why), the most recent real publish attempts, and the Product Definition Registry's real family/manifest status (category, generators, pricing, supported marketplaces) — both backend services already existed (Roadmap Steps 3-4); the gap was purely that no UI rendered them.

### 4. `quality_doctor.py` resolved honestly

Not removed (a live endpoint with unknown future use is a behavior change, not a default cleanup) — but its response now carries an explicit `warning` field disclosing that its "fixes" are fabricated and that `inspectors.py`'s Dual Inspection is the real, load-bearing QA gate. `CLAUDE.md` updated to stop describing it as if it were real.

## What's still manual by design (not a gap)

- **Researchers / `market_researcher`**: deliberately founder-request-gated, per `HIGH_VALUE_STRATEGY.md`. Not automated this phase, on purpose.
- **`FACTORY_AUTO_PRODUCE`/`FACTORY_LIVE_PUBLISH`**: still unset. Flipping them is the founder's own decision, gated by `AUTO_PRODUCE_ACTIVATION_CHECKLIST.md`'s existing review process — this phase made the modern pipeline *reachable* through that same switch, not automatic.
- **`multi_source_intelligence/`'s 9 connectors**: still not wired to anything live. A real, named opportunity for a future phase (per-niche evidence enrichment once real opportunities need deeper research), not touched here to avoid scope creep beyond what was actually prioritized.

## Tests

- `tests/test_orchestrator.py::TestExistingDecisionAvoidsDuplicateDecisionRecording` / `::TestCliRunLadderOpportunity` — the duplicate-decision safeguard and the CLI bridge, including a real (safe, read-only) subprocess smoke test.
- `tests/test_pioneer.py` — Pioneer's discovery logic, mocked, plus one deliberate real HN integration test.
- `tests/test_market_hunter_sensing_link.py` — Pioneer's integration into `hunt_market()`'s existing loop, including a real-failure-never-blocks-the-hunt test.
- Real, live, end-to-end verification performed directly (not just unit tests): a real server instance was started and both new Mission Control API endpoints (`commercial-execution`, `production-families`) were called with real authentication, confirming the exact response shape the new UI code consumes.
