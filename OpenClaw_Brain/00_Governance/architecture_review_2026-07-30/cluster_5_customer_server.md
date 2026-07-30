# Architecture Review — Cluster 5: Customer Platform, Server & Orchestration Surface

**Scope:** customer_pipeline.py, contract_generator.py, invoice_generator.py, build_in_public.py, mission_control_api.py, server.js, factory_loop.js, knowledge_brain.js, mission_control_sw.js, self_awareness.js, lib/ (14 files), knowledge_graph/build.py, scripts/ (19 files).

**Summary:** This cluster contains the repo's two largest single files by far — `server.js` (288KB, 126 `SERVICE_REGISTRY` entries + 69 `ACTION_REGISTRY` entries = ~195 real registered HTTP endpoints) and `mission_control_api.py` (102KB, the CLI dispatch hub nearly every Python subsystem is reached through). Both are the real, central hub of the whole repo's dependency graph — almost every other cluster's modules are ultimately reached FROM one of these two files. The security posture here is genuinely strong: every `child_process.spawn()` call (14 found) uses the safe array-argument form with JSON-stringified payloads, never shell string interpolation; the one `execSync()` template-string call is confirmed to only ever receive one of 3 hardcoded literal interpreter names, never external input. The `lib/*.js` extraction pattern is a real, already-self-corrected architecture discipline (see Cross-cutting §1 — a documented past duplicate-code incident with a permanent regression guard now in place). The real risk in this cluster is concentration, not correctness: two files this large are a genuine single-point-of-maintainability-risk regardless of how well-organized their internals are.

---

### HTTP Service Layer (server.js)
- **Files:** server.js
- **Purpose:** The entire real HTTP surface — Mission Control auth, ~195 registered service/action endpoints, direct routes (`/generate-book`, `/finance/*`, `/chat`, `/health`, customer-platform routes), static file serving, Python subprocess orchestration.
- **Inputs:** HTTP requests (browser Mission Control UI, customer_site/, internal automation via `X-Internal-Token`).
- **Outputs:** JSON API responses; spawns Python subprocesses for every non-trivial computation.
- **Dependencies:** Nearly every other cluster's modules are reached FROM here (directly via `spawn()` into Python, or via `require()` for `lib/*.js`). Confirmed 14 real `spawn()` call sites, all using the safe `spawn(cmd, [args])` array form — zero shell-string-concatenation injection risk found.
- **Current maturity:** REAL/production — this is the actual live server.
- **Business value:** The literal runtime this entire factory operates through.
- **Technical debt:** Sheer size (288KB, ~195 endpoints in one file) — no internal duplication found via the registry-pattern grep, but a single file this large is itself a maintainability cost independent of code quality (navigation, merge-conflict surface, cognitive load for any single change).
- **Risk level:** MEDIUM (maintainability/bottleneck, not security or correctness) — confirmed via evidence: `/chat` (line 3092) is still `requireMissionControlAuth`-gated and still has zero real callers per CLAUDE.md's own disclosure (unchanged since last audit); `DELETE /finance/delete/:id` (line 3283) is still auth-gated with no UI button (unchanged, half-finished CRUD pair as previously documented — confirmed still true, not a new finding).
- **Recommendation:** REFACTOR (long-term, not urgent) — split `SERVICE_REGISTRY`/`ACTION_REGISTRY` entries into per-domain files (e.g. `registries/evolution.js`, `registries/customer.js`) imported and concatenated at startup, preserving the exact same runtime behavior while reducing single-file size. No bug evidence justifies urgency; this is a pure maintainability investment.

