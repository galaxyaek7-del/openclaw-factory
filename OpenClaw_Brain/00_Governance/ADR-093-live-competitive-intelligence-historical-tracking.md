# ADR-093 — Live Competitive Intelligence: Historical Tracking Foundation

**Date:** 2026-07-23
**Status:** Adopted. First of several pieces of the "Live Competitive Intelligence Layer" mission — historical tracking, the piece everything else depends on.

---

## The directive

"MISSION: PHASE NEXT — LIVE COMPETITIVE INTELLIGENCE LAYER" — extend (never duplicate) `market_intelligence_core`, `profit_oracle`, `decision_engine`, and `executive_board` with: real competitor discovery across 6 types, live tracking of 11 event categories, an 8-dimension threat engine, Executive Board integration (a real competitor brief before every production decision, automatic re-opening when the landscape materially changes), and alerting for 7 named event types — all under a strict "never invent competitors/funding/market share/customer counts" rule.

## What a real search found

`competitor_discovery.py` (ADR-042) already does real HN+GitHub competitor discovery with 6 categories (`Direct Competitor`, `Indirect Competitor`, `Alternative Solution`, `Enterprise Leader`, `Emerging Startup`, `Unclassified`) — covering 4 of the 6 requested competitor types almost exactly. `executive_board.py`'s `analyze_as_cmio()` already has a `risk_intel` parameter with slots for `pricing_changes`/`regulation_changes`/`technology_disruption` — and `enterprise_readiness.py`'s `run_risk_intelligence_scan()` **already honestly discloses** `pricing_changes` as `Unknown` with the exact reason: *"no real historical competitor pricing tracking stored yet — needs repeated real runs to compare."* That disclosed gap is precisely what this ADR closes the foundation for.

## The real data-source limit, raised and resolved

Of the 11 requested live-tracking event types, only competitor appearance/disappearance and real metric growth (GitHub stars, HN points) are observable with this factory's real, existing data sources (HN Algolia, GitHub Search — both free, keyless). Funding events, acquisitions, hiring spikes, security incidents, regulatory changes, and customer migrations have no real, accessible data source anywhere in this factory — no Crunchbase/PitchBook/LinkedIn/CVE/regulatory-filing connector exists. Founder confirmed: build what's real (competitor-appearance and metric-trajectory tracking), give the other 9 event types a real, honest evidence-recording path (not auto-detection) rather than leaving them unbuilt or fabricating them.

## What was built

**`competitor_discovery.py`:**
- `COMPETITOR_HISTORY_FILE` (`data/competitor_history.jsonl`, new): every real refresh (never a cache hit) now preserves the snapshot it's about to replace, append-only, before overwriting — `save_database()`'s prior behavior silently discarded this, which is exactly why no historical comparison was possible before.
- `diff_competitor_snapshots(old, new)`: a real, pure comparison — new competitors (appeared), disappeared competitors, and real growth signals (`github_stars`/`hacker_news_points` increasing) matched by competitor name. Honestly reports `has_history: False` on a first-ever discovery — never fabricates a trend from one data point. Never reports a decline as growth.
- `is_open_source` field added per competitor: a real, 100%-verifiable fact from which API the hit came from (GitHub-sourced = open source), not a heuristic — closes "identify open-source substitutes" from the original request. "Bundled platform alternative" (the 6th requested type) is deliberately **not** tagged — no real signal in either API distinguishes a platform feature from a standalone product, and guessing would be exactly the fabricated classification this module's docstring already refuses.
- `get_or_refresh_competitors()` now attaches a real `changes` key (the diff above) to every fresh result, and gained a `history_file` parameter mirroring `db_file`'s own test-isolation convention.

**Isolation threaded through the whole real call chain**, the same discipline this session already established for `competitor_db_file`/`ledger_path`: `orchestrator.orchestrator._enrich_with_real_competition()` → `run_cycle()` → `revenue_pipeline.pipeline.process_opportunity()`/`run_revenue_pipeline()` → `factory_orchestrator.run_master_cycle()`. Two pre-existing tests in `tests/test_competitor_discovery.py` (`test_stale_entry_triggers_a_real_refresh`, `test_force_always_refreshes_even_if_fresh`) were found, mid-verification, to be about to leak real history writes into the live default file the moment this shipped — the exact bug class this session already found once for `market_hunter.py`'s `decisions_path` and once more for `competitor_db_file` itself — fixed before it ever reached the live file, not discovered after.

## Verification

`tests/test_competitor_discovery.py`: 12 new tests (`TestDiffCompetitorSnapshots` — 6 pure-function tests; `TestCompetitorDatabase` — 4 new history-integration tests plus the 2 pre-existing tests fixed above; `TestDiscoverCompetitors` — 1 new `is_open_source` test). Full existing test suite (`test_orchestrator.py`, `test_decision_engine.py`, `test_market_intelligence_core.py`, `test_market_intelligence_engine.py`, `test_enterprise_readiness.py`) run first as the highest-risk subset given the signature changes, then the complete repository suite. Real `data/competitor_database.json` diffed byte-for-byte clean before/after; `data/competitor_history.jsonl` confirmed never created outside of test runs.

## What's next

This ADR covers the historical-tracking foundation only. The Threat Engine (3 real dimensions: competitor saturation, market concentration, new-entrant trajectory — the other 5 requested dimensions stay honest `Unknown`), the Executive Board competitor-brief integration, the decision re-open trigger, the real evidence-recording extension to `market_evidence.py` for the 9 non-auto-detectable event types, and alerting are each separate, sequenced pieces — not built in this pass, per this session's own "one real, verified piece at a time" discipline.
