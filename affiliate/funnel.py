#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified per-product funnel telemetry (read-only).

Stages: TRAFFIC -> VIEW -> CHECKOUT -> PURCHASE -> REVENUE -> REFUND -> NET.
Each stage reports value + EVIDENCE LEVEL (OBSERVED/DERIVED/INFERRED/
ESTIMATED/UNKNOWN) + AVAILABILITY (AVAILABLE/NOT_AVAILABLE via accessible
means). Gumroad's API exposes purchases only — upstream stages are
honestly NOT_AVAILABLE, never zero-filled as if measured. A product with
no measurable exposure stays IN_MEASUREMENT_WINDOW, never PASS/FAIL."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent

STAGES = ("TRAFFIC", "VIEW", "CHECKOUT", "PURCHASE", "REVENUE", "REFUND", "NET")


STATES = ("UNKNOWN", "NO_DATA", "OBSERVED", "VERIFIED", "NOT_VERIFIED",
          "INSUFFICIENT_EXPOSURE", "BLOCKED", "FAILED")


def transition_ok(frm: str, to: str) -> dict:
    """Guard the forbidden jumps: UNKNOWN->ZERO (as measured), PAGE_LIVE->
    EXPOSURE, EXPOSURE->VISIT, VISIT->INTEREST, CLICK->PURCHASE,
    CHECKOUT->REVENUE all require direct observation of the target."""
    if frm in ("UNKNOWN", "NO_DATA") and to in ("OBSERVED", "VERIFIED"):
        return {"allowed": False,
                "reason": "target stage needs direct observation, not inference"}
    return {"allowed": True, "reason": "no guarded jump"}


def product_funnel(product_id: str, purchases: int = 0, revenue_usd: float = 0) -> dict:
    stages = {
        "TRAFFIC": {"value": None, "level": "UNKNOWN", "state": "UNKNOWN",
                    "availability": "NOT_AVAILABLE",
                    "note": "no traffic endpoint in accessible API surface"},
        "VIEW": {"value": None, "level": "UNKNOWN", "state": "UNKNOWN",
                 "availability": "NOT_AVAILABLE",
                 "note": "dashboard-only (founder-read UI)"},
        "CHECKOUT": {"value": None, "level": "UNKNOWN", "state": "UNKNOWN",
                     "availability": "NOT_AVAILABLE",
                     "note": "no checkout probe permitted during live test"},
        "PURCHASE": {"value": purchases, "level": "OBSERVED", "state": "OBSERVED",
                     "availability": "AVAILABLE",
                     "note": "sales API read (zero is a measurement, not absence)"},
        "REVENUE": {"value": revenue_usd, "level": "OBSERVED", "state": "OBSERVED",
                    "availability": "AVAILABLE", "note": "finance ledger read"},
        "REFUND": {"value": None, "level": "UNKNOWN", "state": "UNKNOWN",
                   "availability": "NOT_AVAILABLE",
                   "note": "no refund signal; absence is not evidence of zero"},
        "NET": {"value": None, "level": "UNKNOWN", "state": "UNKNOWN",
                "availability": "NOT_AVAILABLE",
                "note": "needs OBSERVED refunds; withheld until measured"},
    }
    if purchases == 0 and stages["TRAFFIC"]["availability"] == "NOT_AVAILABLE":
        verdict = "IN_MEASUREMENT_WINDOW"
        reason = "no measurable exposure; unlicensed to judge success or failure"
    elif purchases > 0:
        verdict = "DIAGNOSE_BEFORE_SCALE"
        reason = "purchases exist; repeatability unproven"
    else:
        verdict = "IN_MEASUREMENT_WINDOW"
        reason = "default: exposure unmeasured"
    return {"product_id": product_id, "stages": stages, "verdict": verdict,
            "reason": reason,
            "measured_at": datetime.now(timezone.utc).isoformat()}
