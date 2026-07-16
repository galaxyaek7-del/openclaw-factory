"""
Multi-Source Market Intelligence — plugin connector registry (ADR-059).

Same pattern proven repeatedly this session (market_intelligence_core,
orchestrator): a connector registers itself by decorating its check()
function; connectors/__init__.py auto-imports every module in that
package via pkgutil, so a new source is one new file — zero edits here.
"""

from typing import Callable, Dict

_CONNECTORS: Dict[str, Callable] = {}


def register_connector(name):
    def decorator(fn):
        _CONNECTORS[name] = fn
        return fn
    return decorator


def get_connectors():
    return dict(_CONNECTORS)
