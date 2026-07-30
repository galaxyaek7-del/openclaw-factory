# Architecture Cluster 2 — Market Intelligence & Evidence

**Scope:** market_intelligence_engine.py, competitor_discovery.py, market_evidence.py, market_memory.py, market_hunter.py, market_alerts.py, evidence_network.py, evidence_completeness.py, capability_registry_scanner.py, market_intelligence_core/, multi_source_intelligence/, real_market_evidence/, real_world_mode/, tool_intelligence/proposals.py, ai_capability/.

**Summary:** This cluster is unusually well-disciplined for a 20-module intelligence layer — nearly every file's docstring explicitly cites which ADR it was born from and which prior module it deliberately does NOT duplicate, and one real duplicate (a byte-for-byte identical `_http_get_json`) was already found and fixed by a prior architecture review (2026-07-16, consolidated into `market_intelligence_core/http_client.py`, ADR-049). That discipline is real but incomplete: two independently-built "evidence source catalog" registries (`evidence_network.py` and `multi_source_intelligence/`) now coexist without ever having been compared to each other, one full production function has zero real callers, and every external call in this cluster is unauthenticated against rate-limited public APIs with no backoff logic anywhere.

---

### Core Opportunity Analysis (market_intelligence_engine.py + competitor_discovery.py)
- **Files:** market_intelligence_engine.py, competitor_discovery.py
- **Purpose:** The one integrated per-niche analysis engine (customer pain via GitHub Issues/HN/StackOverflow, demand pattern, competitor landscape) — explicitly built as "ONE integrated decision system, not separate tools" per founder instruction (ADR-043/042).
- **Inputs:** niche string, optional external_signal, cached DBs (`data/pain_evidence_cache.json`, `data/competitor_database.json`).
- **Outputs:** `analyze_opportunity()` / `discover_competitors()` structured results; feeds `profit_oracle.opportunity_score()` via `external_signal`.
- **Dependencies:** both import `market_intelligence_core.http_client`; imported by `market_intelligence_core/core.py`, `evidence_network.py`, `real_market_evidence` (indirectly via profit_oracle), `mission_control_api.py`.
- **Current maturity:** REAL for customer pain (GitHub Issues + HN, keyless) and competitor discovery (GitHub Search + HN Algolia, keyless); demand-pattern "Exploding/Declining" honestly `Unknown — insufficient history` (own docstring); pricing intelligence explicitly `NOT BUILT`.
- **Business value:** primary real evidence feed for every opportunity evaluation in the factory.
- **Technical debt:** none found beyond the disclosed pricing gap (already honest, not fabricated).
- **Risk level:** MEDIUM (scalability/reliability) — both modules hit unauthenticated GitHub Search (10 req/min limit) and HN Algolia with no rate-limit backoff; see Cross-cutting §6.
- **Recommendation:** KEEP — real, load-bearing, honest about its own gaps.

