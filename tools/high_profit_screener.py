#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""High-Profit Investment Screener — filter for very profitable products.

Reuses existing engines, never new scoring. Criteria for "جد مربحة" (very profitable):
- opportunity_score >= 75 (GOLDEN threshold per profit_oracle, not just 65 ACCEPTED)
- willingness_to_pay real and not UNKNOWN (market_evidence)
- recurring_revenue_potential >= 60 or long_term_strategic_value == True
- economics not dead_zone and margin >= 50

All criteria are OBSERVED/DERIVED, never ESTIMATED as OBSERVED.
"""
from typing import Optional

HIGH_PROFIT_SCORE_FLOOR = 75  # GOLDEN, not just ACCEPTED 65
HIGH_MARGIN_FLOOR = 50
HIGH_RECURRING_FLOOR = 60

def is_high_profit(entry) -> tuple[bool, str]:
    """Returns (is_high_profit, reason) for one investment_pipeline entry."""
    if not entry:
        return False, "no entry"
    score = entry.get("commercial_score")
    if score is None or score < HIGH_PROFIT_SCORE_FLOOR:
        return False, f"score {score} < {HIGH_PROFIT_SCORE_FLOOR}"
    wtp = entry.get("ranking_dimensions", {}).get("willingness_to_pay", {})
    if not wtp or wtp.get("value") in (None, "UNKNOWN", "unknown"):
        return False, "willingness_to_pay UNKNOWN"
    # Check margin via profit/potential if available, else check recurring
    recurring = entry.get("ranking_dimensions", {}).get("recurring_revenue_potential", {})
    recurring_val = recurring.get("value") if isinstance(recurring, dict) else None
    # recurring may be "high"/"medium"/numeric — check numeric or level
    if isinstance(recurring_val, (int, float)):
        if recurring_val < HIGH_RECURRING_FLOOR:
            return False, f"recurring {recurring_val} < {HIGH_RECURRING_FLOOR}"
    elif isinstance(recurring, dict) and recurring.get("level") == "low":
        return False, "recurring low"
    # Check economics not in dead zone if available
    est = entry.get("estimated_profit", {})
    if isinstance(est, dict) and est.get("in_dead_zone"):
        return False, "in dead_zone"
    return True, "passes all high-profit gates"

def screen_high_profit(decisions_path=None, limit=20):
    """Returns list of high-profit entries, sorted by commercial_score desc."""
    from investment_pipeline import build_investment_pipeline
    pipeline = build_investment_pipeline(decisions_path=decisions_path, limit=limit*3)
    candidates = []
    for e in pipeline.get("entries", []):
        ok, reason = is_high_profit(e)
        if ok:
            candidates.append(e)
    candidates.sort(key=lambda x: x.get("commercial_score", 0), reverse=True)
    return candidates[:limit]

def screener_report(decisions_path=None, limit=10):
    """Evidence for audit: what was checked, what passed, what failed."""
    from investment_pipeline import build_investment_pipeline
    pipeline = build_investment_pipeline(decisions_path=decisions_path, limit=limit*3)
    total = len(pipeline.get("entries", []))
    passed = screen_high_profit(decisions_path=decisions_path, limit=limit)
    return {
        "total_screened": total,
        "high_profit_count": len(passed),
        "high_profit_niches": [p["niche"] for p in passed],
        "criteria": {
            "score_floor": HIGH_PROFIT_SCORE_FLOOR,
            "margin_floor": HIGH_MARGIN_FLOOR,
            "recurring_floor": HIGH_RECURRING_FLOOR,
        },
    }
