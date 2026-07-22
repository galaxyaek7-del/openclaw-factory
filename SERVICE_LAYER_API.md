# OpenClaw Unified Service Layer — API Reference (v1)

_Auto-generated from SERVICE_REGISTRY in server.js at server startup — do not hand-edit, it is overwritten on every restart. Source of truth: server.js._

Generated at: 2026-07-22T01:38:12.833Z

Every endpoint below requires an authenticated Mission Control session (`POST /api/mission-control/login`) and returns the standard envelope:

```json
{ "success": true, "service": "<name>", "version": "v1", "generated_at": "<ISO>", "data": { /* ... */ } }
```

Errors:
```json
{ "success": false, "service": "<name>", "version": "v1", "error": { "code": "...", "message": "..." } }
```

## Services

### company-health

Overall factory health status, derived risk level, self-awareness verdict, and current next-dollar priorities.

- Data: `GET /api/v1/company-health`
- Health: `GET /api/v1/company-health/health`
- Reuses: server.js computeHealthStatus() + self_awareness.js assessSelfAwareness() + lib/dashboard_data.js deriveRiskLevel()/readAttentionFlag()/readActivityTimeline() + server.js readNextDollarActions() — identical composition to the pre-existing GET /api/dashboard.

### market-intelligence

The most recent real market intelligence analysis (scores, risk, customer pain, pricing, AI CEO verdict).

- Data: `GET /api/v1/market-intelligence`
- Health: `GET /api/v1/market-intelligence/health`
- Reuses: lib/dashboard_data.js readLatestMarketIntelligence() — same field this session already confirmed is served by GET /api/dashboard.

### opportunity-queue

Every ranked opportunity plus the ACCEPTED queue ready for production.

- Data: `GET /api/v1/opportunity-queue`
- Health: `GET /api/v1/opportunity-queue/health`
- Reuses: decision_engine/ranking.py rank_all()/rank_queue(), via mission_control_api.py.

### unified-priorities

EOS Phase 2, Round 2 (2026-07-19): three real priority signals shown side by side, never merged into one fabricated composite score -- FACTORY_STATUS.md's Next Dollar Actions, the ranked ACCEPTED opportunity queue, and MASTER_CHARTER.md's Strategic Production Priority Ladder. Closes the real Opportunity Intelligence gap (today spread across the market/goldenhunter/pioneer/opportunities tabs) without inventing a new ranking algorithm.

- Data: `GET /api/v1/unified-priorities`
- Health: `GET /api/v1/unified-priorities/health`
- Reuses: server.js readNextDollarActions() (existing, also used by company-health) + decision_engine/ranking.py rank_queue() via the existing opportunity-queue service + a new MASTER_CHARTER.md markdown-section read using the same technique as readNextDollarActions().

### opportunity-pipeline

The real, ranked Opportunity Pipeline: every currently-scored opportunity annotated with 10 real fields (market size, customer type, pain level, competition, price, recurring revenue, technical complexity, time to MVP, defensibility, scalability) -- real data where it exists, honestly Unknown where it doesn't. Product Laboratory = decisions already ACCEPTED by the real existing gate; everything else stays in the backlog.

- Data: `GET /api/v1/opportunity-pipeline`
- Health: `GET /api/v1/opportunity-pipeline/health`
- Reuses: opportunity_pipeline.py build_opportunity_pipeline() (Opportunity Intelligence Round 2, 2026-07-22) -- reuses decision_engine.ranking.rank_all() verbatim, never recomputes accept/reject.

### product-concept-comparison

Real per-ladder price/score variants for one niche (profit_oracle.ladder_opportunity_score() across all 6 ladder ranks) plus real pre-acceptance ROI per variant -- side by side, never auto-selecting a winner.

- Data: `GET /api/v1/product-concept-comparison`
- Health: `GET /api/v1/product-concept-comparison/health`
- Reuses: revenue_pipeline/plan.py compare_ladder_variants() (Strategic Phase 3, Round 1, 2026-07-22) -- reuses profit_oracle.ladder_opportunity_score()/estimate_pre_acceptance_roi() verbatim.

### decision-history

Every ACCEPTED/REJECTED/DEFERRED decision ever recorded, newest first, summary fields only.

