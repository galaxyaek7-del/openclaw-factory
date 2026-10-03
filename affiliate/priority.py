#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — AFFILIATE_PRIORITY_SCORE.

Disclosed heuristic over REAL registry fields only. Never a performance
promise, never blended into revenue. Missing values stay UNKNOWN and score
0 for that axis — never imputed. commission_engine.py's 13-dim scorer
remains the economics depth; this is the directive's named ranking view.
"""
from datetime import datetime, timezone
from . import registry

MAX_SCORE = 100

WEIGHTS = {
    "recurring": 25,
    "commission_evidence": 20,
    "cookie": 15,
    "verification_freshness": 15,
    "terms_transparency": 15,
    "geographic_fit": 10,
}


def _days_since(date_str):
    if not date_str or date_str == "UNKNOWN":
        return None
    try:
        dt = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def _cookie_points(cookie_text):
    if not cookie_text or cookie_text == "UNKNOWN":
        return 0, "UNKNOWN"
    t = str(cookie_text).lower()
    import re
    days = [int(n) for n in re.findall(r"(\d+)\s*-?\s*day", t)]
    hours = [int(n) for n in re.findall(r"(\d+)\s*hour", t)]
    total_days = (max(days) if days else 0) + (max(hours) if hours else 0) / 24.0
    if total_days >= 30:
        return WEIGHTS["cookie"], "OBSERVED"
    if total_days >= 7:
        return 8, "OBSERVED"
    if total_days > 0:
        return 3, "OBSERVED"
    lifetime = ("lifetime" in t or "recurring" in t)
    if lifetime:
        return WEIGHTS["cookie"], "DERIVED"
    return 0, "UNKNOWN"


def score_program(record):
    """Returns {opportunity_id, score, components[{axis, points, basis}],
    warnings}. Pure function of the record dict."""
    comps = []
    rec = record.get("recurring")
    if rec is True:
        comps.append({"axis": "recurring", "points": WEIGHTS["recurring"], "basis": "OBSERVED"})
    elif rec == "UNKNOWN" or rec is None:
        comps.append({"axis": "recurring", "points": 0, "basis": "UNKNOWN"})
    else:
        comps.append({"axis": "recurring", "points": 0, "basis": "OBSERVED"})
    rate = str(record.get("commission_rate", "UNKNOWN"))
    if rate != "UNKNOWN" and any(ch.isdigit() for ch in rate):
        comps.append({"axis": "commission_evidence", "points": WEIGHTS["commission_evidence"], "basis": "OBSERVED"})
    else:
        comps.append({"axis": "commission_evidence", "points": 0, "basis": "UNKNOWN"})
    pts, basis = _cookie_points(record.get("cookie_duration"))
    comps.append({"axis": "cookie", "points": pts, "basis": basis})
    age = _days_since(record.get("verification_date"))
    if age is None:
        comps.append({"axis": "verification_freshness", "points": 0, "basis": "UNKNOWN"})
    elif age <= 30:
        comps.append({"axis": "verification_freshness", "points": WEIGHTS["verification_freshness"], "basis": "OBSERVED"})
    else:
        comps.append({"axis": "verification_freshness", "points": 7, "basis": "OBSERVED"})
    known_terms = sum(1 for k in ("payout_threshold", "prohibited_traffic_sources",
                                  "refund_rules", "attribution_rules")
                      if str(record.get(k, "UNKNOWN")) != "UNKNOWN")
    comps.append({"axis": "terms_transparency",
                  "points": min(WEIGHTS["terms_transparency"], known_terms * 4),
                  "basis": "OBSERVED" if known_terms else "UNKNOWN"})
    geo = str(record.get("geographic_restrictions", "UNKNOWN"))
    if geo == "UNKNOWN":
        comps.append({"axis": "geographic_fit", "points": 0, "basis": "UNKNOWN"})
    elif "algeria" in geo.lower() or "global" in geo.lower() or "worldwide" in geo.lower():
        comps.append({"axis": "geographic_fit", "points": WEIGHTS["geographic_fit"], "basis": "OBSERVED"})
    else:
        comps.append({"axis": "geographic_fit", "points": 0, "basis": "OBSERVED"})
    warnings = []
    if record.get("affiliate_status") in ("DISCONTINUED", "REJECTED"):
        warnings.append("program not rankable: " + record["affiliate_status"])
    total = sum(c["points"] for c in comps)
    return {"opportunity_id": record.get("opportunity_id", "UNKNOWN"),
            "program_name": record.get("program_name", "UNKNOWN"),
            "status": record.get("affiliate_status", "UNKNOWN"),
            "score": min(MAX_SCORE, total), "components": comps,
            "warnings": warnings,
            "not_a_performance_claim": True}


def rank_all():
    summary = registry.registry_summary()
    scored = [score_program(r) for r in summary["records"]]
    rankable = [s for s in scored if not s["warnings"]]
    held = [s for s in scored if s["warnings"]]
    rankable.sort(key=lambda s: s["score"], reverse=True)
    return {"ranked": rankable, "not_rankable": held,
            "generated_at": summary["generated_at"],
            "method": "AFFILIATE_PRIORITY_SCORE disclosed heuristic; missing=0, never imputed"}
