# ADR-096 — Decision Re-open Trigger

**Date:** 2026-07-23
**Status:** Adopted. Closes the last remaining piece of the Live Competitive Intelligence mission (ADR-093, ADR-094, ADR-095).

---

## The directive

Implement the deferred Decision Re-open Trigger. It must reopen a previous Executive Board decision ONLY when new verified evidence materially changes the original confidence or risk profile — never on speculation or an AI-generated assumption, and only on verifiable evidence from the Market Evidence layer. Every reopen event must be recorded with timestamp, reason, previous decision, new evidence, confidence delta, and final board outcome. Integrate with Executive Board, Mission Control, Decision Engine, Opportunity Queue, and Revenue Engine. Preserve full audit trail and rollback capability.

## The materiality rule

Deterministic, grounded entirely in fields other modules already computed and verified — never a freely-generated judgment:

- **1+ real Critical-severity alert** (`market_alerts.py`, ADR-095) since the last board meeting → material by itself. A `competitor_customer_migration`, `competitor_regulatory_change`, or a new Enterprise Leader competitor is already severe enough on its own real terms — see `market_alerts.py`'s own stated severity rationale.
- **2+ real High-severity alerts** since the last meeting → material (compounding real threats). A single High alert alone is not — this avoids a reopen firing off one moderately-serious signal, mirroring the "no alert spam" discipline `market_alerts.py`'s own dedupe already established for alerts themselves, applied one layer up so reopening doesn't spam either.
- Anything less (only Medium/Low alerts, or alerts that predate the last meeting) → never material.

