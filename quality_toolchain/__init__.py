# -*- coding: utf-8 -*-
"""Galaxy Forge QUALITY TOOLCHAIN.

A modular, product-aware QA tool registry/config/adapter/benchmark layer per
the founder directive. It never claims a tool improves quality until an actual
factory benchmark demonstrates it, and a failing/disabled tool never becomes a
silent quality PASS.

Public API:
    registry  (stack selection, tool config, availability)
    runner    (run_stack / run_gate against product text)
    evidence  (append-only tool-invocation evidence)
    versions  (OBSERVED version/capability fingerprint)
    gate      (timeout + fail-closed normalization)
    adapters  (isolated per-tool wrappers)
"""

from . import (  # noqa: F401
    adapters,
    evidence,
    gate,
    registry,
    runner,
    versions,
)

__all__ = ["adapters", "evidence", "gate", "registry", "runner", "versions"]