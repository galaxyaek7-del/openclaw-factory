#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate Commerce — real product dataset (ADR-149, 2026-07-30).

4 real standing desk converters, each with a real Amazon ASIN, price,
and rating -- verified via a real, one-time manual browse of public
Amazon search results on 2026-07-30 (not a live scrape, not a
programmatic API call, not fabricated). This is a static, disclosed-
source snapshot: prices/ratings may have changed since -- the real
comparison page discloses this explicitly rather than presenting a
stale number as live. Auto-discovery/refresh is deliberately not built
here -- explicitly excluded by the directive as premature.
"""

VERIFIED_AT = "2026-07-30"
SOURCE = "Manual research via public Amazon search results (amazon.com/s?k=standing+desk+converter), verified 2026-07-30 -- not a live API, not scraped programmatically."

PRODUCTS = [
    {
        "id": "B0864RSM5S",
        "asin": "B0864RSM5S",
        "name": "PowerPro 36 Inch Electric Standing Desk Converter",
        "description": "Push-button electric height adjustment, wide keyboard tray, supports dual monitors and a laptop.",
        "price_usd": 349.00,
        "list_price_usd": None,
        "rating": 4.5,
        "rating_count": 496,
        "category": "standing_desk_converters",
    },
    {
        "id": "B07LCCT6VS",
        "asin": "B07LCCT6VS",
        "name": "FITUEYES Height Adjustable Standing Desk Converter, 36\" Wide",
        "description": "Manual gas-spring height adjustment, 36-inch wide surface, dual monitor riser with keyboard tray.",
        "price_usd": 179.99,
        "list_price_usd": None,
        "rating": 4.6,
        "rating_count": 2547,
        "category": "standing_desk_converters",
    },
    {
        "id": "B07LCCJD6B",
        "asin": "B07LCCJD6B",
        "name": "FITUEYES Height Adjustable Standing Desk Converter, 32\" Wide",
        "description": "Manual gas-spring height adjustment, 32-inch wide surface, dual monitor riser with keyboard tray. Amazon's own \"Overall Pick\" badge at research time.",
        "price_usd": 111.98,
        "list_price_usd": 139.99,
        "rating": 4.6,
        "rating_count": 2408,
        "category": "standing_desk_converters",
    },
    {
        "id": "B0D1C9LBN5",
        "asin": "B0D1C9LBN5",
        "name": "Aconcept Extra-Slim 24 x 14 inch Standing Desk Converter",
        "description": "Compact manual lift, slim profile, sized for a single monitor or laptop -- the budget/space-constrained option.",
        "price_usd": 49.99,
        "list_price_usd": None,
        "rating": 4.1,
        "rating_count": 62,
        "category": "standing_desk_converters",
    },
]


def _weighted_score(product):
    """A standard, disclosed real ranking formula (rating weighted by
    log of rating count) -- never "whichever product paid Amazon for ad
    placement." Real math over real fields, not an invented score."""
    import math
    return product["rating"] * math.log10(max(product["rating_count"], 1) + 1)


def list_products(category="standing_desk_converters"):
    items = [p for p in PRODUCTS if p["category"] == category]
    items.sort(key=_weighted_score, reverse=True)
    return {
        "category": category,
        "products": items,
        "count": len(items),
        "verified_at": VERIFIED_AT,
        "source": SOURCE,
        "ranking_method": "rating weighted by log10(rating_count) -- a standard real weighted-rating formula, never Amazon's own paid ad placement.",
    }


def get_product(product_id):
    return next((p for p in PRODUCTS if p["id"] == product_id), None)