### CLI Dispatch Hub (mission_control_api.py)
- **Files:** mission_control_api.py
- **Purpose:** The real Python-side CLI dispatch layer server.js's `spawn()` calls invoke by name (`python mission_control_api.py <command> <json_payload>`) — a `COMMANDS` dict mapping ~120+ command names to thin `_handler()` functions, each importing and calling exactly one real subsystem module.
- **Inputs:** `sys.argv[1]` (command name), `sys.argv[2]` (JSON payload).
- **Outputs:** JSON to stdout.
- **Dependencies:** Imports nearly every Python subsystem across all 4 other clusters (confirmed pattern: every `_handler()` function does a local `import <module>` inside itself, not at module top-level — deliberate lazy-import discipline that keeps startup cheap and avoids one subsystem's import error from breaking every other command).
- **Current maturity:** REAL/production.
- **Business value:** The single real bridge between the JS runtime and every Python subsystem.
- **Technical debt:** Same size concern as server.js (102KB) — each individual `_handler()` function is small and clean (confirmed spot-checking evolution_queue/autonomous_operations_status handlers this session), so the size is breadth (many thin handlers), not depth (no single function is bloated).
- **Risk level:** LOW-MEDIUM — the lazy per-function import pattern is a genuine defensive strength (one broken subsystem import can't take down the whole dispatch table), but the file's sheer breadth means it's touched by nearly every feature round, giving it a high change-frequency/merge-conflict profile.
- **Recommendation:** KEEP the lazy-import pattern (it's correct and defensive). REFACTOR (same long-term, non-urgent note as server.js) — the `COMMANDS` dict itself could be split into per-domain registration files that self-register into one shared dict at import time (same Open/Closed registry pattern already proven throughout `channels/registry.py` and friends), without changing any handler's behavior.

### No-Scheduler Tick Engine (factory_loop.js)
- **Files:** factory_loop.js
- **Purpose:** The only scheduler-equivalent in this repo — confirmed via grep: no cron, no `package.json` script entry (package.json has zero `"scripts"` section at all), only runs when manually invoked (`node factory_loop.js`).
- **Inputs:** None (self-contained tick loop once started).
- **Outputs:** Real production/publish/report side effects per tick (~10 min interval once running).
- **Dependencies:** `require('./scripts/factory_startup_check')` (real, direct import — confirmed line 39); spawns `mission_control_api.py` for every daily-gated report/measurement function (evolution_queue_intake, evolution_outcome_measurement, knowledge_graph_snapshot, business_blueprint_generation, executive_brief, ai_doctor, department_health — 7+ daily-gated functions confirmed via grep of `maybeGenerate*`/`maybeMeasure*` naming).
- **Current maturity:** REAL, and honestly self-documented as manually-triggered-only (matches CLAUDE.md's own "No scheduler exists" section verbatim).
- **Business value:** The real automation heartbeat for every "automatic" activity this factory has (per ADR-142's own `autonomous_operations_status.py` classification).
- **Technical debt:** 137KB single file — same size-concentration pattern as server.js/mission_control_api.py, though smaller.
- **Risk level:** LOW — no correctness issues found; the "must be started manually, no OS-level keepalive" property is a known, explicit, previously-declined tradeoff (master_loop.py's always-on-daemon proposal, declined 3x per ADR-107/110/115), not an oversight.
- **Recommendation:** KEEP as-is. `scripts/supervisor.js` (documented in CLAUDE.md's "Running the project" section) is the already-real answer for auto-restart-on-crash without resurrecting the declined always-on daemon — correctly scoped, no further action needed.

### Customer Platform Pipeline
- **Files:** customer_pipeline.py, contract_generator.py, invoice_generator.py
- **Purpose:** Real customer-facing Qualification → Evaluation → Price → Proposal → Approval → Payment → Fulfillment pipeline, explicitly reusing the SAME `decision_engine.evaluate_and_decide()`/`profit_oracle.opportunity_score()` engines every internal opportunity uses (confirmed in docstring, matches this session's own memory of ADR-129/130 work). `contract_generator.py`/`invoice_generator.py` are both deterministic, template-only — zero LLM-generated legal/financial text, explicit "Draft — ..." honest-placeholder convention for undecided terms.
- **Inputs:** `data/customer_requests.jsonl`, real Paddle transaction confirmations.
- **Outputs:** Contracts, invoices, pipeline stage transitions.
- **Dependencies:** invoice_generator.py explicitly never independently computes a price — only reads the already-locked contract price + confirmed Paddle transaction id (verified via docstring: "never a second, independently-computed price").
- **Current maturity:** REAL, extensively verified in prior sessions per this conversation's own memory (Customer Platform Rounds 1-6, ADR-129/130/131).
- **Business value:** The real revenue-realization path for external (non-founder-discovered) customers.
- **Technical debt:** None found beyond the already-disclosed, still-real Paddle onboarding gate (external platform blocker, not code).
- **Risk level:** LOW — no fabrication path found in either generator (confirmed by design: both are template-only, never call an LLM).
- **Recommendation:** KEEP.

### Marketing / Build-in-Public
- **Files:** build_in_public.py
- **Purpose:** Weekly progress report + public-facing content, explicitly closing a "Marketing readiness: NOT READY" finding via pure aggregation over already-real decision/blueprint/finance data (zero AI cost, zero fabrication, explicit "0" when nothing happened).
- **Dependencies:** Reuses decision_engine/production_blueprint/finance data — no new data source.
- **Current maturity:** REAL.
- **Business value:** Marketing-readiness gap closure per founder's own 2026-07-24 decision.
- **Technical debt:** None found.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### Knowledge Graph
- **Files:** knowledge_graph/build.py
- **Purpose:** Living company-memory graph (Niche/Decision/MarketAnalysis/ProductionRun/PublishChannel/AIProvider/CommercialEvent/Proposal/Outcome nodes) built mechanically from 6+ real existing data sources — explicitly NOT a graph database (plain Python/JSON, same "no new dependency" discipline as knowledge_brain.js's own choice against embeddings).
- **Dependencies:** Reads data/decisions.jsonl, market_intelligence_analyses.jsonl, sales_ledger.jsonl, ai_cost_log.jsonl, market_evidence.jsonl, evolution_queue_state.json. Called by factory_loop.js's `maybeGenerateDailyKnowledgeGraph()` (confirmed this session's own prior work, ADR-142).
- **Current maturity:** REAL, mechanical (non-semantic) parse — confirmed live-run this session (2938 nodes/2759 edges per prior session memory).
- **Business value:** Real institutional memory / audit trail across every major recorded event type.
- **Technical debt:** None found.
- **Risk level:** LOW.
- **Recommendation:** KEEP.

### lib/*.js Shared Primitives (14 files)
- **Files:** customer_auth.js, dashboard_data.js, department_events.js, factory_state.js, health_checks.js, health_trend.js, infrastructure_intelligence.js, jsonl.js, metrics.js, n8n_notify.js, next_sale_id.js, publisher_seo.js, recovery_log.js, telegram_direct.js
- **Purpose:** Extracted, framework-free (no Express/child_process dependency), independently-unit-testable primitives — a consistent, deliberate extraction pattern across the whole set (every file's docstring cites the same "extracted from server.js so it's testable in isolation" rationale).
- **Inputs/Outputs:** Varies per file — all pure file/os reads or narrowly-scoped computation, no live server dependency.
- **Dependencies:** `recovery_log.js` imports `jsonl.js` + `department_events.js` (clean, intentional composition, not duplication).
- **Current maturity:** REAL, and notably **self-correcting** — see Cross-cutting §1 (jsonl.js) and §2 (next_sale_id.js) for two confirmed real past-bug/past-duplication fixes documented in these files' own docstrings.
- **Business value:** Direct testability + defensive isolation (a broken health-check computation can't take down the live server process, since it's provably decoupled from Express).
- **Technical debt:** None found — this cluster is a model example of "extract for testability" done consistently, not ad-hoc.
- **Risk level:** LOW.
- **Recommendation:** KEEP — this pattern is worth citing as the template other clusters' size-concentration findings (server.js, mission_control_api.py, profit_oracle.py per Cluster 3) should eventually be refactored toward.

### Ops Scripts (scripts/, 19 files)
- **Files:** check_jsonl_duplication.js, check_orphan_processes.js, check_paddle_checkout_status.py, deploy_production.js, factory_startup_check.js, generate_release_notes.js, harden_file_acls.js, health_monitor.js, ops_daily_checks.js, ops_maintenance.js, perf_measure.js, poll_sales.py, process_approved_drafts.py, readiness_certificate.py, restore_file_from_git.js, rollback_simulate.js, staging_simulate.js, supervisor.js, weekly_public_report.py
- **Purpose:** Manual/ops CLI tooling — deploy, health-monitor, readiness-certify, disaster-recovery simulation, structural-duplication guard, orphan-process check.
- **Dependencies:** Confirmed via grep: `factory_startup_check.js` is the only one directly `require()`'d by factory_loop.js; `poll_sales.py` is directly `spawn()`'d by server.js. Every other script has real cross-references (9-17 hits each across docs/other scripts) but **zero npm `package.json` "scripts" entries exist at all** — confirmed by reading package.json directly (dependencies-only, no scripts block) — meaning every one of these is genuinely manual-invocation-only, consistent with the factory's explicit no-scheduler stance, not accidentally orphaned.
- **Current maturity:** REAL tools, manually run.
- **Business value:** Real ops safety net (readiness certification, rollback simulation, ACL hardening) for a solo founder without a dedicated ops team.
- **Technical debt:** None found — the lack of `package.json` scripts wiring is a deliberate, disclosed architectural choice (manual invocation = deliberate side effects, per CLAUDE.md's own "no scheduler" philosophy cited throughout this session), not an oversight.
- **Risk level:** LOW.
- **Recommendation:** KEEP all — real, referenced, intentionally manual. Optional low-priority polish: adding named `npm run <script>` aliases in package.json purely for discoverability (never auto-invoked) would reduce onboarding friction without changing any automation posture.

---

## Cross-cutting findings

1. **Duplicate responsibilities — CONFIRMED, but already found and fixed.** `lib/jsonl.js`'s own docstring documents a real, now-resolved incident: the same 5-line "read JSONL, skip corrupt lines" pattern was independently reimplemented in 8+ places (factory_loop.js, self_awareness.js, lib/recovery_log.js, lib/dashboard_data.js's own internal helper) before this module existed. `scripts/check_jsonl_duplication.js` (confirmed real, referenced in 10 other files) is a permanent, already-built regression guard against this exact class of duplication recurring — this is a genuine example of this codebase's self-review discipline working as designed, and directly relevant evidence for the founder's own recovery-audit confidence.

2. **Overlapping logic — CONFIRMED, already found and fixed.** `lib/next_sale_id.js`'s own docstring documents a real past bug: `Date.now()`-based sale IDs collided within the same millisecond, causing `DELETE /finance/delete/:id` to silently delete two records at once. Fixed by extraction into a dedicated, unit-testable collision-safe ID generator. Cited as resolved evidence, not an open finding.

3. **Dead code:** None found in this cluster beyond the two already-disclosed, still-accurate items (`/chat` zero-caller endpoint, `DELETE /finance/delete/:id` no-UI-button) — both reconfirmed still true via direct grep this session, not new findings.

4. **Obsolete modules:** None found.

5. **Architectural bottlenecks — the headline finding for this cluster.** `server.js` (288KB, ~195 registered endpoints) and `mission_control_api.py` (102KB, ~120+ dispatch commands) are both genuine single-file concentration risks. Neither shows internal code-quality problems (no duplication found, consistent registry patterns, defensive lazy imports) — the risk is purely operational: every new feature round in this factory's history has touched both files (confirmed by this session's own ADR-143 work, which added entries to both), making them the highest merge-conflict-probability, highest-cognitive-load files in the repo by a wide margin over anything in the other 4 clusters.

6. **Scalability risks:** None found specific to this cluster's own code — server.js's Express routing and mission_control_api.py's dispatch table both scale linearly and cheaply with endpoint count; the real scalability question (decisions.jsonl linear scans) lives in Cluster 3, not here.

7. **Maintainability risks:** The server.js/mission_control_api.py size-concentration (§5) is the clear #1 risk in this cluster. Secondary: factory_loop.js at 137KB is smaller but shares the same "every round touches this file" growth pattern.

8. **Security risks — audited directly, none found.** All 14 `child_process.spawn()` calls in server.js use the safe array-argument form (`spawn(cmd, [arg1, arg2, ...])`), never a shell string — confirmed zero instances of unsanitized-input string concatenation into a shell command. The single `execSync()` template-string call (line 5179, Python-interpreter auto-detection) is confirmed to only ever receive one of 3 hardcoded literal strings (`'python3'`, `'python'`, `'py'`), never external/user input — no injection surface. Every `lib/*.js` credential-adjacent file (customer_auth.js) documents using a deliberately separate signing secret from Mission Control's own session token, preventing cross-privilege forgery — a positive, verified security design choice, not a gap.

9. **Unnecessary complexity / simplification opportunities:** The single highest-leverage move for this cluster is the same one named in §5/Recommendation for server.js and mission_control_api.py — splitting each into per-domain registry files that self-register into one shared table at startup (the exact `channels/registry.py` pattern already proven correct elsewhere in this repo), preserving identical runtime behavior while reducing per-file size and merge-conflict surface. This is a pure future-maintainability investment with zero bug evidence forcing urgency — appropriate to schedule, not to rush.
