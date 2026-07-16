# OpenClaw Unified Service Layer — API Reference (v1)

_Auto-generated from SERVICE_REGISTRY in server.js at server startup — do not hand-edit, it is overwritten on every restart. Source of truth: server.js._

Generated at: 2026-07-16T22:43:33.588Z

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

### docs

Machine-readable version of this same file: `GET /api/v1/docs`.
