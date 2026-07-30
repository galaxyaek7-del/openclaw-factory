# Architecture Cluster 4: Governance, Executive, Autonomy, Trust & Resilience

**Scope:** 35 files across the top-level governance/autonomy layer plus `executive_intelligence/`, `orchestrator/`, `recovery/`, `validation_layer/`, `dossier_bundle/`, `commercial_execution/`.

**Cluster summary:** This is this factory's highest file-density, highest-overlap-risk cluster by name alone — dozens of "executive"/"orchestrator"/"reality"/"department" modules built across ~15 separate founder directives over 8 days (2026-07-19 to 2026-07-29). The good news, verified with evidence below (module docstrings, a real AST-based dependency graph via `dependency_graph.py`, and whole-repo caller greps — never assumed): almost every apparent naming collision is a genuine, previously self-disclosed, intentional layering decision, not accidental duplication. The real findings are narrower and more actionable: **two real circular-import chains**, **one architectural-rule violation** (`master_loop.py` importing the CLI dispatcher it's not supposed to import), and a **file-count-to-distinct-concern ratio worth flattening** even though no individual pair is bad duplication.

---

## Per-subsystem reports

### AI Executive Board
- **Files:** `executive_board.py`
- **Purpose:** Deterministic (non-LLM) approve/hold/reject judgment over one already-evaluated decision, across 10 named executive roles, each a citation of a real existing signal.
- **Inputs:** `executive_quality_gate.py`'s 20 criteria, `enterprise_readiness.py`'s product reviews/risk register, `market_evidence.py`'s logged events.
- **Outputs:** Per-role `{opinion, confidence, evidence, risk, recommendation}`, a real tally/consensus.
- **Dependencies:** imports `value_engine` (real, verified via `dependency_graph.py`); imported by `factory_orchestrator.py`, `mission_control_api.py`, `galaxy_council.py` (per its own docstring, as the precedent).
- **Current maturity:** REAL/production — 25 functions, explicitly deterministic-only, no LLM call.
- **Business value:** the actual accept/reject judgment gate for one decision.
- **Technical debt:** none found (no TODO/FIXME, no eval/exec/shell=True).
- **Risk level:** LOW individually — see Cross-cutting Finding 1 (circular import) for its real risk contribution.
- **Recommendation:** KEEP — but see Finding 1, its import of `value_engine` is one leg of a real 3-module cycle.

### Galaxy Council
- **Files:** `galaxy_council.py`
- **Purpose:** Answers a genuinely different question than the Board — "what does each intelligence domain currently believe about this niche, side by side" (informational, N-way honest disagreement) vs. the Board's "approve this one decision" (verdict). Explicitly documented as deliberately distinct in ADR-138.
- **Inputs:** 9 real per-domain signal producers (Strategic/Market/Production/Customer/Financial/Security/Resilience/Innovation/Executive-Memory).
- **Outputs:** Per-member `{opinion, confidence, evidence, risk, recommendation, founder_approval_required}`, `disagreement_detected`, a 3-way learning join (`data/council_recommendations.jsonl`).
- **Dependencies:** reuses `executive_board.py`'s tally/consensus pattern as its literal template (not a copy — confirmed via docstring).
- **Current maturity:** REAL/production, largest file in this cluster (36KB) — 16 top-level functions.
- **Business value:** the one place a founder gets 9 independent domain opinions on a niche without visiting 9 separate panels.
- **Technical debt:** none found directly, but see Finding 3 (governance-roster proliferation).
- **Risk level:** LOW.
- **Recommendation:** KEEP — genuinely distinct from Executive Board despite the name-adjacency; the docstring's own justification is verifiable, not just asserted.

