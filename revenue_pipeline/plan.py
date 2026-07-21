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
    it does not re-derive anything.

    ADR-077 (Product Generation Pipeline): a ladder-tagged decision
    (`decision["ladder"]`, ADR-076) routes to `product_type="techdoc"` and
    `recommended_platform="paddle"` — the exact same routing
    factory_loop.js's briefFromGoldenOpportunity() already uses (ADR-071),
    kept consistent here rather than a second, diverging assumption.
    `economics_platform` is a separate field: ROI/fee math is still
    modeled against the real "gumroad_elite" band (config/economics.json)
    — the same $97-497 elite-tier fee structure book_generator.py's Dual
    Inspection already validates ladder-tagged products against
    (`_economics_platform_for("techdoc")`); `config/economics.json` has no
    dedicated "paddle" entry yet and Paddle's own fee structure isn't
    confirmed live (checkout still blocked by account onboarding,
    ADR-074), so this is the closest real, already-configured proxy, not
    a guess. Omitting a ladder tag reproduces the exact prior book/
    Gumroad plan unchanged."""
    snapshot = decision.get("evaluation_snapshot") or {}
    ladder = decision.get("ladder")

    if ladder:
        return {
            "niche": decision.get("niche"),
            "tier": decision.get("tier"),
            "recommended_price": snapshot.get("price"),
            "recommended_platform": "paddle",
            "economics_platform": "gumroad_elite",
            "product_type": "techdoc",
            "reasoning": decision.get("reasoning"),
            "pricing_note": f"Ladder rank: {ladder} (MASTER_CHARTER.md §2, ADR-065)",
        }

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
        "economics_platform": "gumroad_digital",
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


def estimate_pre_acceptance_roi(price, platform="gumroad_digital", log_file=None):
    """EOS Phase 2, Golden Hunter Evolution (2026-07-19): the one real
    ROI signal that was only ever computed AFTER an opportunity was
    ACCEPTED (via estimate_roi(), called from process_opportunity()).
    estimate_production_cost() already produces a real, usable-pre-
    production cost estimate (the factory-wide real average logged AI
    cost, not requiring this exact niche to have already been produced)
    -- so a real ROI figure is available at scoring time too, purely by
    calling these two already-real functions together. No new profit
    formula, no per-niche cost guess. Informational only -- this never
    changes the real accept/reject gate, which stays too speculative
    pre-production to act on directly."""
    cost = estimate_production_cost(log_file=log_file)
    if cost.get("maturity") != "REAL":
        return {"maturity": "DISCOVERY", "reason": cost.get("reason", "لا تكلفة إنتاج حقيقية بعد لتقدير عائد مسبق")}
    return estimate_roi(price, cost["estimated_cost_usd"], platform=platform)
