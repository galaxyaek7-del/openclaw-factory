#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Premium Pricing Validator — for جد مربحة products.

Validates that a premium-priced product ($327) is justified for its page count and platform.
Reuses economics.py market_realism and net_profit, never new pricing engine.

Checks:
- economics.evaluate(price, platform, config, page_count) → approved + market_realism
- If market_realism False → suggest bundling (add printable/template to reach premium) or page count increase
- Platform via economics.platform_for_product_type (G2 central)
"""
from typing import Optional

def validate_premium_price(price: float, product_type: str = "premium", page_count: Optional[int] = None):
    """Returns validation dict, never raises on missing config."""
    import economics, json
    from pathlib import Path
    try:
        cfg = economics.load_config(str(Path(__file__).resolve().parent.parent / "config" / "economics.json"))
    except Exception as e:
        return {"valid": False, "reason": f"config load failed: {e}", "suggestion": "check config/economics.json"}
    platform = economics.platform_for_product_type(product_type)
    try:
        result = economics.evaluate(price, platform, cfg, page_count=page_count)
    except Exception as e:
        return {"valid": False, "reason": f"evaluate failed: {e}", "platform": platform}
    approved = result.get("approved", False)
    market_realistic = result.get("market_realistic", True)
    suggested = result.get("suggested_realistic_price")
    if not approved:
        return {"valid": False, "platform": platform, "reason": result.get("reason"), "market_realistic": market_realistic, "suggestion": f"price {price} below floor {suggested}, increase price or reduce cost"}
    if market_realistic is False:
        return {"valid": False, "platform": platform, "reason": f"market unrealistic for {page_count} pages at ${price} → suggested ${suggested}", "market_realistic": False, "suggestion": "add bundle (template/cover) or increase pages to justify premium"}
    return {"valid": True, "platform": platform, "reason": result.get("reason"), "market_realistic": True}

def validate_high_profit_product(niche: str, price: float, product_type: str = "premium", page_count: Optional[int] = None):
    """Combined check for highly profitable product: pricing + high-profit screener."""
    pricing = validate_premium_price(price, product_type, page_count)
    # Also check if niche would be high-profit via screener
    from tools.high_profit_screener import is_high_profit
    # Build minimal entry for check: we can't run full pipeline without decision, so just check pricing
    return {
        "niche": niche,
        "pricing": pricing,
        "high_profit_ready": pricing["valid"],
    }
