# ADR-122 — Strategic Doctrine v2: the 4-Condition Decision Hierarchy

**Date:** 2026-07-24
**Status:** Adopted.

---

## The directive

Founder decision: Proof of Payment (ADR-121) is a permanent first-level filter but "NOT sufficient by itself." Galaxy Forge approves opportunities only when ALL four conditions are satisfied, checked in this exact order:

1. **Real Proof of Payment** — real subscriptions, invoices, procurement records, enterprise budgets, job postings, or validated purchasing behavior. Never search volume or theoretical demand alone.
2. **Pain Severity** — expensive, recurring, time-consuming, or business-critical; prefer problems touching revenue, cost, productivity, compliance, or decision-making.
3. **Competitive Advantage** — Galaxy Forge must be able to build a meaningfully better solution: faster, cheaper, simpler, more automated, AI-enhanced, or uniquely differentiated.
4. **Long-Term Strategic Asset** — should preferably become a SaaS/recurring subscription/AI platform/enterprise software/proprietary dataset/API/automation infrastructure/hard-to-copy digital asset.

"If any of these four conditions fail, the opportunity must not receive top priority regardless of market size."

## What real infrastructure this was built on

Audited before writing any code (same discipline as ADR-121): this factory already had real, if disconnected or under-weighted, machinery for 3 of the 4 conditions.

- **Condition 2 (Pain Severity):** `profit_oracle._score_urgency()` already existed, real and correctly designed — it reads `external_signal["customer_pain"]["pain_language_hits"]`/`["willingness_to_pay_hits"]` and computes a real score. It was simply never fed: nothing in the real call chain ever passed real customer-pain data in. The real feed exists too — `market_intelligence_engine.analyze_customer_pain()` queries real GitHub Issues, Hacker News, and Stack Overflow and returns exactly the `pain_language_hits`/`willingness_to_pay_hits` counts `_score_urgency()` expects, under `real_evidence`. The wire between them was never built until now.
- **Condition 3 (Competitive Advantage):** `profit_oracle._score_ai_leverage()` already existed — a real, deterministic keyword classification of the niche's own text against 19 AI-suitable-task keywords and 11 physical/real-time-task keywords. Unlike the other three conditions, this needs zero external evidence-gathering — it's always computable from the niche string itself.
- **Condition 4 (Long-Term Strategic Asset):** `RECURRING_REVENUE_BY_LADDER`/`REUSABILITY_BY_LADDER` — real, already-documented, ladder-grounded constants (MASTER_CHARTER.md §2) that were already driving `ladder_score` itself, just never used as an explicit accept/reject gate.

**A deliberate architectural constraint respected, not overridden:** `_score_defensibility()`/`_score_market_signal()` already established a real principle in this exact file — scoring functions never trigger a live external query themselves; live data is gathered separately and passed in. `analyze_customer_pain()` makes 3 real network calls (GitHub + HN + Stack Overflow). Auto-wiring it into every `hunt_market()` candidate would mean ~30 real external API calls per hunt (10 seed niches × 3 sources) — a real, meaningful change to this factory's operational/rate-limit profile that was not asked for. `ladder_opportunity_score()` therefore never gathers pain evidence itself; a caller who has already computed it for a specific niche passes it in via `external_signal`, exactly the pattern already established for competitor/market-signal data.

## What was built

`profit_oracle.ladder_opportunity_score()` gained 3 new hard gates, chained after Proof of Payment in the founder's own hierarchy order, ANY of which independently rejects regardless of the weighted score or the other gates:

- **Pain Severity gate:** `has_pain_evidence = urgency_score is not None and urgency_score >= 25` — real evidence must exist AND clear the same floor `_score_urgency()`'s own level bands already use to call a signal "medium" rather than "low."
- **Competitive Advantage gate:** `has_competitive_advantage = ai_leverage_score is not None and ai_leverage_score >= 50` — net-positive real AI-leverage signal (at least as many real AI-suitable keyword hits as physical-task hits).
- **Long-Term Strategic Asset gate:** `is_durable_strategic_asset = recurring_revenue_potential >= 55 and reusability >= 55` — both real, ladder-derived constants; only `ai_saas`/`b2b_systems`/`automation_tools` clear this today (`reusable_assets` fails on recurring=20; `educational`/`kdp_books` fail both).

