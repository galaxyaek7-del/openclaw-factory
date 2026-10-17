"""Galaxy Forge -- Dynamic Pricer (Master Sprint, Plan A3, 2026-10-17).

Rule from the directive:
  recommended price = 10% below the cheapest SOURCED competitor
  floor             = unit cost / (1 - 0.60)   (keeps a 60% margin)

A competitor counts only with a source URL and a numeric price (the same
rule as quality_enforcer.sourced_competitors). With none, the answer is
RESEARCH_NEEDED: the pricer never invents a market price.

Recommendation only. Nothing here calls a platform or changes a live price;
every recommendation is appended to data/pricing/recommendations.jsonl so
the founder can review it before any manual change.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src" / "quality"))
from quality_enforcer import sourced_competitors  # noqa: E402

DEFAULT_LOG = ROOT / "data" / "pricing" / "recommendations.jsonl"
UNDERCUT = 0.10
TARGET_MARGIN = 0.60

PRICED, FLOOR_BOUND, RESEARCH_NEEDED = "PRICED", "FLOOR_BOUND", "RESEARCH_NEEDED"


def margin_floor(unit_cost) -> float | None:
    if not isinstance(unit_cost, (int, float)) or unit_cost < 0:
        return None
    return round(unit_cost / (1 - TARGET_MARGIN), 2)


def _charm(price: float) -> float:
    """Round down to a .99 / whole-dollar shape without going below 1."""
    return max(1.0, math.floor(price) - 0.01) if price >= 2 else round(price, 2)


def recommend(product: dict, *, unit_cost=None, log_path=None, save: bool = True) -> dict:
    comps = sourced_competitors(product.get("competitors"))
    current = product.get("price")
    floor = margin_floor(unit_cost if unit_cost is not None else product.get("unit_cost"))
    rec = {
        "recommended_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "product_id": product.get("id") or product.get("product_id"),
        "title": product.get("title") or product.get("name"),
        "current_price_usd": current,
        "margin_floor_usd": floor,
        "sourced_competitors": comps,
        "live_change": False,
    }
    if not comps:
        rec.update(status=RESEARCH_NEEDED, recommended_price_usd=None,
                   reason="no competitor with a source URL and a price; record sourced prices first")
    else:
        cheapest = min(c["price_usd"] for c in comps)
        target = _charm(cheapest * (1 - UNDERCUT))
        if floor is not None and target < floor:
            rec.update(status=FLOOR_BOUND, recommended_price_usd=floor,
                       reason=f"10% under cheapest (${cheapest:.2f}) is ${target:.2f}, below the 60% margin floor")
        else:
            rec.update(status=PRICED, recommended_price_usd=target,
                       reason=f"10% under cheapest sourced competitor (${cheapest:.2f})")
        if isinstance(current, (int, float)) and rec["recommended_price_usd"] is not None:
            rec["change_usd"] = round(rec["recommended_price_usd"] - current, 2)
    if save:
        p = Path(log_path) if log_path else DEFAULT_LOG
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


class DynamicPricer:
    """Class API (founder directive, 2026-10-17, "Cleanup + Evidence Fix").

    Replaces an earlier version of this class that returned
    ``"applied": True`` and ``"evidence_type": "REAL"`` for competitor prices
    that had no source. A price counts only when its source is an http(s)
    URL; evidence_type is "REAL" only when at least one such price exists,
    and ``applied`` is always False: this class recommends, the founder
    changes prices. Same rule as ``recommend()`` above.
    """

    def calculate_optimal_price(self, competitor_prices: list, price_sources: list,
                                product_cost: float, minimum_margin: float = 0.60) -> dict:
        validated = []
        for i, price in enumerate(competitor_prices or []):
            source = price_sources[i] if i < len(price_sources or []) else None
            if not isinstance(source, str) or not source.startswith(("http://", "https://")):
                continue                      # no source = not real
            if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
                continue
            validated.append({"price": float(price), "source": source})

        if not validated:
            return {
                "status": "CANNOT_PRICE",
                "reason": "No competitor prices with verified sources",
                "action": "Research real competitors before pricing",
                "evidence_type": "NONE",
                "applied": False,
            }

        cheapest = min(validated, key=lambda v: v["price"])
        min_price = cheapest["price"]
        suggested = min_price * (1 - UNDERCUT)
        min_viable = product_cost / (1 - minimum_margin) if minimum_margin < 1 else 0.0
        if suggested < min_viable:
            suggested, basis = min_viable, "MARGIN_FLOOR"
        else:
            basis = "MARKET_MINUS_10_PERCENT"

        return {
            "status": "CALCULATED",
            "suggested_price": round(suggested, 2),
            "basis": basis,
            "cheapest_competitor": min_price,
            "cheapest_source": cheapest["source"],
            "validated_competitors": validated,
            "margin": round((suggested - product_cost) / suggested, 3) if suggested else 0.0,
            "logic": f"${min_price:g} x 0.90 = ${min_price * (1 - UNDERCUT):.2f}",
            "evidence_type": "REAL",
            "applied": False,
            "note": "Recommendation only - Founder approves price changes",
        }
