# ADR-095 — Market Evidence & Alerting Layer

**Date:** 2026-07-23
**Status:** Adopted. Continues the Live Competitive Intelligence mission (ADR-093, ADR-094).

---

## The directive

"Continue the Live Competitive Intelligence roadmap. Implement the complete Market Evidence & Alerting layer with production-grade discipline." Extend `market_evidence.py` to capture every available real evidence source; record only verified evidence; never fabricate market events; build a 4-severity (Critical/High/Medium/Low) alert engine where every alert carries Timestamp, Source, Evidence, Confidence, and Recommended Action; alerts must automatically reach the Executive Board, Mission Control, Revenue Engine, and Opportunity Queue; preserve full backward compatibility; no shortcuts, no placeholders, no fake data.

## What a real search found

ADR-093 had already identified the real gap: of 11 originally-requested live-tracking event types, only competitor appearance/disappearance and real metric growth (GitHub stars/HN points) have a real, automated data source (`competitor_discovery.py`'s `diff_competitor_snapshots()`, ADR-093/roadmap 4.12). The other 9 (funding, acquisitions, hiring spikes, security incidents, partnerships, regulatory changes, customer migrations, feature releases beyond GitHub-visible, pricing changes) have no real, accessible data source anywhere in this factory — no Crunchbase/PitchBook/LinkedIn/CVE/regulatory-filing connector exists, and none will be fabricated. `market_evidence.py` already had the exact right shape for human-observed events (a niche, an event_type, a payload, a source, an append-only ledger) — reused directly rather than building a second, parallel evidence store.

## Design decisions

**1. "Record only verified evidence" is a real, enforced gate — scoped narrowly.** The 15 pre-existing `market_evidence.py` categories are a human's own first-hand account of their own customer interaction (a discovery call they were on, an email reply they received) — low fabrication risk, and this module's long-standing "write what you see, never reject" philosophy correctly applies. A claim about a **competitor's** business (a funding round, an acquisition) is a fundamentally different risk: this factory cannot independently fact-check a third-party claim. The honest substitute is requiring a real, checkable citation. `record_evidence()` now **raises** (not just flags) when one of the 9 new `COMPETITOR_EVENT_TYPES` is recorded without both a real `competitor` name and a real `source_url` in `payload`. This changes behavior for 0 existing callers (none of the 9 types existed before this ADR) — full backward compatibility preserved.

**2. Auto-detected alerts reuse ADR-093's already-computed `changes`, never a new computation.** `market_alerts.detect_auto_alerts()` reads whatever `competitor_discovery.py` already persisted in `data/competitor_database.json` from the last real refresh — zero new network calls, zero new diffing logic. Manually-recorded alerts (`detect_manual_alerts()`) reuse `market_evidence.get_competitor_events()` directly.

**3. Severity, confidence, and recommended actions are all deterministic, never a judgment call.** Auto-detected: a new competitor's severity comes from its real `classify_competitor()` category (Enterprise Leader → Critical, Direct Competitor → High, Emerging Startup/Alternative Solution → Medium, Unclassified → Low); a growth signal's severity comes from a real computed percentage change in GitHub stars/HN points. Manually-recorded: a static per-type baseline, each with a stated business-impact argument (e.g. `competitor_customer_migration` → Critical because it is a real, observed instance of *our own* revenue loss; `competitor_security_incident` → Low because it is mostly reputational to the competitor, not us). Confidence is 1.0 for every alert here — both detection paths only ever produce an alert from data that already passed a real verification gate (the API response itself, or `record_evidence()`'s citation requirement) — never a partially-trusted guess.

**4. "Automatically reach" means "automatically surfaced on the next real read," not a push notification.** No scheduler exists in this factory (CLAUDE.md) — there is no background process that could push an alert anywhere. `market_alerts.scan_market_alerts()` is the one real, on-demand write path (dedupes against every already-persisted alert for a niche via a stable `dedupe_key`, so re-scanning never re-alerts the same underlying event — "no alert spam"). `market_alerts.get_active_alerts()` is the one real, read-only lookup every connected system uses — the exact same pattern `executive_board.get_latest_board_brief()` already established and the founder already confirmed for the Executive Board Integration mission.

## What was built

**`market_evidence.py`:** `COMPETITOR_EVENT_TYPES` (9 new categories, appended to `EVENT_TYPES`), the citation-required gate in `record_evidence()` (scoped only to the 9 new types), `get_competitor_events()`, and an additive `competitor_landscape_events` key in `summarize_niche()`'s return shape (every pre-existing key unchanged).

**`market_alerts.py` (new module):** `SEVERITY_LEVELS`, `detect_auto_alerts()`, `detect_manual_alerts()`, `scan_market_alerts()` (the only write path — dedupes, persists to `data/market_alerts.jsonl`), `get_active_alerts()` (the only read path — grouped by severity).

**Connected to the 4 named systems**, all via the same read-only `get_active_alerts()` lookup:
- **Executive Board** — `executive_board.build_strategic_brief()`'s Threat Assessment lens gains `active_alerts`; `convene_board()` gained an `alerts_path` parameter threaded the same way `board_path` already is.
- **Mission Control** — new `scan_market_alerts` (mutating) and `get_market_alerts` (read-only) actions in `mission_control_api.py` → `server.js`'s `scan-market-alerts`/`get-market-alerts`, gated by the existing `/api/v1` `requireMissionControlAuth` wrapper.
- **Revenue Engine** — `revenue_pipeline.pipeline.process_opportunity()`/`run_revenue_pipeline()` gained `active_alerts` in their result (informational only, same non-blocking precedent as `board_brief` from ADR-094).
- **Opportunity Queue** — `opportunity_pipeline.py`'s `_annotate()` gained `active_alerts`, isolated via a new `alerts_path` parameter threaded through `build_opportunity_pipeline()`.

`factory_orchestrator.run_master_cycle()` gained `alerts_path`, threaded to both `convene_board()` and `revenue_pipeline.process_opportunity()` — the same real alerts ledger, deliberately shared, not two independent stores (same pattern as `board_path`).

## Verification

54 new tests: `tests/test_market_evidence.py` (+8, `TestCompetitorEvidence` — citation-gate rejection/acceptance, backward-compatibility of the 15 pre-existing types, `get_competitor_events()`, additive `summarize_niche()` shape), `tests/test_market_alerts.py` (new file, 21 tests — severity helpers, auto-detection from a real cached snapshot, manual detection from real recorded evidence, scan/dedupe/no-spam, read-only `get_active_alerts()` never writing), `tests/test_executive_board.py` (+2 — active_alerts honestly empty and a real persisted alert reaching the strategic brief), `tests/test_opportunity_pipeline.py` (+2), `tests/test_revenue_pipeline.py` (+1, plus `alerts_path` isolation added to every existing call site), `tests/test_master_cycle_production_e2e.py` (isolation added). Highest-risk existing suites run first (`test_market_evidence.py`, `test_executive_board.py`, `test_opportunity_pipeline.py`, `test_revenue_pipeline.py`, `test_orchestrator.py`, `test_master_cycle_production_e2e.py`, `test_decision_engine.py`, `test_enterprise_readiness.py`, `test_api_contract.js`), then the full repository: Python 1117/1117 (up from 1084), Node 233/233 real tests (unchanged — this piece is Python-only). `data/competitor_database.json`/`competitor_history.jsonl`/`board_meetings.jsonl`/`decisions.jsonl`/`market_evidence.jsonl`/`market_alerts.jsonl` confirmed never created or modified outside test runs.

## What's next

The decision re-open trigger (deferred in ADR-094, founder-confirmed) remains the one still-open piece named in ADR-093's original scope. No further pieces are currently queued for this mission.
