# ADR-121 — Proof of Payment Doctrine

**Date:** 2026-07-24
**Status:** Adopted.

---

## The directive

Founder decision: upgrade `market_hunter.py` and `profit_oracle.ladder_opportunity_score()` to weight **evidence of existing spend** above inferred demand. New highest-weight signals: (1) competitors actually selling with complaining reviews, (2) paid job postings for tasks that could be automated, (3) agencies/freelancers charging money for the manual version, (4) existing subscriptions users are trying to replace or escape. Score any opportunity with real payment evidence far above one based only on desk-researched pain. Add a `payment_evidence` field to every opportunity — with the actual source URL/quote — and reject as UNPROVEN any opportunity with none.

## What real infrastructure this was built on

Before writing any code, this factory's existing evidence/scoring infrastructure was audited (not assumed):

- `market_evidence.py`'s **Market Evidence Ledger** already existed (ADR-088) — a real, working, JSONL-backed store with 24 event categories, and one real precedent worth copying exactly: `COMPETITOR_EVENT_TYPES` (Market Evidence & Alerting layer, 2026-07-23) already refuses to record an uncited claim about a third party (requires `competitor` + `source_url`, raises `ValueError` otherwise). This is the same fabrication-risk category as the founder's 4 new signals — a claim about something outside this factory's own first-hand experience — so the new `PAYMENT_EVIDENCE_EVENT_TYPES` reuse the identical enforcement pattern (`source_url` + `quote` required).
- **Confirmed, and this matters:** the ledger has been recording evidence since 2026-07-22 and **zero events of any kind have ever been recorded** (`find data -iname "*evidence*"` → no files existed until this session). Whatever this doctrine does to today's real ACCEPTED opportunities, it does so against a genuinely empty evidence store, not a stocked one.
- **Confirmed, and this bounds the doctrine's honest scope:** no real connector exists anywhere in this factory for review sites (G2, Trustpilot, Capterra, Amazon reviews), job boards (Indeed, LinkedIn Jobs, Upwork job postings), freelance marketplaces (Upwork/Fiverr gig pricing), or subscription-churn signals. The only real external connectors in this factory are Hacker News (top stories + Algolia search) and GitHub (issue/repo search), per CLAUDE.md's own 2026-07-23 finding. Building a connector that pretends to read real reviews/job-postings/freelancer-rates when none exists would be exactly the kind of fabrication this factory's entire engineering discipline has refused everywhere else.

**Consequence, stated plainly:** this doctrine is real, working, and enforced — but recording a payment-evidence event today requires a human (or Claude Code, checking a real public page during a session) to actually find one and cite it, exactly the same manual-observation discipline every one of the ledger's other 21 categories already had. No opportunity will pass this gate automatically until someone does that.

## What was built

1. **`market_evidence.py`**: `PAYMENT_EVIDENCE_EVENT_TYPES = ("complaining_review", "paid_job_posting", "freelancer_agency_pricing", "subscription_escape")`, added to `EVENT_TYPES`. `record_evidence()` now refuses (raises `ValueError`) any of these four without both `source_url` and `quote` in `payload` — same discipline as the competitor-event gate, scoped only to these four types; the pre-existing 15 (+9 competitor) categories are completely unaffected. New `get_payment_evidence(niche, evidence_path=None)` helper; `summarize_niche()` now additively includes a `payment_evidence` key.

2. **`profit_oracle.ladder_opportunity_score()`** — reweighted and given a new hard gate:
   - New component `payment_evidence_score`: 0 with no real evidence, 40 with one real citation, 70 with two, 100 with three or more — real evidence, never inferred or estimated from keywords.
   - New weights: `0.35 payment_evidence_score + 0.10 market_demand + 0.10 competition_favorability + 0.10 profit_potential + 0.15 recurring_revenue_potential + 0.20 reusability` (previously `0.15/0.15/0.15/0.25/0.30` with no payment-evidence term). Payment evidence is now the single highest-weighted factor, and demand dropped from 0.15 to 0.10 — the founder's literal instruction ("weight evidence of existing spend above inferred demand").
   - New hard gate, checked **before** the price floor and score floor: `accepted = has_payment_evidence and clears_score_floor and clears_profit_floor`. Zero real citations means `accepted=False` and `reason` explicitly says `UNPROVEN`, regardless of how high the ladder_score or price would otherwise be. This is an absolute gate, not a scoring nudge — a niche can score 100/100 on every keyword-inferred dimension and still be rejected as unproven.
   - New `payment_evidence` field on every returned result: the actual recorded evidence for that niche, each entry carrying its real `event_type`, `source_url`, `quote`, and `recorded_at` — never a summary, never a count standing in for the citation itself.
   - New `evidence_path=None` parameter, same test-isolation convention as every other stateful path in this factory; real callers (market_hunter.py, the CLI, the JS bridge) omit it and hit the real `data/market_evidence.jsonl`.

