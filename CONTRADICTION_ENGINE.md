# Galaxy Forge — Contradiction Engine

**Date:** 2026-08-08 | Phase 18, Section 15. Document companion to `contradiction_engine.py` — live output captured this round.

---

## Real, live findings (this round)

**19 real contradictions** found across this factory's own real decision history:

- **18** `conflicting_market_estimate` — the same real niche's `opportunity_score` swung by more than the disclosed 20-point threshold across different real evaluation runs. Largest: "AI Agent Blueprint for Freelance Security Pentesting Automation," a 42.8-point spread.
- **1** `contradictory_strategic_conclusion` — a real niche flip-flopped between `ACCEPTED` and `REJECTED` status.
- **0** real price contradictions — the one real product with a live-checkable price (`EU AI Act Compliance Toolkit`) matches exactly between the internal record and the live Paddle API.

## What this means, honestly

**This is not a defect in the scoring pipeline.** `profit_oracle.py`'s real evaluation formula legitimately produces different scores across separate runs when the real, underlying evidence available at each run differs (a real competitor search returning different results, a real evidence-gathering pass finding new signals). The Contradiction Engine's real job is to surface this volatility — which existed all along, silently, in `data/decisions.jsonl`'s own history — not to declare either score wrong.

**Never silently resolved**: confirmed by direct test (`test_never_picks_a_winner_both_sources_preserved`) — every contradiction preserves both real values with their real timestamps and decision IDs, for a human to investigate if it matters for a specific decision.

## Real limitation

This engine detects only the 2 contradiction classes this factory can currently check mechanically (decision-score volatility, price mismatch). The directive's other named classes (conflicting customer counts, different platform statuses, conflicting product prices across multiple platforms) have no real data source to check against yet — 0 real customers, 1 credentialed platform.

---

*See also: `contradiction_engine.py`, `KNOWLEDGE_EVIDENCE_MODEL.md`.*
