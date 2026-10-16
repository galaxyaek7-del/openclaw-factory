#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regulatory pipeline: CHANGE -> BUYER -> OBLIGATION -> PAIN -> NEED ->
SOLUTION -> VALIDATION. Framework + GPSR reference implementation (the one
regulation with first-hand factory evidence). New regulations enter only
with cited sources + dates, never from headlines alone."""

from __future__ import annotations

PIPELINE = ("CHANGE", "BUYER", "OBLIGATION", "PAIN", "NEED", "SOLUTION", "VALIDATION")

REFERENCE = {
    "regulation": "GPSR Regulation (EU) 2023/988",
    "CHANGE": "general product-safety net incl. online sales; applicable since 2024-12-13 (OBSERVED, EC)",
    "BUYER": "non-EU sellers to EU + EU SMB physical sellers (DERIVED, 17/20 sample)",
    "OBLIGATION": "RP mandate (non-EU) / file+risk+labels (all sellers) (OBSERVED, EC scope)",
    "PAIN": "listing removal + doc burden (OBSERVED docs; per-company pain UNOBSERVED)",
    "NEED": "DIY documentation route vs consultant invoices (DERIVED)",
    "SOLUTION": "GPSR kit $79 live (OBSERVED); EU-role gap specified (DERIVED)",
    "VALIDATION": "IN_MEASUREMENT_WINDOW (0 sales; exposure UNKNOWN)",
    "sources": ["EC factsheet 2023-07", "EUR-Lex guidance", "checked 2026-09-21"],
}


def evaluate(change: dict) -> dict:
    """Score a candidate regulation through the pipeline. Missing stages
    stay UNKNOWN; a chain with UNKNOWN pain or buyer can only HOLD."""
    stages = {s: (change.get(s) or "UNKNOWN") for s in PIPELINE}
    unknown = [s for s, v in stages.items() if v == "UNKNOWN"]
    if unknown:
        return {"decision": "HOLD", "stages": stages,
                "reason": "unknown at: %s" % ", ".join(unknown)}
    return {"decision": "RESEARCH_MORE", "stages": stages,
            "reason": "complete chain still needs buyer evidence before TEST"}