3. **`market_hunter.hunt_market()`**: gained the same `evidence_path=None` override and threads it into its one `ladder_opportunity_score()` call — a real hunt now automatically inherits the new doctrine with zero further wiring, since it already called this function.

4. **`decision_engine.engine.record_ladder_decision()`**: now persists `payment_evidence` into `evaluation_snapshot` — this field was computed and silently discarded before persisting, the exact "real data computed then thrown away" pattern this same function's own comment history had already been fixed for three times; fixed proactively this time rather than left for a fourth discovery.

5. **`factory_loop.js`'s `getLadderOpportunityScore()`** and **`profit_oracle.py`'s `--ladder-score` CLI**: gained an optional `evidencePath`/`evidence_path` passthrough (test isolation only; a real call from the automatic tick never sets it).

## Real regression impact — 13 tests broke, and why that's expected

Applying a hard "reject as UNPROVEN with zero evidence" gate to a function called pervasively across this factory's test suite broke 13 existing tests the moment it shipped, across `test_ladder_opportunity_score.py`, `test_opportunity_score.py`, `test_automation_systems_e2e.py`, `test_master_cycle_production_e2e.py`, and `test_unified_pipeline_e2e.py`. Every one of these tests previously assumed a fixture niche would be `accepted=True` purely from keyword-inferred scoring — exactly the assumption this doctrine exists to remove. Each was fixed the honest way: by recording real-shaped (test-fixture) evidence citations into that test's own isolated ledger via the real `record_evidence()` function, so the test still exercises real acceptance logic rather than bypassing the new gate. `test_opportunity_score.py`'s literal weight-formula assertion was updated to the new documented weights. None of the 13 were worked around by weakening the gate itself.

## Re-scoring the 3 real ACCEPTED opportunities under the new doctrine

The 3 real opportunities this factory has ever accepted (`workflow automation system for logistics companies`, `inventory management system for wholesale distributors`, `automated invoice processing toolkit for small businesses`, all decided 2026-07-22) were re-scored against the real, current `data/market_evidence.jsonl` — which, confirmed above, has never had a single event recorded for any niche, ever.

**Result: all 3 flip from ACCEPTED to REJECTED — UNPROVEN — under the new doctrine.** This is not a bug and not softened here: it is the real, honest consequence of a real doctrine applied to a real, empty evidence store. Every one of these 3 opportunities was accepted under the old doctrine on keyword-inferred demand/competition/margin signals alone — precisely the kind of "desk-researched pain" evidence this doctrine now refuses to accept as sufficient on its own. Two of the three have already been produced and dry-run-published to Paddle (per this session's own separate live-cycle verification of the third) — that real production history is untouched by this ADR; nothing already produced is unpublished or reverted. What changes is that none of the three would be accepted for a *new* production decision today without a human going and finding a real, citable review, job posting, freelancer rate, or subscription complaint for one of them first.

## What's deliberately not done

- No automated connector for review sites, job boards, freelance marketplaces, or subscription-churn signals — confirmed none exist, none fabricated. Building one is a real, separately-scoped future project, not attempted here.
- No automatic population of `PAYMENT_EVIDENCE_EVENT_TYPES` from the real HN/GitHub connectors that do exist (`market_intelligence_engine.analyze_customer_pain()` already discards the real matching issue/thread URLs it fetches — a real, disclosed, pre-existing gap found during this round's audit, not fixed here since it's adjacent to, not required by, today's directive). A real, worthwhile fast-follow if the founder wants it.
- No retroactive edit to the 2 already-produced/dry-run-published opportunities' own historical decision records — they stay as they were decided, same historical-accuracy principle as ADR-120's ADR-preservation policy.