### Market Intelligence Core plugin layer (market_intelligence_core/)
- **Files:** core.py, http_client.py, market_review.py, pipeline.py, registry.py, types.py, scoring/*.py (8 scorer plugins)
- **Purpose:** An additive plugin-scoring layer on top of `market_intelligence_engine.analyze_opportunity()` — attaches a `dimension_scores` dict (8 dimensions: demand, competition, profit_margin, pricing_power, risk, execution, trend_stability, confidence), never replaces the legacy result shape (ADR-049).
- **Inputs:** niche, tier, external_signal (same contract as the engine it wraps).
- **Outputs:** `EvaluationContext` → `Score` objects (raw_data/normalized_score/confidence/explanation — a real, enforced uniform contract via `types.py`).
- **Dependencies:** wraps `market_intelligence_engine`; `types.CONFIDENCE_SCALE` is reused by `multi_source_intelligence/types.py` (good cross-package reuse, not duplication).
- **Current maturity:** REAL — deliberately kept out of `profit_oracle.py`'s synchronous scoring path (same standalone-orchestrator rule as its dependencies).
- **Business value:** richer, extensible per-dimension scoring without touching the tested production path.
- **Technical debt:** `registry.py`'s decorator-registry pattern (`register_scorer`/`get_scorers`, ~20 lines) is near-byte-identical to `multi_source_intelligence/registry.py`'s `register_connector`/`get_connectors` — see Cross-cutting §4.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Multi-Source Evidence Accumulation (multi_source_intelligence/)
- **Files:** aggregator.py, coverage.py, registry.py, types.py, connectors/*.py (11 source connectors: amazon, arxiv, etsy, github, google_trends, gumroad, hacker_news, product_hunt, public_search, reddit, stack_overflow)
- **Purpose:** ADR-059 — evidence coverage across 11 named external sources, explicitly built as a standalone, NOT-wired-into-production tool ("No production logic may change. Only improve evidence quality" — founder's own words, cited in the docstring).
- **Inputs:** niche.
- **Outputs:** `evidence_coverage_score()` (checked/succeeded/failed/unknown per source).
- **Dependencies:** `evidence_coverage_score()` IS called for real from `mission_control_api.py` (`/api/v1/...` panel, confirmed via grep) and `server.js`; `accumulate_evidence()` (aggregator.py) is not.
- **Current maturity:** Mixed and real per-connector — verified by grep: `arxiv.py`, `github.py`, `hacker_news.py`, `stack_overflow.py` make real `http_client` calls; `gumroad.py`/`etsy.py` are conditionally real (only if a channel arm is registered/credentialed); `amazon.py`, `google_trends.py`, `product_hunt.py`, `public_search.py`, `reddit.py` unconditionally `return unavailable_result(...)` — 5 of 11 named sources are permanent stubs today, honestly disclosed per-connector but never rolled up anywhere as "5/11 real."
- **Business value:** the Mission Control evidence-coverage panel; a real, if partial, second opinion alongside `evidence_network.py`.
- **Technical debt:** **`aggregator.py::accumulate_evidence()` has zero real callers anywhere in the repo** — confirmed via `grep -rn "accumulate_evidence"` across every `.py`/`.js` file: the only two hits are inside `tests/test_multi_source_intelligence.py` itself. A full module (26 lines, its own file) exists solely to be unit-tested, never invoked by any real code path, dashboard, or CLI. Its own docstring calls this deliberate ("available for a human... to consume"), but nothing — no Mission Control button, no CLI entry, no doc — actually exposes that consumption path.
- **Risk level:** LOW (isolated, doesn't block anything) but a genuine simplification candidate.
- **Recommendation:** REFACTOR — either wire `accumulate_evidence()` into a real, reachable entry point (Mission Control action or documented manual CLI usage), or delete `aggregator.py` and have callers use `coverage.evidence_coverage_score()` directly (which is already the real, used function it wraps with almost no added value — `accumulate_evidence()` only renames 2 keys).

### Amazon-specific Evidence (real_market_evidence/)
- **Files:** evidence_collector.py, types.py
- **Purpose:** ADR-058 — Amazon marketplace evidence sourced EXCLUSIVELY from `profit_oracle._find_niche_report()`'s already-saved `niche_validator_v2` reports; explicit permanent boundary: "no live Amazon scraping, ever."
- **Inputs:** niche (looked up against already-saved reports, no live fetch).
- **Outputs:** `Evidence` objects (metric/source/confidence/raw_value), `evidence_quality_summary()`.
- **Dependencies:** imports `profit_oracle`, `market_intelligence_core.types.CONFIDENCE_SCALE`; referenced by `golden_hunter/hunt.py`, `mission_control_api.py`.
- **Current maturity:** REAL for metrics present in a saved report; honestly `Unknown` (with a stated structural reason per metric) for BSR/marketplace_age/update_frequency/seller_concentration/revenue_indicators — none of which Amazon exposes on a single search-results snapshot.
- **Business value:** real Amazon-derived evidence without the legal/technical risk of live scraping.
- **Technical debt:** see Cross-cutting §2 — models the same real-world concept ("do we have Amazon evidence for this niche") as `multi_source_intelligence/connectors/amazon.py`, which is a permanent stub. Neither module references the other.
- **Risk level:** LOW.
- **Recommendation:** KEEP, but see §2 recommendation to cross-link/document the split with the `amazon.py` connector.

### Real-World Signal Intake (real_world_mode/)
- **Files:** operating_mode.py, signal_intake.py
- **Purpose:** ADR-056 — thin, deliberately-run entry point feeding real external signals (OPPORTUNITIES.md, tier1_intake candidates) through the existing `orchestrator.run_cycle()`, adding zero new decision logic.
- **Inputs:** OPPORTUNITIES.md, `tier1_intake/candidates/*.json`.
- **Outputs:** shaped `(niche, external_signal)` tuples into the orchestrator's existing contract.
- **Dependencies:** reuses `profit_oracle._read_opportunities()` directly (not a second parser); imported by `mission_control_api.py`.
- **Current maturity:** REAL, small, low-risk.
- **Business value:** real bridge from manually-curated research into the automated pipeline.
- **Technical debt:** none found.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Evidence Network — production connector registry (evidence_network.py + evidence_completeness.py)
- **Files:** evidence_network.py, evidence_completeness.py
- **Purpose:** ADR-128 — the real, extensible connector registry `evidence_completeness.acquire_missing_evidence()` dispatches through generically, keyed by `evidence_completeness.py`'s own scoring CRITERIA (e.g. `difficult_to_copy`, `pain_severity`), not by source name.
- **Inputs:** niche + a criterion name.
- **Outputs:** REAL/DISCOVERY-tagged `EvidenceConnector` metadata + real fetch dispatch.
- **Dependencies:** imports `competitor_discovery`, `market_intelligence_engine`; imported by `evidence_completeness.py`, `mission_control_api.py`. Confirmed 2 real production callers via grep (beyond its own tests).
- **Current maturity:** REAL — every REAL connector persists to an already-real cache (`competitor_database.json`, `pain_evidence_cache.json`).
- **Business value:** the actual dispatch mechanism behind "which evidence source resolves which decision-scoring gap," directly load-bearing for every niche's evidence-completeness score.
- **Technical debt:** see Cross-cutting §1 — structurally near-identical concept to `multi_source_intelligence/`'s registry, built 5 real days earlier, never cross-referenced.
- **Risk level:** LOW individually; MEDIUM at the architecture level (§1).
- **Recommendation:** KEEP, but see §1 — a follow-up round should decide whether `multi_source_intelligence/` sources should register as `evidence_network` connectors instead of maintaining a second parallel catalog.

### Market Evidence Ledger + Commercial Memory (market_evidence.py + market_memory.py)
- **Files:** market_evidence.py, market_memory.py
- **Purpose:** the permanent, append-only evidence store the Executive Quality Gate reads automatically (market_evidence.py); a 17-dimension commercial-event enrichment that attaches to the SAME `closed_sale` events rather than writing a second store (market_memory.py).
- **Inputs:** real sale events (via `channels/ledger.py`), manually/Claude-recorded evidence events.
- **Outputs:** `record_evidence()`/`read_evidence()`, `build_commercial_event()`, `monthly_evolution_report()`.
- **Dependencies:** `market_memory.py` imports `market_evidence` only (correct — extends, doesn't duplicate storage). Both real production modules confirmed wired to `decision_engine/feedback.py::sync_outcomes()`.
- **Current maturity:** REAL infrastructure, honestly near-empty of data (zero/near-zero real sales recorded factory-wide per repeated CLAUDE.md disclosures) — this is a data-volume gap, not a code gap.
- **Business value:** the real "does the market actually confirm this niche" feedback loop.
- **Technical debt:** none found; explicit anti-fabrication docstring ("Building a fake autonomous market sensor here would be exactly the kind of fabrication this whole engagement has refused everywhere else").
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Market Hunter (market_hunter.py)
- **Files:** market_hunter.py
- **Purpose:** Golden Hunter niche generation — curated business-problem categories + real Sensing Engine signals, scored exclusively through `profit_oracle.ladder_opportunity_score()` (explicitly "not a second, duplicate scorer").
- **Dependencies:** imports nothing from this cluster directly load-bearing besides its own knowledge-brain search; scored via profit_oracle (outside this cluster).
- **Current maturity:** REAL, explicitly non-fabricated ("no live market-research API integration... never a fabricated live data pull").
- **Business value:** primary niche-candidate generator.
- **Technical debt:** none found in this scope.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Market Alerts (market_alerts.py)
- **Files:** market_alerts.py
- **Purpose:** on-demand competitive-intelligence alerting, reusing `competitor_discovery.py`'s diffs and `market_evidence.py`'s competitor-landscape event categories — explicitly "reuses, never duplicates."
- **Current maturity:** REAL, deterministic severity/confidence (no freely-generated judgment).
- **Business value:** surfaces real competitor changes (new entrants, funding, etc.) to Mission Control/Executive Board.
- **Technical debt:** none found.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Tool Intelligence Proposals (tool_intelligence/proposals.py)
- **Files:** tool_intelligence/proposals.py
- **Purpose:** real, evidence-cited improvement proposals (3 hand-written + 6 dynamically generated from live factory signals) feeding `evolution_queue.py`'s intake — already extensively documented/verified in this session's own prior work (ADR-133/143).
- **Current maturity:** REAL.
- **Recommendation:** KEEP (no new findings beyond what this session already verified in ADR-143 work).

### Capability Registry Scanner (capability_registry_scanner.py)
- **Files:** capability_registry_scanner.py (46 lines)
- **Purpose:** flags every `config/capability_registry.json` entry below REAL level — deliberately no staleness/age filter (no per-entry timestamp exists, so it refuses to fabricate a "days open" number).
- **Current maturity:** REAL, minimal, clean.
- **Risk level:** LOW.
- **Recommendation:** KEEP — a model example of appropriately-scoped simplicity; nothing to simplify further.

### AI Capability Registry (ai_capability/)
- **Files:** registry.py, evaluator.py, orchestrator.py
- **Purpose:** REAL/DISCOVERY metrics per AI provider (only Groq has real data); `orchestrator.generate()` is the real multi-model dispatcher, honest that it currently has exactly one real provider path.
- **Dependencies:** 9 real callers across the repo confirmed via grep (autonomous_business_builder, build_in_public, ceo_decision_center, department_health, executive_score, global_opportunity_exchange, integration_registry, market_intelligence_engine, mission_control_api) — the best-integrated module in this cluster.
- **Current maturity:** REAL infrastructure around a single real provider; explicitly not fabricating comparative data for uncalled providers.
- **Business value:** the literal mechanism behind CLAUDE.md's "لا ولاء لأي موديل ذكاء اصطناعي" (no AI-model loyalty) principle.
- **Technical debt:** none found.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

---

## Cross-cutting findings

**1. Duplicate responsibility — two parallel, uncompared evidence-source registries.**
`evidence_network.py` (ADR-128, 2026-07-25) and `multi_source_intelligence/` (ADR-059, 2026-07-20-ish) independently invented the same structural pattern: a named external source with a REAL/DISCOVERY status tag, reliability/cost/latency-style metadata, and a real fetch callable. `evidence_network.py` is keyed by *decision-scoring criterion* and wired into production (`evidence_completeness.acquire_missing_evidence()`); `multi_source_intelligence/` is keyed by *source name* and deliberately unwired. Neither module's docstring mentions the other, even though `evidence_network.py` was built 5 real days after `multi_source_intelligence/` in the same repository. This is exactly the class of duplication a prior architecture review already caught once in this same cluster (`_http_get_json`, fixed via ADR-049) — evidence that duplicate-detection here is incident-driven, not systematic. **Recommend:** a scoped follow-up decide whether `multi_source_intelligence`'s 11 sources should register through `evidence_network.py`'s connector shape instead of maintaining two catalogs, or explicitly document why they must stay separate.

**2. Overlapping logic — "Amazon evidence" modeled twice with contradictory maturity.**
`real_market_evidence/evidence_collector.py` (real, reads saved report data) and `multi_source_intelligence/connectors/amazon.py` (permanent stub, always `unavailable_result`) both claim to answer "what Amazon evidence exists for this niche," with no cross-reference between them. A caller using `multi_source_intelligence` would wrongly conclude Amazon evidence is never available, when `real_market_evidence` may actually have real data for the same niche.

**3. Dead code — `multi_source_intelligence/aggregator.py::accumulate_evidence()`.**
Verified via `grep -rn "accumulate_evidence" --include=*.py --include=*.js .`: zero callers outside its own test file. A full module exists to be unit-tested only.

**4. Unnecessary complexity — near-identical plugin-registry boilerplate repeated per-package.**
`market_intelligence_core/registry.py` and `multi_source_intelligence/registry.py` are ~20-line files with near-byte-identical decorator/dict/getter shapes (`register_scorer`/`_SCORERS`/`get_scorers` vs `register_connector`/`_CONNECTORS`/`get_connectors`). This pattern likely repeats again outside this cluster (`orchestrator/registry.py`, `asset_generation/registry.py`, `content_generation/registry.py`, `product_families/registry.py`, `product_packaging/registry.py` — named but out of this cluster's scope, flagged for whichever cluster covers them). A single generic `make_plugin_registry(kind_name)` factory function could collapse each of these into ~3 lines without introducing cross-package coupling (each package still owns its own registry instance).

**5. Obsolete modules:** none found in this cluster — every file is either actively called or explicitly, honestly marked standalone/deliberately-run.

**6. Scalability / security risk — unauthenticated external HTTP with no rate-limit handling.**
Verified via grep: neither `market_intelligence_core/http_client.py` nor `competitor_discovery.py`'s local HTTP helper sends any `Authorization`/`Bearer` header. Every GitHub Search API call in this cluster (`competitor_discovery.py`, `market_intelligence_engine.py`, `multi_source_intelligence/connectors/github.py`) is unauthenticated, which GitHub caps at 10 requests/minute (vs. 30/minute authenticated) — and no backoff/retry/queueing logic exists anywhere in `http_client.py` (a bare `urllib.request.urlopen(timeout=10)`). A burst of niche evaluations (e.g. a Golden Hunter batch run, or several `analyze_opportunity()` calls in one Mission Control session) can silently degrade real evidence to `Unknown`/`unavailable_result` rather than failing loud or queueing — a real risk that scales down decision quality exactly when factory throughput scales up, with no alert surfacing it today.

**7. Maintainability risk:** low overall in this cluster — docstring discipline is genuinely exceptional (every file states its ADR, its real/DISCOVERY boundary, and what it deliberately does not duplicate). The one maintainability gap is §1/§2 above: the discipline is per-file, not cross-file, so two files can each individually be honest and well-documented while still describing the same real-world concept in contradictory ways to each other.

**8. Simplification opportunities:** §3 (delete or wire up `aggregator.py`), §4 (registry factory), and — smaller — `capability_registry_scanner.py` is small enough it could arguably live as a function inside `evolution_queue.py`'s own `_capability_gap_proposal()` caller rather than a separate 46-line file, though this is a genuinely minor call either way (LOW priority, not listed in the main recommendations above).
