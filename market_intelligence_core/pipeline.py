"""
Market Intelligence Core — plugin pipeline (ADR-049).

Runs every registered primary scorer, then every registered meta scorer
(which additionally receive the primary results) — both sets are
auto-discovered via scoring/__init__.py's pkgutil import, so a new
scoring dimension needs zero edits here.
"""

from market_intelligence_core import scoring  # noqa: F401 — import triggers auto-registration
from market_intelligence_core.registry import get_meta_scorers, get_scorers


def run(context):
    scores = {}
    for name, fn in get_scorers().items():
        scores[name] = fn(context)

    for name, fn in get_meta_scorers().items():
        scores[name] = fn(context, scores)

    return scores