### Executive Score
- **Files:** `executive_score.py`
- **Purpose:** One global company score + named sub-scores (Trust/Automation/Customer Happiness/Production Quality/Delivery Quality/Operational Stability/Architecture Health/Security Health/Technical Debt/Growth), each either a real computed number or honest `"Unknown"`.
- **Dependencies:** cites `value_engine.py`/`reality.py` as its precedent for "never a silently-assumed 0 or 100."
- **Current maturity:** REAL — 14 functions, purely informational (never touches accept/reject/production gates, per its own docstring).
- **Business value:** the one honest "how healthy is the company overall" number.
- **Technical debt:** none found.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Executive Quality Gate
- **Files:** `executive_quality_gate.py`
- **Purpose:** The mandatory pre-production gate every opportunity/product/report passes through — 20 named criteria, most real citations of existing signals, 2 genuinely new (`brand_reputation_risk`, `evidence_freshness`).
- **Current maturity:** REAL, largest-but-one file in cluster (31KB, 30 functions) — honestly discloses that several of its 20 requested criteria (willingness-to-pay, customer-acquisition-difficulty, customer-retention-potential) have no real automatic data source and are proxy/labeled as such.
- **Business value:** the actual permanent gate every real product passes through.
- **Technical debt:** none found; its own docstring is the most rigorous self-disclosure in the cluster.
- **Risk level:** LOW for the module itself; MEDIUM at the system level — this is a single point of failure for every product's quality gate (if this file has a bug, nothing ships safely). Concentration risk, not a code-quality risk.
- **Recommendation:** KEEP.

### Evolution Engine + Evolution Queue
- **Files:** `evolution_engine.py`, `evolution_queue.py`
- **Purpose:** `evolution_engine.py` is a READ-ONLY report (concatenates bottlenecks/tech-debt/high-ROI-opportunities/capability-gaps/tool-proposals into one document). `evolution_queue.py` is a STATE MACHINE for individual self-improvement proposals (PROPOSED→SIMULATED→AWAITING_FOUNDER_APPROVAL→APPROVED/REJECTED→IMPLEMENTED), Execute always human-gated by explicit founder decision.
- **Dependencies:** both independently call `executive_intelligence.bottlenecks`/`strategic_intelligence.technical_debt` — see Finding 2.
- **Current maturity:** REAL/production. `evolution_queue.py` is this cluster's 2nd-largest file (27KB, 21 functions) and the most actively-developed module this session (2 rounds, ADR-133 + ADR-143 with real outcome-measurement/ranking added 2026-07-30).
- **Business value:** the actual self-improvement proposal pipeline, with a real Learning History (`stage_history`) and now real before/after outcome measurement.
- **Technical debt:** Finding 2 (redundant signal computation, not redundant logic).
- **Risk level:** LOW.
- **Recommendation:** KEEP both — genuinely distinct (report vs. state machine), not a merge candidate.

### Business Blueprint Chain (Autonomous Business Builder + Business Dossier + Production Blueprint)
- **Files:** `autonomous_business_builder.py`, `business_dossier.py`, `production_blueprint.py`
- **Purpose:** A deliberate 3-layer reuse chain, each layer's own docstring confirms it: `business_dossier.py` (8 real deterministic sections, zero LLM) is the base; `production_blueprint.py` reuses it + `value_engine` + `growth_engine` + `ai_capability.orchestrator` ("near-zero new computation," its own words); `autonomous_business_builder.py` reshapes both into a 12-section/8-estimate directive-shaped output, adding exactly 3 new citations (competitor map, risk assessment, execution roadmap).
- **Current maturity:** REAL — a textbook example of disclosed, intentional reuse rather than 3 competing implementations.
- **Business value:** every real ACCEPTED opportunity gets one, not three, blueprint.
- **Technical debt:** none — this is the cluster's best-factored subsystem, explicitly self-audited before being built (2026-07-29 research audit, cited in its own docstring and ADR-141).
- **Risk level:** LOW.
- **Recommendation:** KEEP all three — this is NOT the duplication it superficially resembles; each layer earns its existence with a named, narrow addition.

