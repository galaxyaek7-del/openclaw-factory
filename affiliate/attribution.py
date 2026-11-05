#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate attribution classifier + program synergy mapper (read-only).

Attribution: every click row classified ATTRIBUTED / PARTIALLY_ATTRIBUTED /
UNATTRIBUTED / UNKNOWN. All 24 recorded clicks are null-referrer internal
bursts -> UNATTRIBUTED (quarantined, never commercial).
Synergy: program <-> Galaxy Forge asset matches with rationale; customer
utility first — a match never reshapes the product recommendation."""

from __future__ import annotations

from affiliate import signals as sig


def classify_clicks(rows: list) -> dict:
    out = {"ATTRIBUTED": 0, "PARTIALLY_ATTRIBUTED": 0, "UNATTRIBUTED": 0, "UNKNOWN": 0}
    for r in rows:
        if not isinstance(r, dict):
            out["UNKNOWN"] += 1
            continue
        c = sig.classify_signal({"kind": "click",
                                 "referrer": r.get("referrer"),
                                 "note": r.get("note", "")})
        cat = c["category"]
        if cat == "EXTERNAL_CLICK" and r.get("referrer"):
            out["ATTRIBUTED"] += 1
        elif cat == "EXTERNAL_CLICK":
            out["PARTIALLY_ATTRIBUTED"] += 1
        else:
            # INTERNAL_TEST_SIGNAL and UNCLASSIFIED alike: no usable
            # attribution path (null referrer, no external source) —
            # quarantined from anything commercial.
            out["UNATTRIBUTED"] += 1
    return out


SYNERGIES = [
    {"program": "SYSTEME_DIRECT (SYSTEME_AFFILIATE_ID in env; not a portfolio program)",
     "asset": "AST-SYSTEME-VIDEO-01",
     "rationale": "video teaches the tool; tool link is the honest next step",
     "distortion_risk": "LOW (editorial independence kept; video useful without purchase)"},
    {"program": "CO-amazon-affiliate", "asset": "books/* (physical-goods kits)",
     "rationale": "kits cite tools/materials readers must buy anyway",
     "distortion_risk": "MEDIUM (recommendations must stay evidence-picked, never commission-picked)"},
    {"program": "CO-etsy-affiliate", "asset": "AST-MEDIUM-GPSR-01",
     "rationale": "Etsy-seller audience overlap",
     "distortion_risk": "MEDIUM (same independence rule)"},
]


def synergy_for(asset_id: str) -> list:
    return [s for s in SYNERGIES if s["asset"] == asset_id or s["asset"].startswith("books/")]
