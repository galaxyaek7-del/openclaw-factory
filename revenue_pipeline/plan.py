"""
Revenue Pipeline — production plan + real financial metrics.

Reuses economics.py (real platform fees, ADR-041) and profit_oracle's
real logged AI cost — no new profit formula, no new cost model.
"""

from pathlib import Path

import economics
import profit_oracle

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
_ECONOMICS_CONFIG = _FACTORY_ROOT / "config" / "economics.json"


def build_production_plan(decision):
    """decision: a Decision.to_dict()-shaped record. Every field here is
    read from data the pipeline already computed (evaluation_snapshot's
    real pricing/reasoning) — this only organizes it into a plan shape,
    it does not re-derive anything."""
    snapshot = decision.get("evaluation_snapshot") or {}
    pricing = snapshot.get("pricing") or {}
    price_str = pricing.get("recommended_price", "")
    try:
        price = float(str(price_str).replace("$", "").strip())
    except (TypeError, ValueError):
        price = None

    return {
        "niche": decision.get("niche"),
        "tier": decision.get("tier"),
        "recommended_price": price,
        "recommended_platform": "gumroad_digital",  # the only real, currently-tested distribution arm (channels/gumroad_arm.py)
        "product_type": "book",
        "reasoning": decision.get("reasoning"),
        "pricing_note": pricing.get("note"),
    }


def estimate_production_cost(log_file=None):
    """Real average logged Groq cost per real book generation
    (profit_oracle._real_average_ai_cost_per_call(), reused directly,
    ADR-041) — None/DISCOVERY when zero real generations have been
    logged yet, never a fabricated placeholder cost."""
    avg_cost, sample_size = profit_oracle._real_average_ai_cost_per_call(log_file=log_file)
    if avg_cost is None:
        return {"maturity": "DISCOVERY", "reason": "لا استدعاءات Groq حقيقية مسجَّلة بعد لحساب تكلفة إنتاج حقيقية"}
    return {"maturity": "REAL", "estimated_cost_usd": round(avg_cost, 4), "sample_size": sample_size}


def estimate_roi(price, production_cost_usd, platform="gumroad_digital"):
    """Real fee math (economics.net_profit(), reused directly, ADR-041) —
    never a new profit formula. Honestly Unknown whenever either input
    (real recommended price, real logged production cost) is missing."""
    if price is None:
        return {"maturity": "DISCOVERY", "reason": "لا سعر مُوصى به حقيقي لحساب العائد عليه"}
    if not production_cost_usd:
        return {"maturity": "DISCOVERY", "reason": "لا تكلفة إنتاج حقيقية مسجَّلة بعد لحساب العائد"}

    config = economics.load_config(str(_ECONOMICS_CONFIG))
    net_profit = economics.net_profit(price, platform, config)
    net_after_cost = net_profit - production_cost_usd
    roi_pct = round(100 * net_after_cost / production_cost_usd, 1)

    return {
        "maturity": "REAL",
        "net_profit_after_fees": round(net_profit, 2),
        "production_cost_usd": round(production_cost_usd, 4),
        "expected_net_after_cost": round(net_after_cost, 2),
        "roi_pct": roi_pct,
    }