An alert with no real, parseable `occurred_at`/`alerted_at` timestamp is honestly excluded from "new since the last meeting" — never assumed to be new. This is the literal implementation of "never reopen based on speculation": the trigger only ever looks at real severities `market_alerts.py` already computed from real, cited data (a GitHub/HN API fact, or a human-cited competitor claim with a real `source_url` — ADR-095's citation gate), and only ever counts an alert as new evidence when its own timestamp proves it post-dates the decision being reconsidered.

## What was built

**`decision_reopen.py` (new module):**
- `check_for_reopen_trigger(niche, ...)` — pure, read-only. Pulls the previous real meeting via `executive_board.get_latest_board_brief()`, the real active alerts via `market_alerts.get_active_alerts()`, filters to those genuinely new since the previous meeting, and applies the materiality rule above. Honest `should_reopen: False` when there's no prior meeting to reopen at all.
- `execute_reopen(niche, ...)` — the only function that actually re-convenes the board. Refuses honestly (never fabricates a result) when the trigger isn't material, or when no real decision is on record to rebuild a spec from. On a real material trigger: rebuilds the exact same real spec `factory_orchestrator.py` itself uses (via the newly-public `factory_orchestrator.build_spec()` — reused, not duplicated, closing a real risk of the two ever silently diverging), calls `executive_board.convene_board()` for the real new meeting, computes the real confidence delta, and appends one permanent event to `data/decision_reopens.jsonl` with every required field: `reopened_at`, `reason`, `trigger_alerts` (the real new evidence), `previous_decision` (convened_at/board_decision/confidence), `new_decision` (same three fields from the fresh meeting), `confidence_delta`, and `decision_changed`.
- `scan_and_maybe_reopen(niche, ...)` — the one real, on-demand, do-everything entrypoint: runs a real `market_alerts.scan_market_alerts()` first, then `execute_reopen()`. No scheduler exists in this factory (CLAUDE.md) — this only ever runs when explicitly invoked.
- `get_reopen_history(niche, ...)` — read-only, the full permanent audit trail for a niche.

**`factory_orchestrator.py`:** `_build_spec()` renamed to public `build_spec()` (a real, deliberate exception to "prefer duplicating a tiny private helper over cross-module coupling" — the decision→spec mapping is meaningful, growing logic, not a one-line regex, so reuse is the right call here) and threaded a new `reopen_log_path` parameter down to `revenue_pipeline.process_opportunity()`'s own read-only lookup. `run_master_cycle()` itself deliberately does **not** check or execute a reopen — that stays `decision_reopen.py`'s own, separately-invoked responsibility, avoiding an unplanned board reconvene firing inside every real production cycle.

## Integration, and one deliberate non-integration

- **Executive Board** — the real connection *is* the reuse: `execute_reopen()` calls `executive_board.convene_board()` directly for the new meeting. No parallel board logic exists.
- **Mission Control** — three new actions: `check-decision-reopen-trigger` (read-only), `scan-and-maybe-reopen-decision` (the real mutating entrypoint), `get-decision-reopen-history` (read-only), gated by the existing `/api/v1` `requireMissionControlAuth` wrapper like every other action.
- **Decision Engine** — reused read-only, via `factory_orchestrator.find_decision()`/`build_spec()` (the exact same real lookup every other real caller of the board already uses). **Deliberately does NOT write to `decision_engine`'s `decision_outcomes.jsonl`.** A real search found that ledger's `Outcome` dataclass (`decision_engine/types.py`) is scoped specifically to real sales matched against decisions (`feedback.py`'s `sync_outcomes()`, consumed by `learning.py`'s prediction-accuracy computation) — forcing a "board reopened" event into that shape would be a real misuse of an already well-scoped structure, and would risk corrupting `learning.py`'s sale-outcome accuracy math with unrelated governance events. The correct scope is a read-only connection, not a write into a system built for a different real purpose.
- **Opportunity Queue** — `opportunity_pipeline.py`'s `_annotate()` gains `reopen_history`, isolated via a new `reopen_log_path` parameter threaded through `build_opportunity_pipeline()`.
- **Revenue Engine** — `revenue_pipeline.pipeline.process_opportunity()`/`run_revenue_pipeline()` gain `reopen_history`, informational only (same non-blocking precedent as `board_brief`/`active_alerts`).

## Audit trail and rollback, scoped honestly

Every reopen event is appended, never overwritten, to `data/decision_reopens.jsonl`. The previous board meeting in `data/board_meetings.jsonl` is never mutated or deleted — verified directly in the test suite (`test_the_previous_meeting_is_never_mutated_full_audit_trail`, a byte-for-byte before/after comparison). "Rollback capability" is scoped to exactly what is real and honest: the prior decision remains fully intact and inspectable via the existing `get_latest_board_brief()`/`review_board_track_record()` reads. It does **not** mean undoing an already-executed real action (a real production run, a real publish) — this factory has no such mechanism, and none is fabricated here.

## Verification

54 new tests: `tests/test_decision_reopen.py` (new file, 21 tests — materiality helpers, trigger detection with real cached alerts including a stale-alert-is-excluded case, execute_reopen's refuse/execute paths, the full audit-trail-preservation test, `get_reopen_history`, `scan_and_maybe_reopen`), `tests/test_opportunity_pipeline.py` (+2), `tests/test_revenue_pipeline.py` (+1 plus isolation added to every existing call site), `tests/test_master_cycle_production_e2e.py` (isolation added). Highest-risk existing suites run first (`test_executive_board.py`, `test_opportunity_pipeline.py`, `test_revenue_pipeline.py`, `test_orchestrator.py`, `test_master_cycle_production_e2e.py`, `test_decision_engine.py`, `test_market_alerts.py`, `test_market_evidence.py`, `test_enterprise_readiness.py`, `test_api_contract.js`), then the full repository: Python 1141/1141 (up from 1117), Node 233/233 real tests (unchanged — this piece is Python-only). All 7 live data files (`competitor_database.json`, `competitor_history.jsonl`, `board_meetings.jsonl`, `decisions.jsonl`, `market_evidence.jsonl`, `market_alerts.jsonl`, `decision_reopens.jsonl`) confirmed untouched by the test run.

## What's next

This closes ADR-093's originally-scoped Live Competitive Intelligence mission in full. No further pieces are currently queued for this mission.
