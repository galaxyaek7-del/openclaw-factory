#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate program intelligence (read-only joins, disclosed rules).

Reuse, not duplication: portfolio rows come from
`commission_engine.load_opportunity_portfolio`, freshness from the engine's
own `_freshness_from_last_verified`, ranking from `rank_commission_shortlist`.
This module adds only three small, disclosed mappings the engine never
computed: per-field evidence classification, an opportunity category, and a
lifecycle (kill/hibernate) decision. No network, no writes, no revenue.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

import commission_engine as ce

# Fields the portfolio schema actually carries (OBSERVED from
# data/commission_opportunities.jsonl). Anything outside this list is
# UNKNOWN by construction, never backfilled.
_KNOWN_FIELDS = (
    "opportunity_id", "merchant", "network", "verification_status",
    "commission_value", "recurring", "recurring_commission", "cookie_duration",
    "last_verified", "evidence_url", "source", "category",
)

_CATEGORIES = ("STRONG_EVIDENCE", "PROMISING", "INSUFFICIENT_EVIDENCE",
               "HIGH_RISK", "HOLD")
_LIFECYCLE = ("ACTIVE", "MONITORING", "HOLD", "BLOCKED", "HIBERNATE")


def program_record(opportunity: dict, now=None) -> dict:
    """One structured intelligence record. Every field tagged
    OBSERVED (present in the row) or UNKNOWN (absent) — never inferred."""
    now = now or datetime.now(timezone.utc)
    rec = {"opportunity_id": opportunity.get("opportunity_id"),
           "fields": {}, "freshness": None, "classified_at": now.isoformat()}
    for field in _KNOWN_FIELDS:
        value = opportunity.get(field)
        rec["fields"][field] = {
            "value": value,
            "evidence": "OBSERVED" if value not in (None, "", [], "UNKNOWN",
                                                    "COMMISSION_UNKNOWN") else "UNKNOWN",
        }
    # The engine returns a plain status string ("FRESH"/"AGING"/"STALE"/
    # "UNKNOWN" under its disclosed 14/45-day rule); wrap it so callers get
    # a stable shape without re-deriving the rule here.
    try:
        status = ce._freshness_from_last_verified(
            opportunity.get("last_verified"), now=now)
        rec["freshness"] = {"status": status if isinstance(status, str) else "UNKNOWN",
                            "basis": "commission_engine 14/45-day rule"}
    except Exception as e:
        rec["freshness"] = {"status": "UNKNOWN", "reason": "freshness unreadable: %s" % type(e).__name__}
    return rec


def score_category(record: dict, commercial: Optional[dict] = None) -> dict:
    """Map a program record (+ optional commercial signals) onto one of
    STRONG_EVIDENCE / PROMISING / INSUFFICIENT_EVIDENCE / HIGH_RISK / HOLD.

    Disclosed rules (no fake precision, reasons always emitted):
    - STRONG_EVIDENCE requires VERIFIED + FRESH + real conversion evidence.
      With zero conversions recorded anywhere, this is currently unreachable
      by construction — and says so, rather than grading on a curve.
    - HIGH_RISK requires a known adverse fact (material term deterioration,
      compliance exposure, or STALE terms with no re-check path).
    - PROMISING = VERIFIED + not-STALE + no adverse fact.
    - INSUFFICIENT_EVIDENCE = anything with UNKNOWN-heavy fields.
    - HOLD = explicit human pause flag present.
    `commercial` may carry {"conversions": int, "adverse": [reasons],
    "hold": bool} — all default to the honest empty case.
    """
    commercial = commercial or {}
    fields = record.get("fields", {})
    status = (fields.get("verification_status", {}) or {}).get("value")
    fresh = (record.get("freshness") or {})
    fresh_status = fresh.get("status") if isinstance(fresh, dict) else "UNKNOWN"
    reasons = []
    if commercial.get("hold"):
        return {"category": "HOLD", "reasons": ["explicit human pause flag"]}
    if commercial.get("adverse"):
        return {"category": "HIGH_RISK",
                "reasons": ["adverse: %s" % a for a in commercial["adverse"]]}
    if status == "VERIFIED" and fresh_status == "FRESH" and commercial.get("conversions", 0) > 0:
        return {"category": "STRONG_EVIDENCE",
                "reasons": ["verified", "fresh", "%d conversions" % commercial["conversions"]]}
    if status == "VERIFIED" and fresh_status in ("FRESH", "AGING"):
        reasons.append("verified, freshness=%s, no adverse fact" % fresh_status)
        if commercial.get("conversions", 0) == 0:
            reasons.append("no conversions yet — promising, not proven")
        return {"category": "PROMISING", "reasons": reasons}
    if fresh_status == "STALE":
        reasons.append("evidence stale — re-check before any new content use")
    unknowns = [k for k, v in fields.items() if v.get("evidence") == "UNKNOWN"]
    if unknowns:
        reasons.append("unknown fields: %s" % ", ".join(unknowns[:6]))
    return {"category": "INSUFFICIENT_EVIDENCE",
            "reasons": reasons or ["no basis to promote"]}


def kill_decision(program_state: str, campaign: Optional[dict] = None) -> dict:
    """Lifecycle routing per the directive's hibernate rules. Pure function:
    inputs in, decision out. `program_state`: VERIFIED/PARTIALLY/THIRD_PARTY/
    CLOSED/TERMS_CHANGED/EVIDENCE_GONE/UNTRUSTED_TRACKING. `campaign` may
    carry {"conversions": int, "window_days": int, "window_complete": bool,
    "compliance_risk": bool}. Never deletes history — callers archive."""
    campaign = campaign or {}
    if program_state in ("CLOSED",):
        return {"state": "HIBERNATE", "reason": "program closed upstream"}
    if program_state in ("TERMS_CHANGED", "EVIDENCE_GONE", "UNTRUSTED_TRACKING"):
        return {"state": "HIBERNATE", "reason": "unresolvable evidence/tracking gap: %s" % program_state}
    if campaign.get("compliance_risk"):
        return {"state": "HOLD", "reason": "compliance risk unresolved"}
    if campaign.get("window_complete") and not campaign.get("conversions"):
        return {"state": "HOLD",
                "reason": "valid window, zero conversions — diagnose before any clone"}
    if campaign.get("conversions", 0) > 0:
        return {"state": "ACTIVE", "reason": "converting — measure for scale candidacy"}
    if program_state in ("VERIFIED", "PARTIALLY_VERIFIED", "THIRD_PARTY_ONLY"):
        return {"state": "MONITORING", "reason": "no campaign signal yet"}
    return {"state": "HOLD", "reason": "default pause: %s" % program_state}


def portfolio_intelligence(portfolio=None, now=None) -> List[dict]:
    """Whole-portfolio pass: record + category per opportunity (no commercial
    signals exist, so every entry is honestly scored without them)."""
    if portfolio is None:
        portfolio = ce.load_opportunity_portfolio()
    out = []
    for o in portfolio:
        rec = program_record(o, now=now)
        out.append({"opportunity_id": rec["opportunity_id"],
                    "record": rec, "scoring": score_category(rec),
                    "lifecycle": kill_decision(
                        "CLOSED" if rec["fields"].get("verification_status", {}).get("value") == "CLOSED"
                        else (rec["fields"].get("verification_status", {}).get("value") or "UNKNOWN"))})
    return out
