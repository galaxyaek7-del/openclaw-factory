"""
OpenClaw Factory — Golden Opportunity Hunter (ADR-060).

Not infrastructure. This phase's explicit instruction: stop building
architecture, find real opportunities using what already exists. Every
computation here is reused, never re-derived:

  evidence_package.py   builds the 9-field opportunity package entirely
                         from a Decision's already-computed
                         evaluation_snapshot (market_intelligence_core,
                         ADR-049) — zero new scoring. The only two
                         genuinely new fields (implementation difficulty,
                         "why now") are simple, evidence-cited labels
                         derived from fields that already exist in that
                         snapshot, not new calculations.

  hunt.py                reuses real_world_mode.signal_intake (ADR-056)
                         for "continuously monitor every available
                         evidence source" (OPPORTUNITIES.md and
                         tier1_intake/candidates/ are re-read fresh every
                         call — always current, no stale cache), reuses
                         orchestrator.run_cycle() (ADR-051) with
                         execute_production hardcoded False — never a
                         parameter, never exposed, never True anywhere
                         in this module — and reuses decision_engine.
                         ranking.rank_all() (ADR-050) for the prioritized
                         queue, which already ranks by opportunity_score
                         (demand + competition + profit + automation
                         potential + long-term value combined), not raw
                         popularity/demand alone.

"Never recommend production automatically" is a structural guarantee
here, not a convention: run_hunt() has no execute_production parameter
at all, and a dedicated test reads this package's own source to confirm
the literal "execute_production=True" never appears anywhere in it.
"""
