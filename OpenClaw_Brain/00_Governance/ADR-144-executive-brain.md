# ADR-144 — Executive Brain

**Date:** 2026-07-30
**Status:** Adopted.

---

## The directive

"MISSION: Build the Executive Brain V2 for Galaxy Forge... The Executive Brain becomes the only decision maker." Four phases: P0 (consume 10 named intelligence systems, produce ONE executive decision per cycle, no conflicting actions), P1 (an 11-step daily autonomous loop, explicitly "no human intervention"), P2 (self-improvement: detect weak modules, propose, validate, run regression, reject unsafe, promote safe — automatically), P3 (every success/failure/discovery/decision becomes Knowledge Graph knowledge, no duplication). A named Priority 1-5 framework (System Stability > Opportunity Discovery > Premium Product Creation > Revenue Growth > Self Evolution). Mission Control becomes "the single source of truth."

## The real conflict and the real overlap, surfaced before any code was written

Two research findings, both confirmed via direct code/history checks, not assumed:

1. **Phase P1's "no human intervention" and Phase P2's "reject unsafe changes, promote safe improvements" (automatically) reopen a question already declined 4 times**: `master_loop.py`'s always-on-daemon proposal (ADR-107 → ADR-110 → ADR-115), and most recently ADR-142 (2026-07-29), where the founder was asked directly via `AskUserQuestion` whether to loosen exactly this kind of execution gate and answered "keep all 4 gates exactly as-is." `evolution_queue.py`'s own docstring — unchanged since ADR-133 — still states Execute is "deliberately NOT automated... the founder's own explicit choice."

2. **Nearly every one of Phase P0's 10 named inputs already has a real, wired aggregator.** `strategic_intelligence_core.build_executive_brief()` (ADR-137) already synthesizes company health, top risks/opportunities/bottlenecks, recommended priorities, and founder-required decisions from `resilience_monitor`/`ceo_decision_center`/`evolution_engine`/`founder_console`, once per cycle, verbatim. `global_opportunity_exchange.py` (ADR-140), `capital_allocation_engine.py` (ADR-139), `evolution_queue.py` (ADR-133/143), `autonomous_operations_status.py` (ADR-142), and the Knowledge Graph (`knowledge_graph/build.py`) are all real and already wired. More pointedly: the Architecture Stability Review committed this same session (`012c084`) explicitly found "9+ Mission Control panels answer overlapping 'what matters most' questions" as this factory's clearest maintainability risk, and recommended consolidation, not more layers, as the single highest-value fix — building an "Executive Brain V2" on top of `strategic_intelligence_core`/`ceo_decision_center`/`galaxy_council`/`executive_board`/`master_loop` would have repeated the exact pattern that review diagnosed and committed hours earlier.

**Both surfaced via `AskUserQuestion` before any code was written. The founder's answers**: keep execution human-gated (Executive Brain recommends; approval stays a real founder action through the existing mechanisms — evolution-queue approve/reject, capital reallocation, publish protection — exactly unchanged); consolidate rather than add an 11th parallel layer.

## What was built

`executive_brain.py` (new) calls `strategic_intelligence_core.build_executive_brief()` + `global_opportunity_exchange.build_global_opportunity_exchange_dashboard()` + `capital_allocation_engine.build_capital_allocation_dashboard()` + `evolution_queue.list_evolution_queue()` + `channels.ledger.revenue_trend()` exactly once each — never a second competing computation. It adds exactly two genuinely new pieces:

