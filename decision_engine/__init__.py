"""
Galaxy Forge — Opportunity Decision Engine (ADR-050).

The permanent Decision Brain: consumes market_intelligence_core.
evaluate_opportunity() as one input among the real signals this factory
already has, ranks every opportunity globally, keeps an append-only
Decision Queue, and closes the loop with real sales once they exist.

Signal -> Evaluation -> Decision -> Execution -> Feedback -> Learning:
  Signal      a niche/opportunity someone wants evaluated
  Evaluation  market_intelligence_core.evaluate_opportunity() (unchanged)
  Decision    engine.evaluate_and_decide() — this package
  Execution   book_generator.py / distributor.py (untouched, out of scope)
  Feedback    feedback.py — reads real data/sales_ledger.jsonl
  Learning    learning.py — real prediction-accuracy + recalibration report

Deliberately not wired into server.js or factory_loop.js's live tick —
same "standalone tool, run deliberately" convention this factory already
uses for market_hunter.py/competitor_discovery.py/market_intelligence_engine.py.
"""
