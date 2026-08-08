# Galaxy Forge — Data Lineage Audit

**Date:** 2026-08-08 | ADR-221, Phase 30.5, Section 13.

---

## Method

For each major commercial KPI, traced SOURCE → INGESTION → TRANSFORMATION → STORAGE → API → DASHBOARD → DECISION, verified by direct code read and live calls this round.

## Traced KPIs

**Real Revenue (Mission Control "Revenue" tiles)**
SOURCE: Paddle/Gumroad/Etsy/Payhip real transactions (none have ever occurred) → INGESTION: `channels/ledger.py::record_publish_attempt()` / `finance_data.json` writer → STORAGE: `data/sales_ledger.jsonl` (34 events, 32 dry-run) + `finance_data.json` (1 record, a disclosed smoke test) → API: `GET /oracle`, `GET /api/dashboard` → DASHBOARD: multiple revenue panels → DECISION: `capital_allocation_engine.py`, `strategic_planning.py`. **Traceable end-to-end. Real value at every stage: $0 real revenue** (the one `finance_data.json` record is explicitly named `contract-test-ladder-DELETE-ME`, a smoke test artifact, not a sale — flagged here as a **stale test record that should be deleted, not a live KPI input**).

**Golden Hunter Ranked Opportunities**
SOURCE: `market_hunter.py::hunt_market()`'s real niche scan → INGESTION: `decisions.jsonl` (append-only, real) → TRANSFORMATION: `profit_oracle.py::run_oracle()` (conditional — only runs on a new GOLDEN-tier catch) → STORAGE: `golden_opportunities.json` → API: `GET /oracle` → DASHBOARD: Golden Hunter Room panel. **Traceable, but STALE**: the file has not been regenerated in 411 hours because the transformation step's trigger condition (a new golden catch) hasn't fired — the underlying daily scan runs, but its downstream ranked artifact does not always refresh with it. Flagged as **ORPHANED (in the sense of stale-but-not-invalid)**, not fake.

**Customer Health Score**
SOURCE: would be a real customer's real purchase/support/usage history → INGESTION: `customer_pipeline.py`'s request store → STORAGE: `data/customer_requests.jsonl` (**does not exist**) → API/DASHBOARD/DECISION: all real code, all correctly returning honest empty/UNKNOWN states. **No orphaned or fake data — the entire chain honestly has nothing to carry, and reports that truthfully rather than defaulting to a fabricated "HEALTHY".**

**AI Spend**
SOURCE: real Groq API responses → INGESTION: `data/ai_cost_log.jsonl` writer (per-call) → STORAGE: `data/ai_cost_log.jsonl` (230 real events) → DASHBOARD: not currently surfaced as its own panel (a real, minor gap — cost is tracked but not prominently displayed against $0 revenue). **Traceable, real, immaterial ($0.02 total).**

## Flags

- **STALE VALUE**: `golden_opportunities.json` (17 days).
- **TEST RECORD MASQUERADING AS DATA**: `finance_data.json`'s one sale record (`contract-test-ladder-DELETE-ME`) inflates `totalSales`/`totalPaddle` to $150 in the raw file — any dashboard reading this field directly without cross-checking `config/reality.json` would display a **fabricated-looking non-zero revenue figure that is not real**. This is the single highest-priority data-lineage risk found this round. **Recommendation: delete this record or explicitly exclude it from any revenue tile (some already do, via `config/reality.json` cross-checks — not universally verified across all panels this round; time-bounded).**
- No hardcoded KPI values were found in the 5 audited phase modules (see `SECURITY_AUDIT.md`'s hardcoded-data scan).
- No duplicated or undefined values found in the traced chains above.

---

*See also: `TRUTH_MATRIX.md`, `AUTOMATION_REALITY.md`.*
