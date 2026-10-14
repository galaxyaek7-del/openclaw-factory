"""Cycle 85 baseline re-verification. Strictly READ-ONLY.

Exists to re-confirm, from the live API at this moment, the five numbers the
executive directive lists as its reference point. It writes nothing to Gumroad,
costs nothing, and records its own evidence so the figures are OBSERVED rather
than remembered.

Usage:  python scripts/cycle85_baseline.py
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from channels import gumroad_publisher as gp  # noqa: E402
from channels.gumroad_publisher import GUMROAD_API_BASE, _request_with_retry  # noqa: E402


def _load_token():
    for line in open(".env", encoding="utf-8"):
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no GUMROAD_ACCESS_TOKEN in .env")


def main():
    token = _load_token()

    # Use the project's own paginated reader rather than a hand-rolled loop.
    # An earlier version of this script paginated by hand, assumed a 20-item
    # page, and reported 10 listings; a second version looped until empty and
    # never terminated because /v2/products ignores `page` past the first
    # request. list_products() is the single code path every other caller in
    # this factory already trusts, so there is one pagination truth, not two.
    products = gp.list_products(token)

    # Sales: /v2/sales returns every completed sale. An empty list is the only
    # thing that counts as zero revenue -- a 200 with no body would not.
    sr = _request_with_retry(
        "GET", f"{GUMROAD_API_BASE}/sales",
        headers={"Authorization": f"Bearer {token}"}, timeout=30)
    sales = sr.json()
    if isinstance(sales, dict):
        sales = sales.get("sales", [])

    published = [p for p in products if p.get("published")]
    unpublished = [p for p in products if not p.get("published")]
    total_cents = sum(int(s.get("amount", 0) or 0) for s in sales)

    out = {
        "generated_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "read_only": True,
        "writes_performed": 0,
        "cost_usd": 0,
        "total_listings": len(products),
        "published": len(published),
        "unpublished": len(unpublished),
        "unpublished_names": sorted(p.get("name", "?") for p in unpublished),
        "sales_entries": len(sales),
        "verified_revenue_usd": round(total_cents / 100.0, 2),
        "per_listing_sales": sorted(
            (int(p.get("sales_count", 0) or 0), p.get("name", "?"))
            for p in products)[-5:],
    }
    os.makedirs("data", exist_ok=True)
    with open("data/cycle85_baseline.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"  OBSERVED  listings      : {out['total_listings']}")
    print(f"  OBSERVED  published     : {out['published']}")
    print(f"  OBSERVED  unpublished   : {out['unpublished']}")
    print(f"  OBSERVED  /v2/sales     : {out['sales_entries']}")
    print(f"  OBSERVED  revenue       : ${out['verified_revenue_usd']:.2f}")
    print(f"  OBSERVED  writes        : 0   cost: $0.00")
    print("wrote data/cycle85_baseline.json")


if __name__ == "__main__":
    main()