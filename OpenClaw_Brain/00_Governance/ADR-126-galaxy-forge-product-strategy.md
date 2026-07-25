# ADR-126 — Galaxy Forge Product Strategy: the 10-Condition Checklist

**Date:** 2026-07-25
**Status:** Adopted.

---

## The directive

Founder decision: Galaxy Forge selects opportunities only when ALL of 10 conditions are satisfied — (1) High commercial value, (2) Strong Proof of Payment, (3) Low or moderate competition, (4) Difficult to copy, (5) Premium pricing potential, (6) Global scalability, (7) Long-term strategic value, (8) AI can provide a significant advantage, (9) Continuous improvement potential, (10) High profit margin. "Quality over quantity... one exceptional product is better than one hundred average products... operates like a venture capital firm combined with an elite AI product studio... every rejected opportunity is recorded with its rejection reason."

## What already existed — audited before writing any code

This is the third doctrine-tightening round this session (ADR-121 Proof of Payment, ADR-122 Strategic Doctrine v2, now this). A read-only audit of `profit_oracle.py`/`opportunity_pipeline.py`/`strategic_investment_layer()` mapped all 10 named conditions onto what already exists, to avoid building a second, parallel, divergent gate system:

| # | Condition | Real signal | Status before this round |
|---|---|---|---|
| 1 | High commercial value | none | **genuine gap** |
| 2 | Strong Proof of Payment | `_score_payment_evidence()` | already a hard gate (ADR-121) |
| 3 | Low/moderate competition | `_score_competition()` | real, but weighted-only (10%), not a gate |
| 4 | Difficult to copy | `_score_defensibility()` | real, but explicitly informational-only |
| 5 | Premium pricing potential | `butter_price()`/`MIN_LADDER_PROFIT_FLOOR` | already a hard gate, different framing |
| 6 | Global scalability | none independent — `opportunity_pipeline.py` relabels `reusability` | **not a second signal — a duplicate label** |
| 7 | Long-term strategic value | `RECURRING_REVENUE_BY_LADDER`/`REUSABILITY_BY_LADDER` | already a hard gate (ADR-122) |
| 8 | AI significant advantage | `_score_ai_leverage()` | already a hard gate (ADR-122) |
| 9 | Continuous improvement potential | none, anywhere, for any per-opportunity signal | **genuine gap** |
| 10 | High profit margin | `_score_margin()` | real, but weighted-only (10%), not a gate |

`strategic_investment_layer()`'s existing 7-question VC-style synthesis (2026-07-22) was also checked — it recombines the exact same real components (price, defensibility, ai_leverage, recurring, reusability, competition_favorability) into Yes/No/Uncertain questions, but is explicitly informational-only ("لا يُغيّر بوابة القبول/الرفض" — never changes the accept/reject gate) and adds no new real signal beyond what `profit_oracle.py`'s core scoring already computes.

## What was built

**3 new hard gates**, added to `ladder_opportunity_score()` alongside ADR-121/122's existing 4 (Proof of Payment, Pain Severity, Competitive Advantage, Long-Term Strategic Asset — all preserved unchanged, nothing this round loosens any prior gate):

- **Low or Moderate Competition** — `competition_favorability >= 60`, reusing the exact threshold `strategic_investment_layer()`'s own q4 already treats as "favorable enough," not an invented number.
- **Difficult to Copy** — real defensibility level must not be Unknown or "منخفضة" (low). Unknown fails, same "absence of evidence is never a pass" principle as every other gate in this factory.
- **High Profit Margin** — `profit_potential >= 50`, reusing the exact threshold the Competitive Advantage gate already uses.

**"Global Scalability" is deliberately not a fourth new gate** — it is the identical real `reusability` component the Long-Term Strategic Asset gate already checks, cited under its own name in the new `product_strategy` output rather than silently duplicated as a second computation (proven by a dedicated test).

**2 of the 10 conditions stay honestly Unknown, never gated:** "High Commercial Value" and "Continuous Improvement Potential" have no real per-opportunity signal anywhere in this factory today. Fabricating one to gate on would be exactly the invented-market-signal this factory's culture exists to prevent; silently treating Unknown as a pass would be worse than not gating at all. Both are surfaced in the new `product_strategy` result field with an explicit `"answer": "Unknown"` and a real reason, and are excluded from `all_gateable_satisfied`.

A new `product_strategy` dict is returned by `ladder_opportunity_score()` alongside the existing `strategic_doctrine_v2` (kept, unchanged, additive) — the single source of truth for all 10 named conditions' real status. `decision_engine.record_ladder_decision()` now persists both `strategic_doctrine_v2` and `product_strategy` into `evaluation_snapshot` — neither was being persisted before (this function's own docstring already documents 3 prior "computed then dropped" fixes; these are proactive this time, not a 4th reactive one).

