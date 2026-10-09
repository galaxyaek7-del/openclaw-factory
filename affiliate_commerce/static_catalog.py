#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static catalog builder for the Pages-hosted affiliate page (GF-19).

Root cause it fixes: customer_site/affiliate-standing-desks.html fetched
/api/affiliate/products + /api/affiliate/click/*, which are factory-server
routes that do not exist on the static GitHub Pages host — so the public
page rendered zero product links.

Static-first fix: this module builds the exact public-safe payload from the
real affiliate_commerce.products dataset (same ranking, same fields) plus a
plain Amazon destination URL per product. No secrets (ASINs/prices/ratings
are public Amazon data). No tag invented: the URL carries a real Associates
tag only when one is configured, else an honest untagged product URL.

Capability separation (GF-19 §3):
  display  = this payload (always safe to render),
  link-gen = tag applied only when genuinely configured,
  tracking = NOT included — static clicks cannot be counted; the page must
             not claim attribution. (Server-side /api/affiliate/click
             remains the only counted path, factory host only.)
"""
from affiliate_commerce import networks, products

REQUIRED_FIELDS = ("id", "name", "description", "price_usd",
                   "rating", "rating_count")


class StaticCatalogError(ValueError):
    pass


def _validate_product(p):
    for f in REQUIRED_FIELDS:
        if f not in p or p[f] is None:
            raise StaticCatalogError("product missing required field %r: %r" % (f, p.get("id")))
    if not isinstance(p["price_usd"], (int, float)):
        raise StaticCatalogError("bad price_usd for %r" % p.get("id"))
    if not isinstance(p["rating"], (int, float)):
        raise StaticCatalogError("bad rating for %r" % p.get("id"))
    asin = p.get("asin") or p.get("id")
    if not asin:
        raise StaticCatalogError("no asin/id for product URL")


def build_static_catalog(category="standing_desk_converters"):
    """Return the public-safe catalog dict. Raises StaticCatalogError on
    missing/malformed data — never a silent empty list for a bad dataset
    (a genuinely empty category legitimately yields products: [])."""
    data = None
    # Validate raw rows BEFORE the upstream ranking sort, so a malformed
    # dataset raises our explicit StaticCatalogError (never a bare KeyError
    # from inside the sort, never a silent drop).
    for p in products.PRODUCTS:
        if p.get("category") == category:
            _validate_product(p)
    data = products.list_products(category=category)
    items = data.get("products", [])
    out_products = []
    for p in items:
        _validate_product(p)
        asin = p.get("asin") or p["id"]
        out_products.append({
            "id": p["id"],
            "name": p["name"],
            "description": p["description"],
            "price_usd": p["price_usd"],
            "list_price_usd": p.get("list_price_usd"),
            "rating": p["rating"],
            "rating_count": p["rating_count"],
            # Honest destination: tagged only when genuinely configured.
            "url": networks.build_amazon_url(asin),
            "affiliate_attributed": networks.amazon_associate_tag_configured(),
        })
    return {
        "category": category,
        "products": out_products,
        "count": len(out_products),
        "verified_at": data.get("verified_at"),
        "source": data.get("source"),
        "ranking_method": data.get("ranking_method"),
        "tag_configured": networks.amazon_associate_tag_configured(),
    }