1. **`_candidate_directives()` + `_arbitrate()`** — the one real judgment this module contributes. Every candidate action already exists inside one of the reused systems above (an active resilience alert, a publish emergency stop, a DEFERRED opportunity decision, an accelerate-bucket niche, a top-ROI initiative, a portfolio concentration warning, the highest-ranked evolution-queue proposal) and is tagged with the founder's own named Priority tier (1-5) via its real source, never invented. `_arbitrate()` picks the single lowest-tier candidate as the cycle's Executive Directive; a genuine tie within the lowest tier is honestly reported `SPLIT` (same discipline as `galaxy_council.py`'s own N-way disagreement handling) rather than arbitrarily resolved. Verified live against real factory data: found 43 real candidates across all 5 tiers and correctly arbitrated to a real Tier-1 finding (an unpinned npm dependency warning from `resilience_monitor`), not a fabricated one.

2. **A permanent, append-only decision ledger** (`data/executive_directives.jsonl`) — the real "store lessons permanently" Phase P1/P3 asked for, same shape/convention as `galaxy_council.py`'s `data/council_recommendations.jsonl`. `knowledge_graph/build.py` gained a matching `_executive_directive_nodes()` function and a new `ExecutiveDirective` node type, mechanically parsed from the ledger — closing "every architecture decision becomes knowledge" for this new artifact specifically, with an edge to the real `Proposal` node it cites when resolvable (never a guessed edge otherwise, same discipline as every other node type in that module).

**A real design bug found and fixed during implementation**: the first draft's Mission Control read handler defaulted to `record_ledger=True`, meaning every page view would append a near-duplicate entry to the "permanent" ledger — directly violating Phase P3's own "no duplicated knowledge" requirement. Split into `_executive_brain_directive()` (the live Mission Control view, `record_ledger=False`, never writes) and `_generate_daily_executive_directive()` (the one real path that grows the ledger, called only by `factory_loop.js`'s daily tick). Verified live: the expensive endpoint (measured ~59s — it chains 3 real full-portfolio scans) returns a real, correct directive over HTTP, and the ledger file does not even exist on disk afterward, confirming the live view never records.

## What stays exactly as human-gated as before

`build_executive_directive()` never calls `evolution_queue.approve_proposal()`, never reallocates capital, never publishes, never retires a business. `requires_founder_approval` is always `True` in the real response. Nothing in this module, `factory_loop.js`'s new daily tick step, or the new Mission Control panels adds a single new execute-capable code path — every one of the 4 protected gates reaffirmed in ADR-142 is untouched.

## What was deliberately NOT built (Phase P2, mostly)

Phase P2's "detect weak modules, propose improvements, generate ADR draft, validate impact, run regression, reject unsafe changes, promote safe improvements" is, functionally, a re-description of the already-real `evolution_queue.py` pipeline (Observe → Simulate → Decide → Learn, ADR-133/143) plus this session's own Architecture Stability Review process — not rebuilt here. No new self-improvement engine was written; `executive_brain.py`'s Tier-5 candidate generator cites `evolution_queue.py`'s own real `awaiting_approval` list rather than duplicating its logic. A genuinely new capability — automatically running regression tests against a *proposed* code change before it reaches `AWAITING_FOUNDER_APPROVAL` — does not exist anywhere in this factory today and was not built in this round; flagged here as an honest gap for a future, narrowly-scoped round, not silently assumed to already exist.

## Mission Control

`mission_control_api.py` gained `executive_brain_directive` (live, `record_ledger=False`), `generate_daily_executive_directive` (the daily-tick-only path, `record_ledger=True`), and `executive_directives_history` (read-only ledger view). `server.js`'s `SERVICE_REGISTRY` gained `executive-brain` (120s timeout, measured live ~59s) and `executive-directives-history` (cheap). `mission_control_executive_v1.html` gained two new panels placed first in the section list — the founder's own "Mission Control becomes the single source of truth" ask — with the 4 most directly-reused existing panels (`evolution-queue`, `executive-brief`, `capital-allocation-dashboard`, `global-opportunity-exchange`) cross-referenced in place, unchanged and undeleted, per the founder's own "consolidate, preserve backward compatibility" answer.

## Validation

`tests/test_executive_brain.py` (new, 17 tests): arbitration tier-ordering and honest `SPLIT`/`NO_ACTION_NEEDED` behavior, every candidate generator's real-signal-only discipline, the Architecture Health citation's mechanical parse (and honest `Unknown` when the report doesn't exist), risk-level max-severity selection, ledger append/read-back ordering, and — the regression case for the bug found above — a full-chain mocked test proving `record_ledger=False` never touches disk while `record_ledger=True` writes exactly once. Verified live over a real logged-in HTTP round-trip on a disposable test server: `executive-directives-history` (instant, honestly empty) and `executive-brain` (~59s, real `SINGLE_DIRECTIVE` Tier-1 result, confirmed the ledger file still doesn't exist afterward). `data/evolution_queue_state.json` and every other real data file confirmed unchanged by this session's testing.