Absence of real evidence is never a pass for gates 1–3, same principle as every other honesty gate in this factory. A new `strategic_doctrine_v2` dict is returned on every result: `{proof_of_payment, pain_severity, competitive_advantage, long_term_strategic_asset, all_4_satisfied}` — the single source of truth for which conditions a niche actually cleared, never re-derived elsewhere.

`market_hunter.hunt_market()` and `factory_loop.js`'s `getLadderOpportunityScore()` both gained an `external_signal`/`externalSignal` passthrough alongside the existing `evidence_path`/`evidencePath` one — real callers omit both and get the real defaults (real ledger, no auto-gathered pain evidence).

## Real regression impact — 12 more tests broke, fixed the same honest way

12 tests across `test_automation_systems_e2e.py`, `test_master_cycle_production_e2e.py`, and `test_unified_pipeline_e2e.py` broke immediately — every one assumed acceptance without pain evidence or without verifying AI-leverage keyword coverage. Fixed by:
- Seeding real pain-evidence `external_signal` dicts into every call that needs to prove acceptance (never bypassing the gate).
- **Correcting two test fixture niches that genuinely failed Competitive Advantage on their own real merits**, not by accident: `test_automation_systems_e2e.py`'s niche mixed a real HIGH keyword ("compliance") with a real LOW keyword ("logistics"), netting 45/100 — below the 50 floor. Swapped "logistics firms" → "professional services firms" and added "reporting" (another real HIGH hit), netting 90/100. The shared `SYNTHETIC_NICHE` fixture (introduced this same session to fix the Proof of Payment collision) similarly had zero AI-leverage keyword matches at all — added "reporting."

New `TestStrategicDoctrineV2` class (7 tests) in `test_ladder_opportunity_score.py` proves each of the 3 new gates independently — a niche/ladder engineered to pass every other gate still rejects on exactly the one gate under test.

## Re-scoring the 3 real ACCEPTED opportunities under the full 4-condition hierarchy

| Niche | Ladder | Proof of Payment | Pain Severity | Competitive Advantage | Long-Term Asset |
|---|---|---|---|---|---|
| workflow automation system for logistics companies | b2b_systems | ✗ | ✗ | **✗ (real, on its own merits — "logistics" is a real AI_LEVERAGE_LOW_KEYWORDS hit)** | ✓ |
| inventory management system for wholesale distributors | b2b_systems | ✗ | ✗ | ✗ (Unknown — no AI-leverage keyword match either way) | ✓ |
| automated invoice processing toolkit for small businesses | automation_tools | ✗ | ✗ | ✗ (Unknown) | ✓ |

All 3 already failed Proof of Payment alone (ADR-121). Under the full v2 hierarchy, **all 3 also independently fail both Pain Severity (no real evidence ever gathered) and Competitive Advantage** — one genuinely on its own real text (a logistics-flavored niche scoring net-negative on AI-leverage, not an evidence gap), the other two on missing evidence (Unknown, never queried). Only Long-Term Strategic Asset passes for all 3, since `b2b_systems`/`automation_tools` are real durable-asset ladders. Full detail in ADR-121's own re-score table for the Proof of Payment dimension specifically.

## What's deliberately not done

- No automatic per-candidate pain-evidence gathering inside `hunt_market()` — would add ~30 real external API calls per hunt, a real operational cost/rate-limit change not authorized here. A real caller can gather it explicitly for a specific niche via `analyze_customer_pain()` and pass it in, same manual-but-real pattern as Proof of Payment evidence.
- No change to `strategic_investment_layer()` — its own richer, Uncertain-aware synthesis (7 Yes/No/Uncertain questions) stays informational-only; the new hard gate uses the simpler, always-available `recurring_revenue_potential`/`reusability` constants directly rather than depending on `strategic_investment_layer()`'s cache-dependent `defensibility` chain, which would make the gate fail-Unknown for most un-cached niches.
- No retroactive edit to any already-produced opportunity's historical decision record.
