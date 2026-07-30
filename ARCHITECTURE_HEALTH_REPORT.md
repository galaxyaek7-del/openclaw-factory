# Galaxy Forge — Architecture Health Report

**Date:** 2026-07-30
**Type:** Architecture Stability Review (read-only — no production code modified)
**Method:** 5 parallel evidence-gathering passes across every production subsystem (~110 files across 5 clusters), each using module docstrings, real repo-wide `grep` caller checks, and a real AST-based import graph (`dependency_graph.py`, run live: 218 internal modules, 0 parse errors). No claim in this report is asserted without a cited grep result, import edge, or docstring quote. Full per-subsystem detail (Purpose/Inputs/Outputs/Dependencies/Maturity/Business Value/Technical Debt/Risk/Recommendation for every subsystem, not condensed) lives in the 5 source cluster reviews under `OpenClaw_Brain/00_Governance/architecture_review_2026-07-30/`: `cluster_1_production_publishing.md`, `cluster_2_market_intelligence.md`, `cluster_3_decision_value_engines.md`, `cluster_4_governance_resilience.md`, `cluster_5_customer_server.md`. This top-level document is the synthesized summary; §4 below is a condensed index into those 5 files, not a replacement for them.

---

## 1. Scores (0–100)

| Dimension | Score | Rationale |
|---|---|---|
| **Overall architecture score** | **68 / 100** | A well-disciplined, honestly self-documenting codebase carrying real but named, non-urgent structural debt. Zero critical defects found; zero fabrication found; zero security vulnerabilities found. The gap to a higher score is entirely surface-area proliferation and two hub files, not correctness. |
| **Stability score** | **82 / 100** | No crash-causing defects found anywhere. `dry_run`-by-default, atomic tmp-then-rename writes, and honest-degradation-over-fabrication are enforced consistently across every cluster (verified, not assumed). Deducted for: 2 real circular-import chains (§3) and 2 outsized single-file hubs (`server.js` 288KB/~195 endpoints, `mission_control_api.py` 102KB) that concentrate blast radius. |
| **Maintainability score** | **65 / 100** | Genuine strengths: exceptional docstring discipline (every file states its own ADR, its real/DISCOVERY boundary, and what it deliberately does not duplicate — verified true in every file read), and a real, demonstrated self-correction history (`path_safety.py`, `lib/jsonl.js`, `integration_registry.py`'s MiniMax fix). Genuine weaknesses: 12+ distinct "executive layer" concepts, 9+ Mission Control prioritization panels, several naming collisions (`scheduler.py` vs. a Windows Scheduled Task panel; `golden_hunter/` vs. `market_hunter.py`), and 2 hub files that every feature round touches. |
| **Scalability score** | **55 / 100** | Every real scalability gap found is already self-disclosed in the code as "fine today, real concern at N× real volume" — never ignored, never hidden. Concretely: linear full-file scans of `decisions.jsonl`/`sales_ledger.jsonl` per call (no index), a synchronous/no-queue `distributor.py` (explicit, deliberate scope boundary), and unauthenticated external API calls (GitHub Search, HN Algolia) with zero backoff/retry logic anywhere in `http_client.py`. None of these are active problems — real recorded volume across the whole factory is near-zero (dozens of decisions, ~zero completed sales) — but none has a fix in progress either. |
| **Automation score** | **58 / 100** | Reflects genuine, *intentional* restraint, not a gap. This factory has no scheduler by design (confirmed: `factory_loop.js` has no cron, no `package.json` script entry, runs only when manually started) and explicitly keeps 4 irreversible-action gates human-only (evolution-queue Execute, capital reallocation, business retirement, new-channel/elevated-risk publishing) — a documented decision reaffirmed as recently as ADR-142. Within those bounds, real automation is substantial: 7+ daily-gated report/measurement functions run automatically once the tick is started, and the resilience monitor runs every tick. |
| **Technical debt score** | **70 / 100** | Real, named, mostly small items: one still-open, already-self-disclosed 3-way niche-scorer redundancy (`market_analyzer.py`, dating back to 2026-07-15); two independently-built, uncompared evidence-source catalogs (`evidence_network.py` vs. `multi_source_intelligence/`); one confirmed dead function (`multi_source_intelligence/aggregator.py::accumulate_evidence()`); 2 real import cycles; and one confirmed false-positive in the repo's own dead-code-detection tool (`dependency_graph.py`). None are correctness bugs. All were found via evidence, not inferred. |
| **Business alignment score** | **72 / 100** | Every subsystem reviewed ties to a real, documented business rationale (ADR citation, founder directive, or CLAUDE.md cross-reference) — zero fabricated features, zero invented metrics found anywhere across ~110 files. The one honest tension worth naming: build velocity (roughly one major new module every 1–2 days across this session's own history) has outpaced revenue validation (near-zero real recorded sales company-wide) — in tension with the repo's own stated golden rule ("no expansion before the first real dollar"), even though every individual module's construction was itself evidence-audited and justified. |

---

## 2. Dependency Graph — Real Findings

Computed live via `dependency_graph.py::build_graph()` (AST-parsed imports, 218 internal modules, 0 parse errors) rather than hand-drawn.

**10 real import cycles, 2 families:**

1. **Production plugin-registration cycle** (6 path variants of one root cause): `book_generator ↔ inspectors ↔ profit_oracle ↔ product_families ↔ product_families.generic_adapter ↔ asset_generation.builders.pdf_builder ↔ book_generator`, plus a variant through `dossier_bundle.build_bundle ↔ production_factory.dossier ↔ revenue_pipeline.plan`. Root cause: the self-registering plugin architecture (Universal Production Engine) naturally creates a cycle between the generic dispatcher and the concrete generators it dispatches to.
2. **Executive-orchestration cycle** (4 path variants): `executive_board → value_engine → factory_orchestrator → executive_board`, plus variants through `opportunity_pipeline`, `decision_reopen`, `revenue_pipeline.pipeline`. Root cause identified precisely: `value_engine.py` imports `factory_orchestrator.py`, which imports `executive_board.py`, which imports `value_engine.py` — closing the loop. This is the one edge (`value_engine → factory_orchestrator`) worth removing first.
3. **`master_loop ↔ mission_control_api`** (2-node cycle): `master_loop.py` imports `mission_control_api.py` to call 2 live functions, while `mission_control_api.py` imports `master_loop.py` in the reverse direction. This **directly violates a rule documented in this same repo** (`infrastructure_bridge.py`'s own docstring: "`mission_control_api.py` is a thin CLI dispatcher, not meant to be imported as a library by other modules") — the one confirmed instance of that rule being broken.

None of these cycles cause a runtime failure today (confirmed: full test suite, server, and factory_loop.js all run cleanly) — they are real, verified coupling, not live bugs.

**28 modules flagged "zero dependents"** by the graph's own `find_zero_dependent_modules()`. **This list contains at least one confirmed false positive** (`evidence_completeness.py` — actually imported by 6 real files: `autonomous_operations_status.py`, `decision_engine/engine.py`, `decision_engine/types.py`, `evidence_network.py`, `mission_control_api.py`, plus 2 tests) and several confirmed-intentional cases (`orchestrator/engines/*`, `market_intelligence_core/scoring/*`, `multi_source_intelligence/connectors/*` — all self-register via `pkgutil` at import time, which the tool's module-level-only import scan cannot see). **The tool's known limitation**: it only tracks module-top-level imports, missing this codebase's extensive lazy/function-local `import X` pattern (used throughout `mission_control_api.py`, `evolution_queue.py`, `tool_intelligence/proposals.py`). Roadmap item #1 below addresses this.

---

## 3. Cross-Cutting Findings (all 5 clusters, consolidated)

### 3.1 Duplicate responsibilities
- **CONFIRMED, open**: `market_analyzer.py` is a 3rd, independently-maintained "is this niche good" scorer alongside `profit_oracle.score_opportunity()`/`niche_validator_v2.py` — self-disclosed in its own docstring since 2026-07-15, never consolidated. It is live (`server.js:3873`, `POST /api/market-analyze`) but always returns the same static 3-answer table regardless of input.
- **CONFIRMED, open**: two independently-built evidence-source catalogs — `evidence_network.py` (ADR-128, wired into production via `evidence_completeness.acquire_missing_evidence()`) and `multi_source_intelligence/` (ADR-059, deliberately unwired) — solve structurally the same problem (named source → REAL/DISCOVERY status → fetch callable) without ever cross-referencing each other, despite being built 5 real days apart in the same repo.
- **Investigated and REJECTED as findings** (verified via real evidence, not assumed): the `*_arm.py`/`*_publisher.py` channel pairs (legitimate adapter-pattern layering); Executive Board vs. Galaxy Council (different question, verified via docstring + zero problematic cross-import); Evolution Engine vs. Evolution Queue (report vs. state-machine, confirmed distinct); Founder Console vs. CEO Decision Center (approval filter vs. Q&A dashboard, zero cross-import); the 12+ "executive layer" modules broadly (every spot-checked pair either has zero cross-import or an explicit, verified-true "answers a different question" docstring claim).

### 3.2 Overlapping logic
- `evolution_engine.py`'s report and `tool_intelligence/proposals.py`'s dynamic proposal generators both independently call `executive_intelligence.bottlenecks.detect_bottlenecks()` / `strategic_intelligence.technical_debt` — same signals, computed twice per cycle by two separate assemblers with no shared cache. Wasteful, not wrong; a future drift risk if one is updated and the other isn't.
- `growth_engine.py` independently re-reads `decisions.jsonl` directly rather than going exclusively through `decision_engine.store`/`ranking` — a second real read-path (not write-path) into the same file.
- **Already found and fixed, cited as evidence the review discipline works**: `path_safety.py` (unified a real duplicate path-sanitization implementation between `book_generator.py`/`cover_designer_v2.py`), `lib/jsonl.js` (unified a JSONL-reading pattern independently reimplemented 8+ times, now permanently guarded by `scripts/check_jsonl_duplication.js`), the `market_intelligence_core.http_client` consolidation (ADR-049, fixed a byte-identical `_http_get_json` duplicate).

### 3.3 Dead code
- **One confirmed instance**: `multi_source_intelligence/aggregator.py::accumulate_evidence()` — zero callers anywhere outside its own test file (verified via repo-wide grep). A full module exists solely to be unit-tested.
- **No other confirmed dead code found.** The mechanically-generated 28-module "zero dependents" list (§2) is a real lead but not a verdict — one manually-checked entry was a false positive, and the other 27 were not exhaustively re-verified in this pass (explicitly time-scoped out, flagged as roadmap item #2, not silently skipped).

### 3.4 Obsolete modules
- `channels/gumroad_arm.py` — self-declared **ARCHIVED** (ADR-065, deprioritized after the Strategic Ladder pivot) but still self-registers and is still imported by 7+ real modules (`distributor.py`, `executive_intelligence/inactivity.py` + `revenue_distance.py`, `strategic_intelligence/channel_value.py`, `multi_source_intelligence/connectors/etsy.py`, `production_factory/dossier.py`, plus tests). Cannot be safely removed without a coordinated migration of all dependents.
- `master_loop.py` — real, live (2 functions reachable via Mission Control), but confirmed never wired into the automatic tick (3×-declined always-on-daemon precedent, ADR-107/110/115) — deliberately dormant, not obsolete.
- 3 previously-removed modules (`quality_doctor.py`, old `cover_generator.py`, old `niche_validator.py` v1) confirmed still gone and still unreferenced anywhere — no regression.

### 3.5 Architectural bottlenecks
- **`server.js`** (288KB, 126 `SERVICE_REGISTRY` + 69 `ACTION_REGISTRY` entries = ~195 real endpoints) and **`mission_control_api.py`** (102KB, ~120+ dispatch commands) are the two largest files in the repo by a wide margin and the real central hub nearly every other module is ultimately reached through. No internal quality defect found in either — the risk is pure concentration (every feature round touches both, confirmed by this session's own prior ADR-143 work).
- The 2 real import cycles (§2) are architectural bottlenecks in the coupling sense: none of their member modules can be tested, reasoned about, or refactored fully independently.

### 3.6 Scalability risks
- `decision_engine/store.py`'s `latest_decision_per_niche()`/`rank_all()` do a full linear scan of `decisions.jsonl` per call — fine at current real volume (dozens of records), a real future concern at thousands.
- `distributor.py` is explicitly synchronous/no-queue by design (disclosed, not hidden) — appropriate at current real publish volume (zero real completed sales via distributor.py to date).
- Every external call in the Market Intelligence cluster (`competitor_discovery.py`, `market_intelligence_engine.py`, `multi_source_intelligence/connectors/github.py`) hits unauthenticated, rate-limited public APIs (GitHub Search: 10 req/min unauthenticated vs. 30 authenticated; HN Algolia) via a bare `urllib.request.urlopen(timeout=10)` with **zero backoff/retry/queueing logic anywhere in `http_client.py`**. A burst of niche evaluations (e.g. a Golden Hunter batch run) can silently degrade real evidence to `Unknown`/`unavailable_result` rather than failing loud or queueing — the single highest-value scalability fix identified in this review, since it degrades decision *quality* silently exactly when usage scales up.

### 3.7 Maintainability risks (the single clearest cross-cluster pattern in this review)
Every cluster independently surfaced the same root cause from a different angle:
- **Cluster 3** (Decision/Value): 9+ Mission Control panels answer overlapping "what matters most" questions (`opportunity-queue`, `unified-priorities`, `opportunity-pipeline`, `executive-score`, `global-opportunity-exchange`, `investment-score`, `get-investment-pipeline`, `get-portfolio-report`, `get-company-reality-score`).
- **Cluster 4** (Governance): 12+ distinct "executive layer" modules (Executive Board, Galaxy Council, Executive Score, Executive Quality Gate, Evolution Engine, Evolution Queue, Founder Console, CEO Decision Center, Master Loop, Factory Orchestrator, Department Health, Execution Status, Enterprise Readiness) — 3 deliberately-separate governance rosters (Constitution's 12 Councils, Executive Board's 10 roles, Galaxy Council's 10 members) and 4 differently-scoped "orchestration"-named modules.
- **Cluster 2** (Market Intelligence): 2 parallel evidence-source catalogs (§3.1).
- **Cluster 5** (Customer/Server): 2 outsized hub files (§3.5).
- **Naming collisions found**: `scheduler.py` (opportunity execution-bucket classifier) vs. `server.js`'s `scheduler-status` Mission Control panel (an unrelated Windows Scheduled Task query, ADR-119) — 33 repo-wide grep hits for "scheduler," genuinely ambiguous without opening the file. `golden_hunter/hunt.py` vs. `market_hunter.py` — only the latter is what `factory_loop.js`'s real tick calls; a future reader could reasonably assume otherwise. `reality.py` vs. `reality_mode.py` — verified genuinely distinct (scorecard vs. taxonomy) but the near-identical names are a real minor friction.

**Verdict, stated plainly**: this factory's architecture discipline reliably prevents *computational* duplication (verified: every spot-checked "suspicious pair" this review investigated turned out to be genuine, evidence-backed layering, not accidental rebuilding) but has **no corresponding discipline that prevents *surface/panel* proliferation**. Nothing found is broken. The compounding cost is cognitive load for whoever — founder or a future Claude Code session with no memory of this review — has to figure out which of 12+ "executive" panels or 9+ "priority" panels to look at first.

### 3.8 Security risks
**Audited directly, no vulnerabilities found.** All 13 `child_process.spawn()` calls in `server.js` (independently re-counted during synthesis: `grep -c "spawn("` = 13, correcting the cluster review's "14") use the safe array-argument form (`spawn(cmd, [arg1, arg2, ...])`) — zero instances of shell-string concatenation with unsanitized input. The one `execSync()` template-string call (Python-interpreter auto-detection) is confirmed to only ever receive one of 3 hardcoded literal strings (`'python3'`, `'python'`, `'py'`) — no injection surface. No hardcoded credentials found anywhere (every credential-reading module explicitly documents reading from `.env` and never logging the value — verified present in each publisher's own docstring, not just claimed). `lib/customer_auth.js` uses a deliberately separate signing secret from Mission Control's own session token, preventing cross-privilege forgery. `path_safety.py` closes the one real path-traversal-adjacent risk found (confirmed both `book_generator.py` and `cover_designer_v2.py` now share it). No `eval`/`exec`(Python)/`shell=True`/`os.system` calls found anywhere across the ~110 files reviewed.

### 3.9 Unnecessary complexity / simplification opportunities
- Retire or clearly re-label `market_analyzer.py` as non-authoritative (§3.1).
- Wire up or delete `multi_source_intelligence/aggregator.py::accumulate_evidence()` (§3.3).
- `commercial_intelligence.py` (116 lines, pure aggregation, zero unique computation) is the cleanest literal MERGE candidate in the whole review — folding it into `opportunity_pipeline.py`'s own report removes a full file/import-surface for zero loss of real functionality.
- The near-identical plugin-registry boilerplate repeated across `market_intelligence_core/registry.py`, `multi_source_intelligence/registry.py`, `channels/registry.py`, `asset_generation/registry.py`, `content_generation/registry.py`, `product_families/registry.py`, `product_packaging/registry.py` (7 instances of the same ~20-line register/get pattern) could collapse into one generic `make_plugin_registry(kind_name)` factory function without introducing cross-package coupling.
- Mission Control panel consolidation (§3.7) — the single highest-leverage, lowest-risk simplification available: a presentation-layer-only regrouping of existing panels, zero computation change.

---

## 4. Subsystem Catalog

*(Condensed; full per-subsystem detail — Purpose/Inputs/Outputs/Dependencies/Maturity/Business Value/Technical Debt/Risk/Recommendation — is in the 5 underlying cluster reviews. This table is the actionable summary.)*

### Cluster 1 — Core Production & Publishing

| Subsystem | Maturity | Risk | Recommendation |
|---|---|---|---|
| Book/Cover Generation Core (book_generator.py, cover_designer_v2.py) | REAL/production | LOW | **KEEP** |
| Niche Validation (niche_validator_v2.py) | REAL, manual-trigger | LOW | **KEEP** |
| Dual Inspection QA Gate (inspectors.py) | REAL/production | LOW | **KEEP** |
| Distribution Backbone (distributor.py, channels/ledger+registry+base_arm) | REAL/production | LOW | **KEEP** |
| Channel Publishing Layer (4 arm+publisher pairs) | Mixed, honestly disclosed | LOW–MEDIUM | **KEEP** (gumroad_arm archived-but-load-bearing — no unilateral removal) |
| Publish Protection (channels/publish_protection.py) | REAL | LOW | **KEEP** |
| Niche Safety Filter (safety_filter.py) | REAL | LOW | **KEEP** |
| Legacy Market Analyzer (market_analyzer.py) | DISCOVERY/placeholder, live endpoint | LOW (tech), MEDIUM (trust) | **REFACTOR** — consolidate into profit_oracle or clearly re-label as non-authoritative |
| Standalone Seed/Audit Tools (audit_seed, hive_logbook_generator, seed_english_book) | REAL, intentionally standalone | LOW | **KEEP** |
| Universal Production Engine Registries (asset_generation/content_generation/product_packaging/product_families) | REAL | LOW | **KEEP** — reference pattern for other clusters |

### Cluster 2 — Market Intelligence & Evidence

| Subsystem | Maturity | Risk | Recommendation |
|---|---|---|---|
| Core Opportunity Analysis (market_intelligence_engine.py, competitor_discovery.py) | REAL for keyless signals | MEDIUM (rate-limit) | **KEEP** |
| Market Intelligence Core plugin layer | REAL | LOW | **KEEP** |
| Multi-Source Evidence Accumulation (multi_source_intelligence/) | Mixed (6/11 real connectors, 5/11 stubs, honestly disclosed) | LOW | **REFACTOR** — wire up accumulate_evidence() or delete it |
| Amazon-specific Evidence (real_market_evidence/) | REAL for saved-report data | LOW | **KEEP** |
| Real-World Signal Intake (real_world_mode/) | REAL | LOW | **KEEP** |
| Evidence Network (evidence_network.py + evidence_completeness.py) | REAL, production-wired | LOW (individually), MEDIUM (vs. multi_source_intelligence) | **KEEP**, but see §3.1 catalog-merge decision |
| Market Evidence Ledger + Commercial Memory | REAL infra, near-empty of data | LOW | **KEEP** |
| Market Hunter (market_hunter.py) | REAL | LOW | **KEEP** |
| Market Alerts (market_alerts.py) | REAL | LOW | **KEEP** |
| Tool Intelligence Proposals | REAL | LOW | **KEEP** |
| Capability Registry Scanner | REAL, minimal | LOW | **KEEP** |
| AI Capability Registry | REAL, best-integrated module in cluster | LOW | **KEEP** |

### Cluster 3 — Decision & Value Engines

| Subsystem | Maturity | Risk | Recommendation |
|---|---|---|---|
| Decision Ledger Core (decision_engine/) | REAL — single source of truth, verified | LOW | **KEEP** — cleanest module in cluster |
| Commercial Scoring Foundation (profit_oracle.py, economics.py) | REAL, honest about live-data gaps | MEDIUM (profit_oracle.py size/blast-radius) | profit_oracle.py: **REFACTOR** (split by signal group, not urgent); economics.py: **KEEP** |
| Opportunity Ranking & Aggregation (opportunity_pipeline, investment_pipeline, commercial_intelligence) | REAL, verified non-duplicative computation | LOW | **KEEP** all; commercial_intelligence.py is the clearest MERGE candidate if consolidating |
| Portfolio & Capital Allocation (portfolio_engine.py, capital_allocation_engine.py) | REAL, newest/most disciplined in cluster | LOW | **KEEP** |
| Growth, Decision-Reopen & Scheduling (growth_engine, decision_reopen, scheduler.py) | REAL | LOW–MEDIUM (naming collision) | growth_engine/decision_reopen: **KEEP**; scheduler.py: **KEEP logic, REFACTOR name** |
| Strategic Intelligence Core & sub-package | REAL, citation-layer done right | LOW | **KEEP** |
| Revenue Pipeline | REAL, load-bearing | LOW | **KEEP** |

### Cluster 4 — Governance, Executive, Autonomy, Trust & Resilience

| Subsystem | Maturity | Risk | Recommendation |
|---|---|---|---|
| AI Executive Board | REAL, deterministic | LOW (individually) | **KEEP** — 1 leg of import cycle 1a |
| Galaxy Council | REAL, verified distinct from Board | LOW | **KEEP** |
| Executive Score | REAL, purely informational | LOW | **KEEP** |
| Executive Quality Gate | REAL, the permanent production gate | MEDIUM (concentration) | **KEEP** |
| Evolution Engine + Evolution Queue | REAL, verified genuinely distinct | LOW | **KEEP both** |
| Business Blueprint Chain (ABB + business_dossier + production_blueprint) | REAL, textbook disclosed reuse | LOW | **KEEP all three** |
| Autonomous Operations Status | REAL, thin | LOW | **KEEP** |
| Founder Console | REAL, verified distinct from CEO Decision Center | LOW | **KEEP** |
| CEO Decision Center | REAL | LOW | **KEEP** |
| Department Health + Department Events | REAL, verified state/log split (not duplication) | LOW | **KEEP both** |
| Master Loop | REAL but narrow-in-use; violates a documented import rule | LOW (functional), rule violation | **REFACTOR** — extract its 2 live functions to break cycle 1b |
| Factory Orchestrator | REAL | MEDIUM — 1 leg of import cycle 1a | **REFACTOR** — break the cycle |
| Orchestrator Package (orchestrator/) | REAL/production, the actual live execution engine | LOW | **KEEP** |
| Dependency Graph tool | REAL, self-verified by use in this review | MEDIUM (own false-positive) | **REFACTOR** — fix the zero-dependents false-positive before future reliance |
| Reality Scorecard + Reality Mode | REAL, verified genuinely distinct | LOW | **KEEP both** |
| Enterprise Readiness | REAL | LOW | **KEEP** |
| Execution Status | REAL, most cross-referenced module in cluster | LOW | **KEEP** |
| Resilience Monitor + Safe Mode + Health Trend | REAL | LOW | **KEEP all three** |
| AI Doctor | REAL, honest quality_doctor.py replacement | LOW | **KEEP** |
| Factory State | REAL, Phase A only (disclosed) | LOW | **KEEP** |
| Integration Registry | REAL, self-correcting (MiniMax fix) | LOW | **KEEP** |
| Infrastructure Bridge | REAL, the one Python→JS call direction | LOW | **KEEP** |
| Path Safety | REAL, security-relevant, already a fix | LOW | **KEEP** |
| Research Department | REAL, safe-by-design | LOW | **KEEP** |
| Global Opportunity Exchange | Mixed REAL/DISCOVERY, honestly labeled | LOW | **KEEP** |
| Validation Layer (validation_layer/) | REAL, legitimate reporting layer over bottlenecks/engine_health | LOW | **KEEP** |
| Recovery (recovery/) | REAL | LOW | **KEEP** |
| Dossier Bundle | REAL | LOW | **KEEP** |
| Commercial Execution (commercial_execution/) | REAL | LOW | **KEEP** |
| trust/, diagnostics/, config/ (real content directories) | REAL, not placeholders | LOW | **KEEP** |

### Cluster 5 — Customer Platform, Server & Orchestration Surface

| Subsystem | Maturity | Risk | Recommendation |
|---|---|---|---|
| HTTP Service Layer (server.js) | REAL/production | MEDIUM (concentration) | **REFACTOR** (long-term) — split registries into per-domain files |
| CLI Dispatch Hub (mission_control_api.py) | REAL/production | LOW–MEDIUM (breadth/change-frequency) | **KEEP** the lazy-import pattern; **REFACTOR** (long-term) same as server.js |
| No-Scheduler Tick Engine (factory_loop.js) | REAL, manually-triggered by design | LOW | **KEEP** |
| Customer Platform Pipeline (customer_pipeline, contract_generator, invoice_generator) | REAL, deterministic/template-only | LOW | **KEEP** |
| Marketing / Build-in-Public | REAL | LOW | **KEEP** |
| Knowledge Graph (knowledge_graph/build.py) | REAL, mechanical parse | LOW | **KEEP** |
| lib/*.js Shared Primitives (14 files) | REAL, model extraction pattern | LOW | **KEEP** — template other clusters' concentration findings should refactor toward |
| Ops Scripts (scripts/, 19 files) | REAL, manual-invocation-only by design | LOW | **KEEP** all |

---

## 5. Prioritized Roadmap — Before Any New Feature Work

Ordered by (real evidence of value) ÷ (effort), highest first. None of these are urgent in the sense of an active defect — every item addresses a named, disclosed risk, not a hidden one.

1. **Fix `dependency_graph.py`'s zero-dependents false positive.** Cheap, unblocks trustworthy future dead-code audits (this review's own most-reused tool has a confirmed accuracy gap). *Effort: low. Value: high — everything downstream of "what's dead" depends on this being trustworthy.*

2. **Manually verify the remaining ~26 "zero-dependent" modules** flagged by `dependency_graph.py` (one of 28 checked this review, confirmed a false positive). Cheap per-module grep check; prevents both accidental future deletion of load-bearing code and continued uncertainty about real surface area. *Effort: low. Value: medium.*

3. **Break the 2 real import cycles.** (a) Remove `value_engine.py`'s import of `factory_orchestrator.py` (the one edge that closes the executive-orchestration cycle) — likely only needs specific fields passed as parameters. (b) Extract `master_loop.py`'s 2 live functions (`trace_lifecycle`, `mission_control_heartbeat`) so the bulk of the file doesn't need to import `mission_control_api.py` at all, resolving the rule-violating cycle. *Effort: medium. Value: high — real coupling reduction, not cosmetic.*

4. **Retire or clearly re-label `market_analyzer.py`.** The oldest still-open, self-disclosed finding in the repo (since 2026-07-15). Either repoint its one real caller (`POST /api/market-analyze`) to `profit_oracle.score_opportunity()`, or add a UI-visible "static reference table, not live" disclosure matching the code comment that already exists internally. *Effort: low. Value: medium — closes a real, long-standing trust gap between what a live endpoint implies and what it delivers.*

5. **Resolve `multi_source_intelligence/aggregator.py::accumulate_evidence()`.** Wire it into a real, reachable entry point, or delete it. *Effort: low. Value: low-medium (small, isolated).*

6. **Fix the 3 naming collisions found**: rename `scheduler.py` or its Mission Control panel; add a disambiguating docstring line to `golden_hunter/hunt.py` ("not what factory_loop.js's tick calls — see market_hunter.py"); add a one-line cross-reference between `reality.py`/`reality_mode.py`. *Effort: very low. Value: medium — pure discoverability fix, prevents a future session repeating this review's own investigation time.*

7. **Decide the fate of the two parallel evidence-source catalogs** (`evidence_network.py` vs. `multi_source_intelligence/`) — either register `multi_source_intelligence`'s 11 sources as `evidence_network` connectors, or explicitly document why they must stay separate. *Effort: medium (needs a real design decision, not just code motion). Value: medium-high — prevents the two from silently diverging further.*

8. **Mission Control panel consolidation.** Group the 12+ "executive layer" panels (Cluster 4) and 9+ "prioritization" panels (Cluster 3) into fewer top-level tabs/sections with existing panels nested underneath. Presentation-layer only — zero computation change, zero risk to correctness. *Effort: medium. Value: highest single item on this list — this is the one finding independently surfaced by 4 of the 5 cluster reviews, making it the most cross-validated recommendation in this entire report.*

9. **Add backoff/retry/rate-limit awareness to `market_intelligence_core/http_client.py`** before any Golden Hunter batch-volume increase. Currently a bare `urllib.request.urlopen(timeout=10)` against unauthenticated, rate-limited public APIs with no protection — the one scalability finding with a plausible near-term trigger (a batch run), unlike the others which require 100× current volume. *Effort: low-medium. Value: medium — prevents a real, silent evidence-quality degradation under realistic (not hypothetical) load.*

10. **Split `server.js`/`mission_control_api.py` into per-domain registry files** (e.g. `registries/evolution.js`, `registries/customer.js`, self-registering into one shared table at startup — the exact `channels/registry.py` pattern already proven correct elsewhere in this repo). Preserves identical runtime behavior. *Effort: high (touches the two largest, most cross-cutting files in the repo). Value: real but long-term — no bug evidence forces urgency; correctly the last item on this list, not the first.*

**Explicitly NOT recommended**: no subsystem in any of the 5 clusters was found to warrant **REMOVE**. No subsystem was found to warrant **SPLIT** except the two hub files (item 10, already captured). Every "duplicate-sounding" pair investigated (§3.1) was either confirmed genuinely distinct or already correctly flagged by its own authors — this factory's core architecture does not need a rebuild, only a surface-area tidy-up.
