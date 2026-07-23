# ADR-094 — Executive Board Integration: 6 Lenses, 6-Field Decisions, 6 Connected Systems

**Date:** 2026-07-23
**Status:** Adopted.

---

## The directive

"MISSION: Continue the Executive Board Integration" — integrate the Threat Intelligence Engine (ADR-093, roadmap 4.13) into the AI Executive Board (`executive_board.py`, ADR-090); every executive decision must automatically include 6 lenses (Threat Assessment, Opportunity Assessment, Market Intelligence, Financial Impact, Technical Risk, Customer Trust Impact); every board decision must produce 6 fields (Decision, Confidence, Evidence, Risks, Recommended Actions, Follow-up Tasks); connect the integration to Decision Engine, Mission Control, Executive Dashboard, Opportunity Queue, Market Intelligence, and Revenue Engine; never duplicate logic.

## What a real search found

Almost every one of the 6 requested lenses already existed as real, scattered evidence: `analyze_as_cto`/`analyze_as_cfo`/`analyze_as_cpo`/`analyze_as_cco` already extract technical/financial/security/privacy/support/customer_success signals from `enterprise_readiness.py`'s Product Review + Risk Register; `run_risk_intelligence_scan()` already assembled market saturation, customer complaints, and (as of ADR-093) is the natural home for the new Threat Engine; `market_evidence.summarize_niche()` was already reused inside `build_transparency_report()`; `revenue_pipeline.plan.estimate_production_cost()` already computed a real production-cost estimate; `enterprise_readiness.compute_evidence_score()` existed but was never wired into the master gate. The real, non-duplicative work was a **synthesis layer** — assembling already-computed evidence into the 6 named lenses and a 6-field decision summary — not building 6 new subsystems.

## Two scope decisions, founder-confirmed before building

1. **Revenue Engine gating stays informational.** The board's verdict is attached to `revenue_pipeline.process_opportunity()`'s result for visibility, but does not block `execute=`. Matches this factory's own existing `advisory_only=True` default in `factory_orchestrator.run_master_cycle()` — almost every real niche today has thin real market evidence, so a hard block would risk freezing production, the exact risk already flagged earlier this session. `enforce_board=True` at the orchestrator layer remains the real hard-gate path for whoever wants it.
2. **The "decision re-open trigger" (ADR-093's named next step) is out of scope for this pass.** Not asked for in this mission's text; stays its own separate, sequenced piece.

## What was built

**`enterprise_readiness.py`** — `run_risk_intelligence_scan()` gained a real `threat_assessment` key: reuses whatever competitor snapshot is already cached locally for the niche (`competitor_discovery.load_database()` + `compute_threat_assessment()`, ADR-093) — never a fresh network call from this path. Honest, reasoned Unknown (not a fabricated "0 competitors = no threat") when no discovery has ever run for that niche.

**`executive_board.py`** — the real synthesis layer:
- `build_strategic_brief(spec, readiness_result, risk_intel)`: the 6 lenses, each pulled from already-computed real fields (spec's `evaluation_snapshot`, `readiness_result`'s product review/risk register/transparency report, `risk_intel`'s market saturation/threat assessment) — zero new narrative.
- `build_decision_summary(executives, tally)`: the 6-field bundle (`decision`, `confidence` — real mean of the 10 executives' own confidence, `evidence`, `risks`, `recommended_actions`, `follow_up_tasks`) — every string traces to one specific executive's own real output; `recommended_actions`/`follow_up_tasks` are mechanically derived (`"عالج: {risk}"` / `"اجمع دليلاً حقيقياً حول: {missing}"`, plus the Chief Risk Officer's already-real `exit_criteria`/`kill_switch_conditions`), never freely generated text.
- `convene_board()`'s `include_risk_intelligence` default flipped `False` → `True` — the only way "automatically include" can be true by default. Safe: `run_risk_intelligence_scan()` never makes a live network call unless `refresh_competitors=True` is separately, explicitly requested (it isn't, here).
- `get_latest_board_brief(niche, board_path=None)`: the real connection point for every other system — a read-only lookup of the latest real meeting, never convening a new one (that stays `convene_board()`'s sole responsibility, per the module's own "no single agent may approve strategic decisions alone" structural rule).

**Connected to the 6 named systems:**
- **Decision Engine** — unchanged structurally (the spec `convene_board()` evaluates already comes from `decision_engine.ranking`); `get_latest_board_brief()` is the new real read-path other decision-adjacent code now uses.
- **Mission Control** — new `get_board_brief` action (`mission_control_api.py` → `server.js`'s `get-board-brief`), gated by the existing `/api/v1` `requireMissionControlAuth` wrapper (no new auth code needed).
- **Executive Dashboard** — `lib/dashboard_data.js` gained `readLatestBoardMeetingSummary()` (pure JS, no Express/child_process dependency, same isolation-testable pattern as `readLatestMarketIntelligence()`), wired into `computeDashboard()`/`GET /api/dashboard` as `latest_board_meeting`. Initially hand-rolled its own JSONL parse loop; the repo's own `scripts/check_jsonl_duplication.js` safeguard caught this as a 3rd duplicate of an already-extracted idiom — fixed to reuse `lib/jsonl.js`'s `readJsonlEntries()` before commit.
- **Opportunity Queue** — `opportunity_pipeline.py`'s `_annotate()` gained a `board_brief` field (via `get_latest_board_brief()`), isolated with a new `board_path` parameter threaded through `build_opportunity_pipeline()`.
- **Market Intelligence** — already covered via `risk_intel` (market saturation, customer complaints, the new threat assessment) and `market_evidence.summarize_niche()`, both reused directly inside `build_strategic_brief()`.
- **Revenue Engine** — `revenue_pipeline.pipeline.process_opportunity()`/`run_revenue_pipeline()` gained a `board_path` parameter and a `board_brief` field in the result (informational only, per the scope decision above). `factory_orchestrator.run_master_cycle()`'s existing `board_path` parameter now threads to both `convene_board()` and this new lookup — the same meetings log, deliberately shared.

## Verification

New tests: `tests/test_executive_board.py` (+7: strategic brief shape, decision summary fields/recommended-actions traceability, honest Unknown when risk intelligence skipped, `get_latest_board_brief` honest no-meeting + latest-meeting lookup), `tests/test_enterprise_readiness.py` (+2: threat assessment honest-Unknown / real-cached-snapshot), `tests/test_opportunity_pipeline.py` (+2: board_brief honest-none / real-prior-meeting, plus isolation added to the whole test class via a `board_path` fixture), `tests/test_revenue_pipeline.py` (+1: board_brief isolated and honest, plus isolation added to 3 existing calls), `tests/test_dashboard_data.js` (+2). Highest-risk existing suites run first (`test_executive_board.py`, `test_enterprise_readiness.py`, `test_opportunity_pipeline.py`, `test_revenue_pipeline.py`, `test_master_cycle_production_e2e.py`, `test_orchestrator.py`), then the full repository: Python 1084/1084 (up from 1074), Node 233/233 real tests (up from 231; 2 apparent failures are `tests/fixtures/always_crash.js`/`crash_n_times.js`, deliberately-crashing helper scripts for `test_supervisor.js` incidentally matched by an ad-hoc glob, not real tests). `data/competitor_database.json`/`competitor_history.jsonl`/`board_meetings.jsonl`/`decisions.jsonl` confirmed untouched by the test run.

## What's next

Decision re-open trigger (deferred, per scope decision above), `market_evidence.py` extension for the 9 non-auto-detectable competitor event types, alerting for the ~2 realistically-detectable event types — the remaining pieces of the Live Competitive Intelligence mission (ADR-093).
