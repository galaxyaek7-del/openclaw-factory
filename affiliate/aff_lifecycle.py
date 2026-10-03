#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate funnel lifecycle with evidence gates (read-only).

PROGRAM_DISCOVERED -> VERIFIED -> OFFER_QUALIFIED -> LINK_GENERATED ->
DISTRIBUTION_READY -> CLICK_OBSERVED -> CONVERSION_OBSERVED ->
COMMISSION_PENDING -> CONFIRMED -> PAYOUT_CONFIRMED -> LEARNED.
A program advances only on its own evidence; absence parks it, never
scores it forward. Clicks are never commissions; pending is never paid."""

from __future__ import annotations

FUNNEL = ("PROGRAM_DISCOVERED", "PROGRAM_VERIFIED", "OFFER_QUALIFIED",
          "LINK_GENERATED", "DISTRIBUTION_READY", "CLICK_OBSERVED",
          "CONVERSION_OBSERVED", "COMMISSION_PENDING", "COMMISSION_CONFIRMED",
          "PAYOUT_CONFIRMED", "LEARNED")


def stage_of(program: dict, links: int = 0, clicks: int = 0,
             conversions: int = 0, commissions: int = 0,
             payouts: int = 0) -> dict:
    """Derive funnel stage from real counts + verification fields."""
    fields = (program.get("record") or {}).get("fields", {})
    verified = (fields.get("verification_status") or {}).get("value") == "VERIFIED"
    scoring = (program.get("scoring") or {}).get("category", "")
    if payouts > 0:
        stage, why = "PAYOUT_CONFIRMED", "payout rows observed"
    elif commissions > 0:
        stage, why = "COMMISSION_CONFIRMED", "commission rows observed"
    elif conversions > 0:
        stage, why = "CONVERSION_OBSERVED", "conversion rows observed"
    elif clicks > 0:
        stage, why = "CLICK_OBSERVED", "external attributed clicks observed"
    elif links > 0:
        stage, why = "DISTRIBUTION_READY", "registered links exist"
    elif scoring in ("PROMISING", "QUALIFIED", "APPROVED"):
        stage, why = "OFFER_QUALIFIED", "internal scoring %s (not market proof)" % scoring
    elif verified:
        stage, why = "PROGRAM_VERIFIED", "verification_status VERIFIED on record"
    else:
        stage, why = "PROGRAM_DISCOVERED", "record exists, verification incomplete"
    return {"stage": stage, "evidence": why,
            "index": FUNNEL.index(stage),
            "next_gate": FUNNEL[FUNNEL.index(stage) + 1] if FUNNEL.index(stage) + 1 < len(FUNNEL) else "LEARNED"}


def advance_allowed(stage: str, evidence: dict) -> dict:
    """Gate check for a forward move: names the missing evidence or passes."""
    needs = {"LINK_GENERATED": "registered_link", "CLICK_OBSERVED": "attributed_click",
             "CONVERSION_OBSERVED": "conversion_event", "COMMISSION_PENDING": "network_report",
             "COMMISSION_CONFIRMED": "commission_confirmation",
             "PAYOUT_CONFIRMED": "payout_record", "LEARNED": "completed_window"}
    need = needs.get(FUNNEL[FUNNEL.index(stage) + 1] if stage in FUNNEL[:-1] else "", "")
    if not need:
        return {"allowed": stage == "LEARNED", "reason": "terminal or unknown"}
    if (evidence or {}).get(need):
        return {"allowed": True, "reason": "evidence present: %s" % need}
    return {"allowed": False, "reason": "missing evidence: %s" % need}
