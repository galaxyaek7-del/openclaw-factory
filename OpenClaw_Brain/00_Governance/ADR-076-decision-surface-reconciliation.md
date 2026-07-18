# ADR-076 — Decision Surface Reconciliation: One Single Source of Truth

**Date:** 2026-07-18
**Status:** Adopted, tested (494 Python tests green, zero regressions), **verified end-to-end across every stage, zero mocking of the scoring itself.**
**Closes:** `ENGINEERING_ASSESSMENT_20260718.md`'s Critical Issue C1 — the top-priority finding of that review.

---

## The problem

Two real decision-making surfaces silently disagreed. `factory_loop.js`'s automatic tick gated via `profit_oracle.ladder_opportunity_score()` (`ADR-066`/`070`). `decision_engine/engine.py` — what Mission Control's Decision Queue actually reads — still called the old, ladder-unaware `profit_oracle.opportunity_score()`. A founder checking Mission Control would see a different picture than what the automatic loop was really doing.

## The fix

**One scoring function, one recording function, one file.**

1. **`decision_engine/engine.py`'s `evaluate_and_decide()`** now accepts an optional `ladder` parameter. When present, it calls `profit_oracle.ladder_opportunity_score()` instead of the old `opportunity_score()` — removing the actual duplicate-scoring-function problem. Omitting `ladder` (every caller before this parameter existed) reproduces the exact prior behavior, unchanged — the old tier-based path remains available for niches with no ladder context.

2. **New `decision_engine/engine.record_ladder_decision()`** — a lightweight recorder for the fast, always-on discovery path. It never recomputes a score (it's handed the exact result the caller already got from `ladder_opportunity_score()`), so it can never silently disagree with the number the caller actually acted on. `ai_ceo_decision` is honestly recorded as `"N/A"` — no live AI-CEO evidence gathering runs here; that stays the separate, deliberately heavier `evaluate_and_decide()` path, still available for manual review.

3. **`decision_engine/types.py`'s `Decision`** gains two additive fields: `ladder` (which Strategic Production Priority Ladder rank, when known) and `decision_path` (`"ladder_fast_gate"` or `"ai_ceo_full_evaluation"` — which of the two real paths produced this record, never blended). Both default to values that preserve every one of the 1,344+ existing historical records' real meaning unchanged.

4. **`market_hunter.py`'s `hunt_market()`** now calls `record_ladder_decision()` for every real candidate it scans — accepted or rejected, matching `decision_engine`'s own stated principle that "a REJECTED decision is exactly as findable as an ACCEPTED one." Guarded import, exactly like `PROFIT_ORACLE`/`INSPECTORS` — a broken `decision_engine` import can never crash the real hunt; a recording failure can never block it either.

5. **`mission_control_api.py` needed zero changes.** It already reads `data/decisions.jsonl` directly via `decision_engine.store.read_decisions()`/`decision_engine.ranking`. The moment `market_hunter.py` became a real co-writer to that same file, Mission Control started reflecting real, current, ladder-aware decisions automatically — the single most elegant part of this fix.

## What was deliberately NOT changed

- **`factory_loop.js`'s `huntGolden()` does not also write to `data/decisions.jsonl`.** It re-validates the top candidate via the same real `getLadderOpportunityScore()` call (a legitimate freshness/safety gate before spending real production resources), but the same niche was already recorded moments earlier in the same daily cycle by `market_hunter.py` (`maybeRunMarketHunter()` runs once per day; `huntGolden()` runs every tick). Writing twice for the same real decision would be redundant, not more correct — the authoritative record is written once, at discovery time.
- **`decision_engine`'s rich AI-CEO evaluation path was not removed or replaced.** It's a genuinely different, richer analysis (live customer-pain/competitor evidence), not pure duplication — only its underlying numeric gate was unified with the ladder-aware one. It remains available for deliberate manual review via Mission Control.
- **No new plumbing into `channels/paddle_arm.py`/distribution.** `briefFromGoldenOpportunity()` already sources its price from the same real `ladder_price` (`ADR-071`); this ADR verifies that chain end-to-end rather than rebuilding it.

## Verified end-to-end, not asserted

`tests/test_unified_pipeline_e2e.py` — 5 real stages, no mocking of any scoring function, one real niche (`"workflow automation system for logistics companies"`, ladder `b2b_systems`) proven to carry the **identical** score/price at every stage:

1. Golden Hunter discovers and scores it (real `ladder_opportunity_score()` call).
2. `market_hunter.hunt_market()` records it into a real `decision_engine` store — same score, never recomputed.
3. `decision_engine.ranking.rank_queue()` (Mission Control's real read path) shows the same record with the same score.
4. `factory_loop.js`'s real `getLadderOpportunityScore()` (a live subprocess call, no mocking) returns the identical score/price.
5. The n8n/Telegram notification payload and the production brief Paddle's price ultimately comes from both carry the same real number.

## Impact

- `decision_engine/types.py`: `Decision` gains `ladder`, `decision_path` (additive, backward compatible).
- `decision_engine/engine.py`: `evaluate_and_decide()` gains optional `ladder` param; new `record_ladder_decision()`.
- `market_hunter.py`: guarded import + call to `record_ladder_decision()` for every real scored candidate.
- `mission_control_api.py`: unchanged — already reads the now-unified store.
- New tests: 3 in `tests/test_decision_engine.py` (ladder-aware `evaluate_and_decide()`), a new `TestRecordLadderDecision` class (4 tests), a new `tests/test_market_hunter_decision_recording.py` (3 tests), a new `tests/test_unified_pipeline_e2e.py` (5 real end-to-end stages). Full suite: 494 Python tests green, zero regressions.
- `PROJECT.md` updated with the final unified architecture diagram.
