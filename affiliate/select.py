#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Internal opportunity ranking from documented evidence only (read-only).

Not a subjective 'best' pick — an operational prioritization. Every
criterion reports PRESENT or INSUFFICIENT with its citation. Any
opportunity with missing gates carries STATUS=INSUFFICIENT_EVIDENCE
and is never scaled. Max 5 ACTIVE (enforced by opportunities.py)."""

from __future__ import annotations

CRITERIA = ("PROBLEM", "BUYER", "URGENCY", "WILLINGNESS_TO_PAY",
            "COMPETITION", "DELIVERY_DIFFICULTY", "AUTOMATION_POTENTIAL",
            "DISTRIBUTION_ACCESS", "EVIDENCE_QUALITY")


def _crit(value, citation):
    return {"level": "PRESENT" if value else "INSUFFICIENT",
            "citation": citation if value else "no documented evidence"}


def rank_opportunities() -> list:
    """Rank queue rows + program-backed niches. Deterministic, cited."""
    from affiliate import opportunities as opp, intelligence as intel
    ranked = []
    for e in opp.read_queue():
        ev = e.get("evidence") or ""
        gate = opp.evidence_gate_check(e)
        crit = {
            "PROBLEM": _crit(e.get("problem") or e.get("title"), "queue row"),
            "BUYER": _crit(e.get("target_buyer"), "queue row"),
            "URGENCY": _crit("deadline" in ev.lower() or "mandate" in ev.lower(), "evidence text"),
            "WILLINGNESS_TO_PAY": _crit(False, ""),
            "COMPETITION": _crit("overlap" in str(e.get("status", "")).lower(), "status note"),
            "DELIVERY_DIFFICULTY": _crit(False, ""),
            "AUTOMATION_POTENTIAL": _crit(False, ""),
            "DISTRIBUTION_ACCESS": _crit(False, ""),
            "EVIDENCE_QUALITY": _crit(bool(ev), "evidence field"),
        }
        score = sum(1 for c in crit.values() if c["level"] == "PRESENT")
        ranked.append({"id": e.get("id"), "kind": "queue",
                       "criteria": crit, "score": score,
                       "STATUS": "RANKED" if gate["pass"] else "INSUFFICIENT_EVIDENCE",
                       "missing": gate["missing"]})
    try:
        rows = intel.portfolio_intelligence()
    except Exception:
        rows = []
    for r in rows:
        if "error" in r:
            continue
        rec = r.get("record", {})
        fresh = (rec.get("freshness") or {}).get("status") == "FRESH"
        ranked.append({"id": r.get("opportunity_id"), "kind": "program",
                       "criteria": {"EVIDENCE_QUALITY": _crit(
                           fresh, "portfolio intelligence freshness")},
                       "score": 1 if fresh else 0,
                       "STATUS": "RANKED" if fresh else "INSUFFICIENT_EVIDENCE",
                       "scoring": (r.get("scoring") or {}).get("category")})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked
