# -*- coding: utf-8 -*-
"""
Galaxy Forge v7+ - Market Analyzer & Niche Scout
Analyzes market trends and recommends profitable niches

Honesty note (STRUCTURAL_DIAGNOSIS.md disease #2, added 2026-07-15 — same
discipline as market_hunter.py's own docstring): MARKET_DATA below is a
fixed, hardcoded reference table, not a live market scan. POST /api/market-
analyze (server.js) calls analyze_market() with no input at all, so every
call returns the exact same top-3 niches out of the exact same 10-item
table, always. This is a third, independent "is this niche good" scorer
alongside profit_oracle.py's score_opportunity()/opportunity_score() — it
predates both and serves a different, dashboard-facing "what's trending in
general" button rather than gating any real production decision, so it is
NOT consolidated into profit_oracle here (that is a larger, riskier change
better suited to its own session with real usage data — see
STRUCTURAL_DIAGNOSIS.md disease #2). What IS fixed here: the previous
`"analysis_confidence": "High"` label overstated what a static table can
possibly tell you — corrected below to say what this function actually is.
"""

import json
from datetime import datetime

MARKET_DATA = {
    "trending_niches": [
        {"niche": "Meal Planner for Busy Moms", "demand": 95, "competition": 60, "avg_price": 12.99, "monthly_sales": 450},
        {"niche": "Budget Tracker for Freelancers", "demand": 88, "competition": 45, "avg_price": 9.99, "monthly_sales": 320},
        {"niche": "Fitness Tracker for Women", "demand": 92, "competition": 70, "avg_price": 11.99, "monthly_sales": 520},
        {"niche": "Gratitude Journal for Mental Health", "demand": 85, "competition": 55, "avg_price": 8.99, "monthly_sales": 280},
        {"niche": "Productivity Planner for Students", "demand": 90, "competition": 65, "avg_price": 10.99, "monthly_sales": 410},
        {"niche": "Expense Tracker for Small Business", "demand": 82, "competition": 50, "avg_price": 14.99, "monthly_sales": 340},
        {"niche": "Habit Tracker Minimalist Design", "demand": 88, "competition": 62, "avg_price": 7.99, "monthly_sales": 380},
        {"niche": "Wedding Planning Checklist", "demand": 78, "competition": 40, "avg_price": 15.99, "monthly_sales": 180},
        {"niche": "Home Organization Planner", "demand": 80, "competition": 55, "avg_price": 9.99, "monthly_sales": 290},
        {"niche": "Investment Portfolio Tracker", "demand": 75, "competition": 35, "avg_price": 19.99, "monthly_sales": 150},
    ],
    "seasonal_trends": {
        "January": "Goal Setting, Fitness, Productivity",
        "February": "Love & Relationships, Wellness",
        "March": "Spring Cleaning, Organization",
        "April": "Health, Tax Planning",
        "May": "Travel Planning, Outdoor Activities",
        "June": "Wedding Planning, Summer Goals",
    }
}

def calculate_profit_score(niche_data):
    demand = niche_data["demand"]
    competition = niche_data["competition"]
    price = niche_data["avg_price"]
    demand_score = demand * 0.4
    competition_score = (100 - competition) * 0.35
    price_score = min(price / 20 * 100, 25)
    total = demand_score + competition_score + price_score
    return min(total, 100)

def get_recommended_niches(limit=3):
    niches_with_scores = []
    for niche in MARKET_DATA["trending_niches"]:
        score = calculate_profit_score(niche)
        niches_with_scores.append({
            **niche,
            "profit_score": round(score, 1),
            "estimated_monthly_profit": round(niche["monthly_sales"] * (niche["avg_price"] * 0.7), 2),
            "recommendation_reason": get_recommendation_reason(niche, score)
        })
    niches_with_scores.sort(key=lambda x: x["profit_score"], reverse=True)
    return niches_with_scores[:limit]


def get_recommendation_reason(niche, score):
    reasons = []
    if niche["demand"] > 85:
        reasons.append("High demand")
    if niche["competition"] < 60:
        reasons.append("Low competition")
    if niche["avg_price"] > 10:
        reasons.append("Good price point")
    if niche["monthly_sales"] > 300:
        reasons.append("Proven sales volume")
    return " + ".join(reasons) if reasons else "Solid market opportunity"

def analyze_market():
    current_month = datetime.now().strftime("%B")
    seasonal = MARKET_DATA["seasonal_trends"].get(current_month, "General trends")
    recommendations = get_recommended_niches(3)
    return {
        "timestamp": datetime.now().isoformat(),
        "current_month": current_month,
        "seasonal_opportunity": seasonal,
        "recommended_niches": recommendations,
        "total_analyzed": len(MARKET_DATA["trending_niches"]),
        "analysis_confidence": "static_reference_table",
        "note": "Curated reference list of common KDP/Etsy niche archetypes, not a live market scan — same 10 niches every call, scored by a fixed formula.",
    }

if __name__ == "__main__":
    result = analyze_market()
    print(json.dumps(result, indent=2))