- Data: `GET /api/v1/decision-history`
- Health: `GET /api/v1/decision-history/health`
- Reuses: decision_engine/store.py read_decisions(), via mission_control_api.py.

### production-queue

Production dossiers for every ACCEPTED opportunity (pricing, assets, pre-production verification), plus the current pause/resume state (Phase 9).

- Data: `GET /api/v1/production-queue`
- Health: `GET /api/v1/production-queue/health`
- Reuses: production_factory/factory.py run_production_factory(), via mission_control_api.py, plus server.js readProductionControl() (Phase 9 pause/resume flag).

### publishing-status

Per-platform publishing checklist for every production dossier — a projection of production-queue's own publishing_checklist field, not a new computation.

- Data: `GET /api/v1/publishing-status`
- Health: `GET /api/v1/publishing-status/health`
- Reuses: production_factory/factory.py (via the production-queue service above), projected to just the checklist fields.

### revenue-summary

Revenue pipeline results for every ACCEPTED opportunity plus the rendered CEO revenue report.

- Data: `GET /api/v1/revenue-summary`
- Health: `GET /api/v1/revenue-summary/health`
- Reuses: revenue_pipeline/pipeline.py run_revenue_pipeline()/render_ceo_revenue_report(), via mission_control_api.py.

### automation-status