### Autonomous Operations Status
- **Files:** `autonomous_operations_status.py`
- **Purpose:** Real citation-only status map of ~21 named "autonomous enterprise" activities, tagged automatic/automatic_new/human_gated_by_design/ambiguous_not_touched.
- **Current maturity:** REAL, small (10KB, 3 functions) — deliberately thin.
- **Business value:** the one place that answers "is this factory actually autonomous right now, and precisely what does that mean" without re-litigating the question.
- **Technical debt:** none found.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Founder Console
- **Files:** `founder_console.py`
- **Purpose:** Pure filter-and-merge of already-real "needs founder action now" signals (channel approval gates, DEFERRED decisions, evolution-queue approvals, active publish emergency stops) — zero new judgment, 1 function.
- **Dependencies:** confirmed live via real callers: `global_opportunity_exchange.py`, `strategic_intelligence_core.py`, `mission_control_api.py`, `server.js`.
- **Current maturity:** REAL, smallest file in cluster (3KB) — intentionally so, per its own docstring.
- **Business value:** the founder's real single "what needs me right now" queue.
- **Technical debt:** none.
- **Risk level:** LOW.
- **Recommendation:** KEEP — confirmed genuinely distinct from `ceo_decision_center.py` below (an approval queue vs. a Q&A dashboard), not a merge candidate despite thematic adjacency.

### CEO Decision Center
- **Files:** `ceo_decision_center.py`
- **Purpose:** Answers 10 named "CEO questions" (most profitable opportunity, what to abandon, etc.) by citing existing modules — explicitly "not a new scoring system," per its own docstring, following the same discipline as `master_loop.py`.
- **Dependencies:** confirmed live via real callers: `capital_allocation_engine.py`, `galaxy_council.py`, `mission_control_api.py`, `server.js`.
- **Current maturity:** REAL, small (13KB, 4 functions).
- **Business value:** the founder's real 10-question strategic dashboard.
- **Technical debt:** none found.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Department Health + Department Events
- **Files:** `department_health.py`, `department_events.py`
- **Purpose:** Genuinely distinct despite the shared "department" prefix — `department_health.py` is a per-department STATE snapshot (health signals, honestly `"data_source": "none"` for unbuilt departments like Researchers/Customer Intelligence); `department_events.py` is an append-only EVENT LOG/correlation-index across 12 named department slots, IDs-and-summary-only (never duplicates business data).
- **Current maturity:** REAL, both small.
- **Business value:** one is "how healthy is X right now," the other is "what happened in X, traceable back to the real record."
- **Technical debt:** none found.
- **Risk level:** LOW.
- **Recommendation:** KEEP both — a state/log split is a legitimate pattern, not duplication.

