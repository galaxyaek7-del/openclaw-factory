"""Cycle 81 — product-quality triage over the REAL full Gumroad catalog.

Read-only over data/cycle81_gumroad_catalog_truth.json. Answers the founder's
§3 question ("does each product actually deliver what it says?") with signals
that come from the platform itself, not from our own optimism.
"""

from __future__ import annotations

import io
import json

F = "data/cycle81_gumroad_catalog_truth.json"


def main() -> None:
    d = json.load(io.open(F, encoding="utf-8-sig"))
    ps = d["products"]

    print("=" * 78)
    print("CATALOG REALITY (live, from Gumroad's own API, read-only)")
    print("=" * 78)
    print(f"live products      : {len(ps)}")
    print(f"published          : {sum(1 for p in ps if p['published'])}")
    print(f"with a real file   : {sum(1 for p in ps if p['has_file'])}")
    print(f"NO FILE ATTACHED   : {sum(1 for p in ps if not p['has_file'])}")
    print(f"total units sold   : {d['AUTHORITATIVE_REVENUE']['total_units_sold']}")
    print(f"total gross USD    : {d['AUTHORITATIVE_REVENUE']['total_gross_usd']}")

    print()
    print("=" * 78)
    print("DELIVERY RISK -- published but no file attached")
    print("=" * 78)
    for p in ps:
        if not p["has_file"]:
            print(f"  ${p['price_usd']:>7.0f}  published={p['published']}  {p['name']}")
            print(f"           {p['url']}")

    print()
    print("=" * 78)
    print("TOP 12 BY PRICE (highest ticket = highest per-sale value)")
    print("=" * 78)
    for i, p in enumerate(sorted(ps, key=lambda r: -r["price_usd"])[:12], 1):
        flag = "" if p["has_file"] else "   <<< NO FILE"
        print(f"{i:2d}. ${p['price_usd']:>7.0f}  sales={p['sales_count']}  "
              f"desc={p['description_chars']:>4}c  {p['name'][:62]}{flag}")

    print()
    print("=" * 78)
    print("PRICE BUCKETS")
    print("=" * 78)
    buckets = [("under $10", 0, 10), ("$10-29", 10, 30), ("$30-59", 30, 60),
               ("$60-99", 60, 100), ("$100+", 100, 10**9)]
    for label, lo, hi in buckets:
        n = sum(1 for p in ps if lo <= p["price_usd"] < hi)
        print(f"  {label:<10} {n:>3} products")

    print()
    print("=" * 78)
    print("DESCRIPTION DEPTH (proxy for 'complete content matching the claim')")
    print("=" * 78)
    thin = [p for p in ps if p["description_chars"] < 600]
    print(f"  under 600 chars : {len(thin)}")
    for p in thin:
        print(f"    ${p['price_usd']:>7.0f}  {p['description_chars']:>4}c  {p['name'][:60]}")


if __name__ == "__main__":
    main()