n8n workflow status from the last real exported definitions (n8n_workflows/*.fixed.json) — honestly labelled as a static export, not live state (n8n REST API still needs a manual login, BLOCKERS.md #1).

- Data: `GET /api/v1/automation-status`
- Health: `GET /api/v1/automation-status/health`
- Reuses: mission_control_api.py's existing n8n_workflows/*.fixed.json reader.

### knowledge-base

OpenClaw_Brain folder map, or full-text search results when called with ?q=.

- Data: `GET /api/v1/knowledge-base`
- Health: `GET /api/v1/knowledge-base/health`
- Reuses: knowledge_brain.js searchBrain()/getBrainMap() — same module already backing the pre-existing GET /brain.

### alerts

NEEDS_ATTENTION.md and NEEDS_REVIEW.md — active flags and their content, if any.

- Data: `GET /api/v1/alerts`
- Health: `GET /api/v1/alerts/health`
- Reuses: lib/dashboard_data.js readAttentionFlag()/readReviewFlag() — same fields already confirmed served by GET /api/dashboard.

### system-configuration

Real, non-secret configuration: unit economics (config/economics.json), tier weights/floor and per-tier automation/long-term-value constants (profit_oracle.py), and the capability maturity registry.

- Data: `GET /api/v1/system-configuration`
- Health: `GET /api/v1/system-configuration/health`
- Reuses: config/economics.json, config/capability_registry.json, profit_oracle.py's TIER_WEIGHTS/MIN_OPPORTUNITY_SCORE/AUTOMATION_POTENTIAL_BY_TIER/LONG_TERM_VALUE_BY_TIER, via mission_control_api.py.

### recovery-status

Unified Recovery System (2026-07-18) dashboard: current in-flight task, recovery state, pending retries, last checkpoint, and the last real recovery action.

- Data: `GET /api/v1/recovery-status`
- Health: `GET /api/v1/recovery-status/health`
- Reuses: factory_state.py load_state() + data/recovery_actions.jsonl, via mission_control_api.py.

### production-families

Universal Production Engine (2026-07-18): which of the 11 UPE product families have a real registered adapter today, under the founder-approved canonical family names, plus each manifest-driven family's real Product Manifest (Roadmap Step 3) — category, generators, pricing, supported marketplaces.

- Data: `GET /api/v1/production-families`
- Health: `GET /api/v1/production-families/health`
- Reuses: product_families.registry + product_families.manifest, via mission_control_api.py — same data-driven discipline as production_factory/dossier.py's _product_type_capability().

### commercial-execution

Universal Production Engine (2026-07-19): the Commercial Execution Layer — which marketplaces are autonomous vs need real founder action right now (approval gates, computed off every arm's own live status()), plus the most recent real publish attempts from the ledger.

- Data: `GET /api/v1/commercial-execution`
- Health: `GET /api/v1/commercial-execution/health`
- Reuses: commercial_execution.approval_gates + channels.ledger, via mission_control_api.py.

### ai-capability-registry

Real AI provider capability registry (Claude, GPT, Gemini, Grok, DeepSeek, Qwen, Mistral, local models, plus Groq itself) — Groq metrics computed live from data/ai_cost_log.jsonl (REAL where measured), every other provider honestly DISCOVERY-level until a credential exists and is actually called. Plus the append-only log of real department requests for a different/better model.

- Data: `GET /api/v1/ai-capability-registry`
- Health: `GET /api/v1/ai-capability-registry/health`
- Reuses: ai_capability/registry.py list_providers()/read_capability_requests() (Autonomous Digital Company v1, Track B2, 2026-07-19), via mission_control_api.py.

### golden-hunter-status

Golden Hunter Evolution -- real recent activity + top currently-scored opportunities, each with a real, informational pre-acceptance ROI estimate. Never changes the real accept/reject gate.

- Data: `GET /api/v1/golden-hunter-status`
- Health: `GET /api/v1/golden-hunter-status/health`
- Reuses: mission_control_api.py _golden_hunter_status() (EOS Phase 2, 2026-07-19) -- reuses golden_opportunities.json, data/golden_hunter_events.jsonl, and revenue_pipeline.plan.estimate_pre_acceptance_roi() verbatim.

### pioneer-status

Pioneer -- real discovery activity. Honestly discloses that Pioneer's candidates share the same event log as Golden Hunter (no separate Pioneer-only counter exists).

- Data: `GET /api/v1/pioneer-status`
- Health: `GET /api/v1/pioneer-status/health`
- Reuses: mission_control_api.py _pioneer_status() (EOS Phase 2, 2026-07-19).

### knowledge-graph

A real, queryable company memory -- nodes (Niche, Decision, ProductionRun, PublishChannel, AIProvider) and edges built fresh from 5 real data sources on every call. The Decision->ProductionRun edge is honestly labelled 'exact' (real production_id match) or 'approximate' (best-effort niche-text fallback) -- never presented as certain when it isn't.

- Data: `GET /api/v1/knowledge-graph`
- Health: `GET /api/v1/knowledge-graph/health`
- Reuses: knowledge_graph/build.py build_graph() (EOS Phase 2, 2026-07-19) -- reuses data/decisions.jsonl, data/market_intelligence_analyses.jsonl, data/sales_ledger.jsonl, data/ai_cost_log.jsonl verbatim, no new data collection.

### department-health

Per-named-department health rollup -- pure assembly of already-computed real signals (orchestrator engine success rates, channel approval status, real activity counts, AI provider status, infrastructure status, recovery/retry state). Researchers and Customer Intelligence are honestly 'no real data' -- never a fabricated score.

- Data: `GET /api/v1/department-health`
- Health: `GET /api/v1/department-health/health`
- Reuses: department_health.py build_department_health() (EOS Phase 2, 2026-07-19) -- reuses executive_intelligence.engine_health, commercial_execution.approval_gates, ai_capability.registry, infrastructure_bridge.py, channels.ledger, and factory_state.py verbatim.

### research-department

Real analysis assembled under 7 named research categories (Market, Competitor, Pricing, Publishing, Automation, Technology, Customer) -- pure assembly of already-real signals, no new analysis logic. Technology and Customer research are honestly 'Unknown' -- no module evaluates tech choices, and this factory has zero real customer data.

- Data: `GET /api/v1/research-department`
- Health: `GET /api/v1/research-department/health`
- Reuses: research_department.py build_research_report() (EOS Phase 2, 2026-07-19) -- reuses market_intelligence_analyses.jsonl, competitor_discovery.py, profit_oracle.py constants, commercial_execution.approval_gates, and evolution_engine.py verbatim.

### ai-doctor

The real, non-fabricated engineering-health system replacing quality_doctor.py's confirmed-fake pattern -- combines evolution_engine's bottleneck/tech-debt/ROI/capability-gap signals with real infrastructure status and a real (never-fabricated) dependency-pinning + npm-audit check.

- Data: `GET /api/v1/ai-doctor`
- Health: `GET /api/v1/ai-doctor/health`
- Reuses: ai_doctor.py build_ai_doctor_report() (EOS Phase 2, 2026-07-19) -- reuses evolution_engine.py and infrastructure_bridge.py verbatim, no reimplementation.

### integration-registry

Real, adapter-based extension points for every founder-named future vendor (n8n, GitHub, Notion, Slack, Discord, Cloudflare, Docker, Supabase, PostgreSQL, vector databases, Shopify, KDP, Perplexity, MiniMax, etc.), plus AI providers/commerce channels referenced from their own real registries -- never a second, duplicate source of truth for those. No live 'test connection' calls -- real env-var presence only.

- Data: `GET /api/v1/integration-registry`
- Health: `GET /api/v1/integration-registry/health`
- Reuses: integration_registry.py list_integrations() (EOS Phase 2, 2026-07-19) -- references ai_capability/registry.py and channels/registry.py rather than duplicating them.

### founder-console

The only view framed as 'you need to decide something': blocked marketplace channels + why, DEFERRED decisions awaiting a call, the real attention/review flags, and BLOCKERS.md's founder-only action list. Everything else in Mission Control stays informational.

- Data: `GET /api/v1/founder-console`
- Health: `GET /api/v1/founder-console/health`
- Reuses: founder_console.py build_founder_queue_partial() (EOS Phase 1, 2026-07-19) + lib/dashboard_data.js readAttentionFlag()/readReviewFlag() + a BLOCKERS.md read (same technique as readNextDollarActions()).

### evolution-report

Company Evolution Engine -- real bottleneck detection, technical debt, high-ROI opportunity ranking, tool-integration proposals, and a new capability-gap scan (config/capability_registry.json entries not yet REAL). Detection only, never automatic execution.

- Data: `GET /api/v1/evolution-report`
- Health: `GET /api/v1/evolution-report/health`
- Reuses: evolution_engine.py build_evolution_report() (EOS Phase 1, 2026-07-19) -- combines executive_intelligence.bottlenecks, strategic_intelligence.technical_debt, revenue_pipeline.pipeline, tool_intelligence.proposals, and the new capability_registry_scanner.py.

### market-review

Weekly Market Review -- niches scanned, real opportunity-gap/customer-pain trend (period vs. all-time), and top rejection reasons. The one weekly Continuous Improvement Engine review type that had no real generator before EOS Phase 1.

- Data: `GET /api/v1/market-review`
- Health: `GET /api/v1/market-review/health`
- Reuses: market_intelligence_core/market_review.py generate_market_review() (EOS Phase 1, 2026-07-19) -- reuses strategic_intelligence.rejection_patterns.most_frequent_rejection_reasons() verbatim, no reimplementation.

### strategic-recommendations

Strategic Recommendations tab: strategic_intelligence's real decision-pattern/rejection/technical-debt report (ADR-054), previously only reachable bundled inside the combined executive report, plus the same real tool-integration proposals as tool-recommendations.

- Data: `GET /api/v1/strategic-recommendations`
- Health: `GET /api/v1/strategic-recommendations/health`
- Reuses: strategic_intelligence/report.py generate_strategic_report() (ADR-054) + tool_intelligence/proposals.py, via mission_control_api.py.

### tool-recommendations

Real, evidence-cited software/AI-tool integration proposals -- '(مقترَح، لا تنفيذ)' (proposed, not implemented), matching the existing ADR-024 convention. Every proposal is grounded in a real gap this factory's own audits found, with why/business-value/effort/ROI/dependencies/risks fields — never a generic tool pitch.

- Data: `GET /api/v1/tool-recommendations`
- Health: `GET /api/v1/tool-recommendations/health`
- Reuses: tool_intelligence/proposals.py list_proposals() (Autonomous Digital Company v1, Track B3, 2026-07-19), via mission_control_api.py.

### infrastructure-status

Real CPU/memory/disk (Node's os/fs modules) plus a real AI cost-rate trend over data/ai_cost_log.jsonl (this week's real spend vs. the real trailing daily average). No fabricated 'quota remaining' — Groq exposes no queryable quota API.

- Data: `GET /api/v1/infrastructure-status`
- Health: `GET /api/v1/infrastructure-status/health`
- Reuses: lib/infrastructure_intelligence.js getInfrastructureStatus() (Autonomous Digital Company v1, Track B1, 2026-07-19) — pure os/fs + JSONL reads, no new dependency.

### docs

Machine-readable version of this same file: `GET /api/v1/docs`.