### Master Loop
- **Files:** `master_loop.py`
- **Purpose:** A near-zero-new-logic map of 20 named lifecycle stages onto real existing modules, "audit-first" — deliberately never auto-wired into `factory_loop.js`'s tick (an always-on-daemon proposal declined 3× — ADR-107/110/115).
- **Dependencies:** verified real, live callers via `mission_control_api.py` → `trace_lifecycle()`/`mission_control_heartbeat()`, wired into `server.js`'s SERVICE_REGISTRY (`get-lifecycle-trace`, `get-mission-control-heartbeat`). **Not dead** — but only 2 of its functions are the actual live API surface; the rest of its 13.6KB is documentation-as-code (the stage-to-module map itself).
- **Current maturity:** REAL but narrow-in-active-use relative to its size.
- **Business value:** real, but concentrated in 2 functions.
- **Technical debt:** **Finding 4** — imports `mission_control_api` directly (see Cross-cutting Finding 1b), which `infrastructure_bridge.py`'s own docstring states is architecturally wrong ("a thin CLI dispatcher, not meant to be imported as a library by other modules").
- **Risk level:** LOW functionally, but the import violates a documented internal rule.
- **Recommendation:** REFACTOR — not remove (it's real and live), but its 2 live functions (`trace_lifecycle`, `mission_control_heartbeat`) could be extracted so the bulk of the file (the stage-map documentation) doesn't need to import `mission_control_api` at all, resolving the cycle in Finding 1b.

### Factory Orchestrator
- **Files:** `factory_orchestrator.py`
- **Purpose:** A single-call, on-demand composite: decision lookup → Executive Quality Gate → AI Executive Board → Revenue Pipeline production, `advisory_only=True` by default. Distinct from `orchestrator/orchestrator.py` below (the real, live, wired production-cycle engine) — this one is a convenience wrapper for what used to take 3+ manual Mission Control calls.
- **Current maturity:** REAL, small (4 functions).
- **Business value:** saves real manual steps for one specific real workflow.
- **Technical debt:** **Finding 1a** — is one leg of a real 3-module import cycle (see below).
- **Risk level:** MEDIUM — the cycle is real, not hypothetical.
- **Recommendation:** REFACTOR — break the cycle (see Finding 1a for the specific fix).

### Orchestrator Package (`orchestrator/`)
- **Files:** `orchestrator/orchestrator.py`, `registry.py`, `retry.py`, `timeline.py`, `types.py`
- **Purpose:** The REAL, live, wired production-cycle coordinator (ADR-051) — `run_cycle()` drives one opportunity through `EXECUTION_ORDER` via dependency inversion (never imports a concrete engine directly, only the registry's abstract callable). Explicitly authorized for real automatic wiring into `factory_loop.js`'s tick (2026-07-19), unlike `master_loop.py`.
- **Dependencies:** `orchestrator/registry.py` auto-imports `orchestrator/engines/*` via `pkgutil` at import time — confirmed this is WHY those 5 engine files show as "zero dependents" in the real dependency graph (intentional decoupling, not dead code — see Finding 5).
- **Current maturity:** REAL/production, the actual live execution engine.
- **Business value:** the real production-cycle driver.
- **Technical debt:** none found in this package itself.
- **Risk level:** LOW.
- **Recommendation:** KEEP. **Naming risk** — 4 modules in this cluster alone contain "orchestrat*" or execute an orchestration-shaped role (`orchestrator/orchestrator.py`, `factory_orchestrator.py`, `master_loop.py`, `ceo_decision_center.py`) with genuinely different scopes; see Finding 3.

### Dependency Graph
- **Files:** `dependency_graph.py`
- **Purpose:** A REAL, AST-based (not hand-drawn) import graph of every internal `.py` file — exactly the tool used to produce Findings 1 and 5 in this report.
- **Current maturity:** REAL, self-verified by direct use in this review (`build_graph()`, `find_cycles()`, `find_zero_dependent_modules()` all ran successfully, 218 modules, 0 parse errors).
- **Technical debt:** **Finding 6** — its own `find_zero_dependent_modules()` has a verified false positive: `evidence_completeness.py` is reported as zero-dependent but is actually imported by 6 real files (`autonomous_operations_status.py`, `decision_engine/engine.py`, `decision_engine/types.py`, `evidence_network.py`, `mission_control_api.py`, plus 2 tests). Root cause not fully diagnosed in this review (likely an import-resolution edge case, e.g. a `from X import Y` form the resolver doesn't attribute correctly) — worth a dedicated follow-up, since it means the "28 zero-dependent modules" list cannot be trusted as a dead-code detector without independent verification per module.
- **Risk level:** LOW for the tool itself; MEDIUM for anyone trusting its zero-dependent output unverified.
- **Recommendation:** REFACTOR — fix the `evidence_completeness.py`-class false positive before this tool is used as an authoritative dead-code signal in future reviews.

### Reality Scorecard + Reality Mode
- **Files:** `reality.py`, `reality_mode.py`
- **Purpose:** `reality.py` — "4 numbers the factory cannot fake," standalone, zero internal imports, reads `config/reality.json` + `finance_data.json` directly. `reality_mode.py` — formalizes a shared 4-level evidence taxonomy (VERIFIED_REALITY/ESTIMATED/SIMULATED/+1 more) used informally across the whole factory.
- **Dependencies:** `reality.py` real caller: `executive_score.py`. `reality_mode.py` real caller: `server.js`'s `get-company-reality-score`.
- **Current maturity:** REAL, both live.
- **Business value:** the factory's own explicit "don't let a green dashboard mean a green business" check.
- **Technical debt:** none found.
- **Risk level:** LOW.
- **Recommendation:** KEEP both — genuinely distinct (a scorecard vs. a shared vocabulary module), resolves the naming-collision concern raised at review start.

### Enterprise Readiness
- **Files:** `enterprise_readiness.py`
- **Purpose:** Prospective-only gate (applies to new products going forward, not retroactive to the 5 already-shipped products) reusing `executive_quality_gate.py` as its scoring backbone.
- **Current maturity:** REAL, 2nd-largest file in cluster (31KB, 26 functions).
- **Business value:** the real enterprise-readiness check for anything new.
- **Technical debt:** none found; explicitly discloses its own proxy-check limitation (no real lawyer/security/privacy officer exists).
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Execution Status
- **Files:** `execution_status.py`
- **Purpose:** Per-opportunity status view (phase/owner/completion%/blocking issue/business value/revenue/effort/confidence/priority/expected completion) — pure aggregation.
- **Dependencies:** heavily used — confirmed real callers: `master_loop.py`, `mission_control_api.py`, `production_evidence/record.py`, `reality_mode.py`, `revenue_pipeline/pipeline.py`, `server.js`, 3 test files.
- **Current maturity:** REAL, load-bearing.
- **Business value:** real, high — this is the most cross-referenced module found in this cluster's caller-grep.
- **Technical debt:** none found; honestly reports "expected completion" as Unknown (no historical per-stage duration tracking exists).
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Trust & Resilience Aggregation (Resilience Monitor + Safe Mode + Health Trend)
- **Files:** `resilience_monitor.py`, `safe_mode.py`, `health_trend.py`
- **Purpose:** `resilience_monitor.py` is the real Monitor+Classify aggregator over signals that already existed scattered across independent modules, with a shared 4-tier severity vocabulary that didn't exist before it. `safe_mode.py` generalizes the existing per-arm circuit-breaker pattern to 3 named subsystems. `health_trend.py` is the Python-side reimplementation of `lib/health_trend.js`'s real health-snapshot recording (explicitly "kept in lockstep with the JS original, never a second divergent algorithm").
- **Current maturity:** REAL, `resilience_monitor.py` is 3rd-largest in cluster (18KB, 17 functions).
- **Business value:** the real early-warning system, explicitly designed never to auto-execute any irreversible action itself.
- **Technical debt:** `health_trend.py` is a deliberate dual-language reimplementation (same precedent as `executive_score.py`'s `_dual_inspection_pass_rate()`) — a real, disclosed maintenance cost (2 codebases to keep in sync) accepted for a specific reason (Python callers need it without a Node runtime).
- **Risk level:** LOW.
- **Recommendation:** KEEP all three.

### AI Doctor
- **Files:** `ai_doctor.py`
- **Purpose:** The real, non-fabricated replacement for the confirmed-fake `quality_doctor.py` (already removed from the repo per CLAUDE.md). Combines `evolution_engine.py`'s report + `lib/infrastructure_intelligence.js`'s status, plus one new dependency-risk check.
- **Current maturity:** REAL.
- **Business value:** real engineering-health reporting.
- **Technical debt:** none found.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Factory State
- **Files:** `factory_state.py`
- **Purpose:** The single authoritative "what's happening right now" view (`data/factory_state.json`), same atomic tmp-then-rename write pattern as `server.js`'s `saveFin()`.
- **Current maturity:** REAL, Phase A scope only (read/write plumbing) — its own docstring says Phase B/C (acting on `recovery_info`/`pending_retries`) is not yet built. Honest, disclosed gap.
- **Business value:** real crash-safety for state.
- **Technical debt:** intentionally incomplete (Phase B/C deferred) — not a defect, a disclosed roadmap gap.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Integration Registry
- **Files:** `integration_registry.py`
- **Purpose:** Vendor extension-point catalog, with an explicit anti-duplication rule against `ai_capability/registry.py` (a vendor already in that catalog is referenced, never re-derived) — the docstring cites a real self-caught duplicate (MiniMax) that was fixed.
- **Current maturity:** REAL, small (4 functions).
- **Business value:** honest vendor-readiness tracking.
- **Technical debt:** none found — the self-correction it documents is evidence of a working anti-duplication discipline, not a debt.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Infrastructure Bridge
- **Files:** `infrastructure_bridge.py`
- **Purpose:** The one Python→JS bridge in the whole codebase (every other cross-language call goes JS→Python) — reuses `lib/infrastructure_intelligence.js` rather than reimplementing CPU/memory/disk logic a second time. Fails honestly (returns `None`) on any error.
- **Current maturity:** REAL, tiny (2 functions).
- **Business value:** avoids a real duplicate implementation.
- **Technical debt:** none — and its own docstring is the source of the architectural rule Finding 4 shows `master_loop.py` violating.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Path Safety
- **Files:** `path_safety.py`
- **Purpose:** Shared safe-output-path confinement, extracted after finding `book_generator.py` and `cover_designer_v2.py` (outside this cluster) had independently reimplemented the same filename-sanitization logic — a real, disclosed fix-drift risk that was closed.
- **Current maturity:** REAL, tiny (2 functions), security-relevant.
- **Business value:** prevents real path-traversal risk (Constitution §4).
- **Technical debt:** none — this module is itself the fix for a technical-debt finding from an earlier audit.
- **Risk level:** LOW now (was MEDIUM before unification — worth noting the pattern: check other clusters for the same "small utility reimplemented independently in 2+ places" shape).
- **Recommendation:** KEEP.

### Research Department
- **Files:** `research_department.py`
- **Purpose:** Pure assembly of already-real analysis under 7 named categories — explicitly does NOT trigger new live/network calls (avoids accidental live-call side effects from a read path).
- **Current maturity:** REAL, small.
- **Business value:** real, safe-by-design read-only research summary.
- **Technical debt:** none found.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Global Opportunity Exchange
- **Files:** `global_opportunity_exchange.py`
- **Purpose:** Marketplace-as-asset portfolio view — explicitly the most DISCOVERY-heavy module in this cluster by design (only 4/15 named marketplaces have a real channel arm, 0 real sale events exist), honestly disclosed rather than backfilled.
- **Current maturity:** Mixed REAL/DISCOVERY, explicitly and correctly labeled as such.
- **Business value:** real framework, will become valuable as real marketplace data accumulates.
- **Technical debt:** none found — DISCOVERY-heaviness here is honesty, not debt.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Validation Layer (`validation_layer/`)
- **Files:** `daily_report.py`, `durations.py`, `lifecycle.py`, `reliability.py`, `stalled.py`
- **Purpose:** A REPORTING layer built entirely on top of `executive_intelligence/bottlenecks.py`/`engine_health.py` (explicitly "reused verbatim") and `orchestrator/timeline.py` — NOT a competing implementation. `durations.py` is the one genuinely new statistic in the package; everything else re-presents existing signals in a different shape (a Daily Validation Report, ADR-053).
- **Current maturity:** REAL, standalone deliberately-run tools (not tick-wired).
- **Business value:** the specific breakdown format ADR-053 asked for.
- **Technical debt:** none found — resolves the naming-collision concern about overlap with `executive_intelligence/bottlenecks.py` raised at review start: this is legitimate layering, not duplication.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Recovery (`recovery/`)
- **Files:** `snapshot.py`, `startup_check.py`
- **Purpose:** `snapshot.py` generalizes an existing ad-hoc quarantine-then-recover pattern (from `server.js`'s `loadFin()`) into a reusable helper for a small, named set of critical files — explicitly NOT a full-repo backup (defers to git for that). `startup_check.py` is the real "was the last shutdown unclean, is auto-resume safe" decision point, reusing `factory_loop.js`'s lock-staleness evidence and `orchestrator/timeline.py`'s success record rather than re-deriving either.
- **Current maturity:** REAL.
- **Business value:** real crash-recovery safety — directly relevant to the "unexpected shutdown" recovery audit performed earlier this session.
- **Technical debt:** none found.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Dossier Bundle
- **Files:** `dossier_bundle/build_bundle.py`
- **Purpose:** Mandatory per-product artifact bundling (docs/metadata/marketing/support/update-history), reusing `production_factory/dossier.py` + `book_generator.py`'s `groq_chat()` — no generation logic duplicated, only assembled.
- **Current maturity:** REAL.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Commercial Execution (`commercial_execution/`)
- **Files:** `approval_gates.py`, `pipeline.py`
- **Purpose:** `approval_gates.py` — real, current-state-driven "what needs founder action before this can publish," computed from every arm's live `status()` (never a hardcoded narrative) — the same source `distributor.py` (outside this cluster) already reads. `pipeline.py` — the unified Publish→Verify→Revenue-Registration→Audit-Trail call.
- **Current maturity:** REAL.
- **Business value:** real publish-readiness and audit trail.
- **Technical debt:** none found.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

---

## Cross-cutting findings

### 1. Duplicate responsibilities / architectural bottleneck — TWO REAL CIRCULAR IMPORT CHAINS (verified via `dependency_graph.py`)

**1a. `executive_board → value_engine → factory_orchestrator → executive_board`** (a real 3-node cycle, confirmed via `dependency_graph.build_graph()`'s actual edge list, not inferred):
```
executive_board.py   imports value_engine
value_engine.py       imports factory_orchestrator
factory_orchestrator.py imports executive_board
```
This is a genuine circular import. It happens to work today (Python tolerates it if nothing is used at true import time in a way that deadlocks), but it means these 3 modules cannot be reasoned about, tested, or refactored independently — a change to any one risks a real import-order bug in the other two. There is also a related, larger cycle found in the graph: `revenue_pipeline.pipeline → decision_reopen → executive_board → value_engine → factory_orchestrator → revenue_pipeline.pipeline` (5 nodes, 2 outside this cluster) and `decision_reopen → executive_board → value_engine → opportunity_pipeline → decision_reopen` (4 nodes) — `executive_board`/`value_engine` are the common thread in all of these, suggesting `value_engine.py`'s import of `factory_orchestrator.py` is the actual root cause worth investigating first (it's the one edge that closes the loop back toward modules that already depend on `executive_board`/`value_engine`).

**1b. `master_loop ↔ mission_control_api`** (a real 2-node cycle): `master_loop.py` imports `mission_control_api`, and `mission_control_api.py` imports `master_loop` (to call its 2 live functions). This directly contradicts `infrastructure_bridge.py`'s own documented architectural rule that `mission_control_api.py` is "a thin CLI dispatcher, not meant to be imported as a library by other modules." Every other module in this cluster correctly avoids importing `mission_control_api`; `master_loop.py` is the one exception.

### 2. Overlapping logic — redundant signal (re)computation, not redundant results
`evolution_engine.py`'s report and `tool_intelligence/proposals.py`'s dynamic proposal generators (outside this cluster, but consumed here) both independently call `executive_intelligence.bottlenecks.detect_bottlenecks()` and `strategic_intelligence.technical_debt`. Same real signals, computed twice per real cycle by two separate assemblers that must be kept in sync by hand. Not wrong, just wasteful and a future drift risk.

### 3. Maintainability risk — governance/orchestration naming density
This cluster's 35 files reduce to roughly **26-28 genuinely distinct subsystems** by function (per the per-subsystem grouping above) — a real but modest (not alarming) file-to-concern ratio. The sharper risk is naming, not count: **3 separate governance rosters** exist on purpose (Constitution's 12 Councils, Executive Board's 10 roles, Galaxy Council's 10 members — confirmed intentionally not merged, ADR-138) and **4 separate "orchestration"-shaped modules** exist with genuinely different scopes (`orchestrator/orchestrator.py` = the real wired engine; `factory_orchestrator.py` = an on-demand advisory composite; `master_loop.py` = a passive lifecycle-stage citation map; `ceo_decision_center.py` = a Q&A dashboard). Every individual pair is justified in isolation (verified above), but a new engineer (or a future Claude Code session without this review's context) would have to redo this exact 30-minute investigation to tell them apart. This is a real documentation/discoverability debt, not a code debt.

### 4. Architectural-rule violation
`master_loop.py` importing `mission_control_api.py` violates `infrastructure_bridge.py`'s documented rule (see Finding 1b) — the one confirmed instance of this rule being broken in this cluster.

### 5. Dead code / obsolete modules — mostly a non-finding, with one meta-caveat
No genuinely dead code was found in this cluster. Every file investigated (including the ones most likely to be vestigial by name — `master_loop.py`, `reality.py`, `execution_status.py`) has verified real, live callers via whole-repo grep. The real dependency graph's own `find_zero_dependent_modules()` flagged `orchestrator/engines/*` (5 files) as zero-dependent, but this is **confirmed intentional** (dependency-inversion via `pkgutil` auto-registration, per `orchestrator/registry.py`'s own docstring) — not dead code. Same confirmed pattern for `market_intelligence_core/scoring/*` and `multi_source_intelligence/connectors/*` (outside this cluster, verified via the same registry mechanism).

### 6. Tooling risk (meta-finding)
`dependency_graph.py`'s `find_zero_dependent_modules()` has a **verified false positive**: `evidence_completeness.py` is reported as having zero dependents but is actually imported by 6 real files. This means its zero-dependent output should not be trusted as an authoritative dead-code list for other clusters without independent caller-grep verification — flagging this for whoever synthesizes the full report, since other clusters' forks may be using the same tool.

### 7. Security risks
No hardcoded secrets, no `eval`/`exec`/`shell=True`/`os.system` calls found anywhere in this cluster (explicit grep, zero matches). `path_safety.py` is a positive security finding — a real path-traversal fix that closed a genuine fix-drift risk between 2 modules (outside this cluster) that had each reimplemented the same sanitization independently. Worth checking other clusters for the same "small security-relevant utility reimplemented in 2+ places" shape.

### 8. Scalability risks
None found specific to this cluster beyond the general note that `executive_quality_gate.py` and `galaxy_council.py`/`executive_board.py` are synchronous, single-process, file-based-state functions — fine at this factory's current real volume (a handful of ACCEPTED opportunities), but every one of these would need real load-testing before this factory operates at 100x its current opportunity volume. Not an active risk today.

### 9. Unnecessary complexity / simplification opportunities
- Break cycle 1a by having `value_engine.py` NOT import `factory_orchestrator.py` directly — likely only needs one or two specific fields/functions that could be passed as parameters or looked up via a narrower interface.
- Extract `master_loop.py`'s 2 live functions (`trace_lifecycle`, `mission_control_heartbeat`) so the bulk of the file doesn't need to import `mission_control_api` at all, resolving cycle 1b.
- No MERGE or REMOVE candidates found in this cluster — every file earns its place. This cluster's technical debt is entirely in **coupling direction** (2 real cycles) and **discoverability** (naming density), not in redundant/dead/obsolete code.
