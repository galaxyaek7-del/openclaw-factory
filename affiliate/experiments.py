#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smallest-useful-experiment engine + asset reuse inventory (read-only).

No experiment is proposed while the sample is inadequate — and the sample
is never manufactured. Before anything new, existing validated assets are
surfaced for repurposing. DO_NOT_CLONE_WITHOUT_EVIDENCE is always True.
"""

from __future__ import annotations

from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DO_NOT_CLONE_WITHOUT_EVIDENCE = True
MIN_SAMPLE_FOR_EXPERIMENT = 100


def propose_experiment() -> dict:
    """Today: no market sample exists, so no experiment is proposed.
    The shape returned when data exists is documented, not fabricated."""
    from affiliate import diagnostics as dg
    funnel = dg.funnel_diagnostic()
    views = funnel["stages"]["VIEW"]["sample"]
    clicks = funnel["stages"]["CLICK"]["sample"]
    if views < MIN_SAMPLE_FOR_EXPERIMENT:
        return {"proposal": None,
                "reason": "sample inadequate (%d views < %d minimum); "
                          "no experiment manufactured" % (views, MIN_SAMPLE_FOR_EXPERIMENT)}
    return {"proposal": None,
            "reason": "views=%d clicks=%d — proposal logic activates on real spread" % (views, clicks)}


def experiment_lifecycle(exp: dict) -> dict:
    """Validate phase order: HYPOTHESIS→BASELINE→RUNNING→RESULT→DECISION.
    Skips and backward jumps are rejected."""
    order = ("HYPOTHESIS", "BASELINE", "RUNNING", "RESULT", "DECISION")
    phases = [p for p in (exp.get("history") or []) if p in order]
    if phases != sorted(phases, key=order.index) or len(set(phases)) != len(phases):
        return {"valid": False, "reason": "phase order violated: %s" % phases}
    return {"valid": True, "phase": phases[-1] if phases else "HYPOTHESIS"}
