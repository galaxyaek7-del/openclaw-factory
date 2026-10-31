"""Transparent campaign priority for offers (0-100), with its uncertainty.

Factors (points): destination verified and eligible (gate, not points);
measurement confidence 0-20; offer clarity 0-20; demand evidence 0-20;
platform fit at zero production cost 0-15; historical performance 0-15;
risk penalty; rotation penalty for offers campaigned in the last 30 days.

Today demand evidence and historical performance are UNKNOWN for every offer
(no demand data in the manifests, zero sales, no post metrics). They score 0
and are listed as uncertainty, never guessed. With so little signal the plan
spreads low-cost experiments across arms instead of repeating the same few.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

TEXT_PLATFORMS = ("linkedin", "x")
ROTATION_DAYS = 30


def score(offer: dict, *, recent_offer_ids=frozenset(), sales_by_offer=None) -> dict:
    f, unknown = {}, []
    if offer["eligibility"]["status"] != "ELIGIBLE":
        return {"offer_id": offer["offer_id"], "score": None, "excluded": offer["eligibility"]["reasons"]}
    m = offer.get("measurement", {}).get("destination")
    f["measurement_confidence"] = {"gumroad": 20, "network": 10}.get(m, 5)
    clarity = 0
    clarity += 8 if len(offer.get("description") or "") >= 300 else 4 if offer.get("description") else 0
    clarity += 6 if offer.get("price_cents") is not None or offer["type"] == "content_asset" else 0
    clarity += 6 if offer.get("tags") else 0
    f["offer_clarity"] = clarity
    f["demand_evidence"] = 0
    unknown.append("demand evidence: none recorded for this offer")
    f["zero_cost_platform_fit"] = 15 if any(p in TEXT_PLATFORMS for p in offer.get("platforms", [])) else 5
    sales = (sales_by_offer or {}).get(offer["offer_id"])
    f["historical_performance"] = min(15, 5 * sales) if sales else 0
    if not sales:
        unknown.append("historical performance: no sales or post metrics yet")
    f["risk_penalty"] = -10 if offer.get("rights_status") not in ("OWNED_ORIGINAL", "CLEARED") else 0
    f["rotation_penalty"] = -25 if offer["offer_id"] in recent_offer_ids else 0
    return {"offer_id": offer["offer_id"], "arm": offer["arm"], "score": max(0, sum(f.values())),
            "factors": f, "uncertainty": unknown}


def recent_offers(jobs: list, now=None, days=ROTATION_DAYS) -> set:
    now = now or datetime.now(timezone.utc)
    cut = (now - timedelta(days=days)).timestamp()
    return {j["offer_id"] for j in jobs if j.get("ts", 0) >= cut}


def plan(offers: list, *, n=6, per_arm=2, recent_offer_ids=frozenset(), sales_by_offer=None, accept=None) -> list:
    """Top n eligible offers, at most per_arm from one arm, so one arm (or one
    product) is not promoted over and over while demand is unknown. `accept`
    (offer_id -> bool) can require, e.g., at least one QA-passing draft."""
    scored = [score(o, recent_offer_ids=recent_offer_ids, sales_by_offer=sales_by_offer) for o in offers]
    scored = sorted((s for s in scored if s["score"] is not None), key=lambda s: (-s["score"], s["offer_id"]))
    picked, per = [], {}
    for s in scored:
        if len(picked) >= n:  # checked first: n=0 must pick nothing (it used to pick one)
            break
        if per.get(s["arm"], 0) >= per_arm:
            continue
        if accept is not None and not accept(s["offer_id"]):
            continue
        picked.append(s)
        per[s["arm"]] = per.get(s["arm"], 0) + 1
        if len(picked) >= n:
            break
    return picked
