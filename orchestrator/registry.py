"""
Executive Orchestrator — plugin engine registry (ADR-051).

Same pattern already proven twice this session (market_intelligence_core/
registry.py, decision_engine's own module boundaries): an engine adapter
registers itself by decorating its run() function; engines/__init__.py
auto-imports every module in that package via pkgutil at import time, so
a new engine is one new file — zero edits to this file, to
orchestrator.py, or to any existing engine adapter (the literal mechanism
behind "allow new engines to register automatically without modifying
existing code").

Every engine adapter has the same shape — run(context: dict) -> dict —
which is the dependency-inversion boundary: the Orchestrator depends on
this one abstract shape, never on any concrete engine's internals
directly. Loose coupling between engines follows from the same rule:
an adapter reads whatever it needs from `context`, nothing reaches into
another adapter's module directly.
"""

from typing import Callable, Dict

_ENGINES: Dict[str, Callable] = {}


def register_engine(name):
    def decorator(fn):
        _ENGINES[name] = fn
        return fn
    return decorator


def get_engines():
    return dict(_ENGINES)
