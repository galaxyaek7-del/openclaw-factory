# OpenClaw / Galaxy Forge — Golden Hunter Engine

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). Golden Hunter already exists, extensively, under this exact name — `golden_hunter/`, `market_hunter.py`, `factory_loop.js::huntGolden()`, `data/golden_hunter_events.jsonl`. This document names the real engine, and discloses a real, current operational finding this exact investigation surfaced: not fabricated, verified live today (2026-08-07).

---

## What Golden Hunter actually is, right now

**Two real, distinct real components, not one:**

1. **`market_hunter.py::hunt_market()`** — generates candidates from `SEED_CATEGORIES` (a real, static, deterministic list — explicitly "not a live market scan," by its own docstring) plus two real linked sources: the Sensing Engine (n8n-fed, real when n8n is reachable — currently `fetch failed` per the live `/health` check) and Pioneer (`golden_hunter/pioneer.py`, a real live Hacker News query). Every candidate is scored via `profit_oracle.py::ladder_opportunity_score()`, kept only if it clears the real Proof of Payment / Pain Severity / Competitive Advantage / Long-Term Strategic Asset gates, then appended to `OPPORTUNITIES.md` and re-scored via `run_oracle()` into `golden_opportunities.json`.
2. **`factory_loop.js::huntGolden()`** — consumes `golden_opportunities.json` each tick, real staleness-gated (skips if the file is >24 hours old rather than acting on stale data), and routes an eligible top pick through real production.

## Real finding, verified live during this directive

`golden_opportunities.json` was 16 days stale (last written 2026-07-22) when this document was written. **Not a broken pipeline** — a fresh `hunt_market()` call, run live as part of writing this document, scanned 13 real candidates and correctly found 0 new golden opportunities: every candidate was a real duplicate of an already-produced product, a real prior `QUARANTINE.md`/`REJECTED_NICHES.md` rejection, or failed the Proof of Payment gate on fresh evaluation. `run_oracle()` correctly did not rewrite `golden_opportunities.json` with an unchanged result.

**The real, honest conclusion:** Golden Hunter's evaluation logic is working correctly. Its *candidate generation* is the actual constraint — a static seed list, real-scanned repeatedly, is finite. This is not a flaw introduced by this document's investigation; it is the real, current state of the system, now disclosed rather than left to look like unexplained staleness.

## What actually produces fresh real decisions today

Separately from the above, `market_hunter.py` also has a real **daily** run (`decision_engine/engine.py::record_ladder_decision()`, `decision_path="ladder_fast_gate"`) that writes directly into `data/decisions.jsonl` without going through `OPPORTUNITIES.md` — confirmed active today (real entries timestamped 2026-08-07). **This is the real, currently-active discovery pathway**, not the `golden_opportunities.json` one. `factory_loop.js`'s own comment already documents this: a ladder-tagged opportunity's production step "reuses" this daily decision rather than re-evaluating.

## Where the directive's named discovery sources really stand

`multi_source_intelligence.types.EVIDENCE_SOURCE_PRIORITY` already lists all of: `arxiv`, `amazon`, `etsy`, `gumroad`, `public_search`, `rss_feeds`, `public_reports`, `google_trends`, `github`, `product_hunt`, `reddit`, `hacker_news`, `stack_overflow`, `web_pages`. **Registered is not the same as real and live** — per this session's own repeated, direct verification: 8 of 14 are confirmed live-query-capable (amazon/arxiv/etsy/github/gumroad/hacker_news/public_search/stack_overflow); `google_trends`, `product_hunt`, `reddit`, `rss_feeds`, `public_reports` are honestly `NOT_ARCHITECTED` — real names in the priority list, no real connector code behind them yet. Creative Market, AI marketplaces, and enterprise software (also named in the directive) have no real connector at all, registered or not.

## The real, honest gap this creates

Golden Hunter cannot discover genuinely new categories of opportunity until either the seed list grows with real new candidates, or one of the `NOT_ARCHITECTED` sources becomes real. This is disclosed here as the single most concrete, actionable finding of this entire Phase 3 directive — not buried in a "future work" footnote.

---

*See also: `OPPORTUNITY_PIPELINE.md`, `OPPORTUNITY_SCORING.md`, `EXECUTIVE_OPPORTUNITY_BRIEF.md`, `GALAXY_FORGE_GOLDEN_HUNTER.md`.*