## A real architecture gap found and closed: defensibility had no test-isolation seam

Turning defensibility into a hard gate immediately broke 7 tests in `test_ladder_opportunity_score.py` and 11 more across 3 e2e test files — all for the identical reason: `_score_defensibility()` always read the real, shared `data/competitor_database.json`, with no `evidence_path`-style override the way payment evidence has had since ADR-121. In-process tests were fixed with `unittest.mock.patch("profit_oracle._score_defensibility", ...)` (this test file's own existing isolation convention, already used for `butter_price`).

One test (`test_stage_4_factory_loop_gate_agrees_with_the_recorded_decision`, plus `test_factory_loop_golden.js`'s AI-SaaS test) genuinely spawns a real, separate Python subprocess via the JS bridge — an in-process mock can't reach it. This is a real, legitimate gap, not just a test inconvenience: **`_score_defensibility()` gained a real `db_file` parameter**, threaded through `score_opportunity()` → `ladder_opportunity_score()` → the `--ladder-score` CLI handler → `factory_loop.js`'s `getLadderOpportunityScore()` (`competitorDbFile` option) → `market_hunter.hunt_market()`, mirroring `evidence_path`'s exact convention at every layer. Real callers never pass it (falls back to the real shared database exactly as before); the two subprocess-spawning tests now seed an isolated, real-shaped competitor database instead of writing into the shared one.

## A second real bug found: Windows subprocess text decoding

Fixing the above surfaced an unrelated, real, previously-latent bug: `subprocess.run(["node", ...], text=True)` (5 call sites across `test_unified_pipeline_e2e.py` and `test_orchestrator.py`) decodes the child process's stdout using the OS locale's preferred encoding — cp1252 on this Windows machine — instead of the UTF-8 Node.js actually writes. This factory's own real JSON payloads are full of real Arabic-language notes (defensibility, ai_leverage, urgency, and now `product_strategy`); ADR-126's added Arabic text was simply the byte sequence that finally hit it first, not the cause. Fixed by adding `encoding="utf-8"` explicitly to all 5 sites — a real, latent, since-day-one bug closed, not merely worked around.

## Re-scoring the 3 previously-known real opportunities under the full 10-condition checklist

All 3 already fail at Proof of Payment (ADR-121) and independently fail Pain Severity + Competitive Advantage (ADR-122). Re-run against the current, real, unmocked default state (empty competitor database, no external signal):

| Niche | Competition | Difficult to Copy | Premium Pricing | Scalability/Long-term | AI Advantage | Margin |
|---|---|---|---|---|---|---|
| workflow automation system for logistics companies | ✓ | **✗ (Unknown)** | ✓ | ✓ | ✗ | ✓ |
| inventory management system for wholesale distributors | ✓ | **✗ (Unknown)** | ✓ | ✓ | ✗ | ✓ |
| automated invoice processing toolkit for small businesses | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |

New finding: 2 of the 3 also independently fail the new Difficult-to-Copy gate — not because they're genuinely easy to copy, but because zero real competitor research has ever been run for either niche (Unknown, not a confirmed "low" defensibility). All 3 still clear Competition, Premium Pricing, Scalability/Long-term, and Margin comfortably. The real, unchanged bottom line: every one of these 3 needs real Proof-of-Payment evidence and a real AI-leverage-positive reframing before any of this factory's real resources go to it — this round adds detail to *why* they're not yet investable, it does not change *that* they aren't.

## Validation

`test_ladder_opportunity_score.py`: 34/34, including a new `TestGalaxyForgeProductStrategy` class (7 tests) proving each new gate independently, the Unknown-never-gates guarantee, and the scalability-is-not-a-duplicate-signal claim. Full Python suite: 1457/1457 (1450 baseline + 7 new). `test_factory_loop_golden.js`: 56/56. Full CI-equivalent JS suite (`test_metrics.js`, `test_dashboard_data.js`, `test_n8n_notify.js`, `test_api_contract.js`): all green. `node scripts/check_jsonl_duplication.js`, `node -c server.js`, Python `ast.parse` on every touched file: all clean.

## What's deliberately not done

- No fabricated signal for "High Commercial Value" or "Continuous Improvement Potential" — honestly Unknown until a real per-opportunity data source exists for either.
- No retroactive edit to any already-produced opportunity's historical decision record.
- No change to `strategic_investment_layer()` — its own richer, Uncertain-aware synthesis stays informational-only, unaffected by this round's new hard gates, same reasoning ADR-122 already gave for leaving it alone.
