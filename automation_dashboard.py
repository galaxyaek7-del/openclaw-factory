#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Automation Revenue Engine — Dashboard (ADR-164, 2026-07-31).

The one real aggregator: scans real candidates (automation_
opportunity_scanner.py, passive only -- never triggers a new live
evaluation), scores each (automation_scoring.py, profit_oracle.py's
real ladder_opportunity_score() verbatim), ranks B2B-first / recurring-
revenue-preferred, and returns the ranked list -- or honestly "NO
VERIFIED OPPORTUNITY FOUND" per the directive's own literal required
string when the scanner finds nothing or every candidate fails a real
hard gate. Never builds a product -- read-only, recommend-only.
"""

from datetime import datetime, timezone

from automation_opportunity_scanner import NO_VERIFIED_OPPORTUNITY


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def build_automation_dashboard(limit=20, decisions_path=None):
    import automation_opportunity_scanner
    import automation_scoring
    from automation_catalog import category_catalog

    scan = automation_opportunity_scanner.scan_candidates(limit=limit, decisions_path=decisions_path)
    if "candidates" not in scan:
        return {
            "answer": NO_VERIFIED_OPPORTUNITY,
            "reason": scan.get("reason"),
            "catalog": category_catalog(),
            "generated_at": _now_iso(),
        }

    scored = [
        automation_scoring.score_opportunity(c["niche"], c["ladder"])
        for c in scan["candidates"]
    ]
    accepted = [s for s in scored if s["accepted"]]
    rejected = [s for s in scored if not s["accepted"]]

    if not accepted:
        return {
            "answer": NO_VERIFIED_OPPORTUNITY,
            "reason": f"{len(scored)} real candidate(s) scanned, 0 cleared profit_oracle.py's real hard gates.",
            "rejected_candidates": rejected,
            "catalog": category_catalog(),
            "generated_at": _now_iso(),
        }

    # Real ranking: B2B-first (directive Objective 6: "detect B2B
    # opportunities before B2C"), then real ladder_score descending --
    # never a second, competing scoring algorithm, just a real sort key.
    accepted.sort(key=lambda s: (not s["is_b2b"]["answer"], -(s["ladder_score"] or 0)))

    return {
        "ranked_opportunities": accepted,
        "rejected_candidates": rejected,
        "count_accepted": len(accepted),
        "count_rejected": len(rejected),
        "catalog": category_catalog(),
        "generated_at": _now_iso(),
    }
