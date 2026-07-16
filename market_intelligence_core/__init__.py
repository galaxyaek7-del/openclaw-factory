"""
OpenClaw Factory — Market Intelligence Core (ADR-049).

The permanent, canonical entrypoint for opportunity evaluation — see
market_intelligence_core.core.evaluate_opportunity() for the single
public API most callers need. Independent scoring dimensions live under
market_intelligence_core/scoring/, each testable in isolation.

Deliberately empty of imports here (beyond this docstring): core.py and
pipeline.py depend on profit_oracle.py/market_intelligence_engine.py/
competitor_discovery.py, and those in turn depend on this package's
http_client submodule — importing core/pipeline eagerly at package
level would create an import-order hazard. Every submodule is imported
explicitly by whoever needs it instead.
"""
