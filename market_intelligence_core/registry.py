"""
Market Intelligence Core — plugin scorer registry (ADR-049).

A scoring module registers itself by decorating its compute() function;
scoring/__init__.py auto-imports every module in that package at import
time (via pkgutil), which runs the decorator and populates the registry
below. Adding a new scoring dimension means adding one new file under
scoring/ — zero edits to this file, to pipeline.py, or to any existing
scorer. This is the actual mechanism behind the requirement "the
pipeline must allow adding future scoring modules without modifying
existing ones."
"""

from typing import Callable, Dict

_SCORERS: Dict[str, Callable] = {}
_META_SCORERS: Dict[str, Callable] = {}


def register_scorer(name):
    """Primary scorer: receives only an EvaluationContext, returns a Score.
    Order-independent — every primary scorer runs once per pipeline.run()."""
    def decorator(fn):
        _SCORERS[name] = fn
        return fn
    return decorator


def register_meta_scorer(name):
    """Meta scorer: runs after every primary scorer has already run.
    Receives (context, scores) where `scores` is the dict of every
    primary Score already computed — e.g. confidence.py, which averages
    every other dimension's own .confidence and so must run last."""
    def decorator(fn):
        _META_SCORERS[name] = fn
        return fn
    return decorator


def get_scorers():
    return dict(_SCORERS)


def get_meta_scorers():
    return dict(_META_SCORERS)
