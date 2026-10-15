"""Cycle 81 Phase 1: verify the reported baseline and product identifiers.

The directive names /l/iaiyi, while earlier cycles recorded /l/iaiyt. A
transposed slug is exactly the kind of thing that causes the wrong product to be
edited, so identity is resolved against the live catalog before anything is
touched.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from channels import gumroad_publisher as gp  # noqa: E402

token = [l.split("=", 1)[1].strip() for l in open(".env", encoding="utf-8")
         if l.startswith("GUMROAD_ACCESS_TOKEN=")][0]
prods = gp.list_products(token)

print(f"catalog size (OBSERVED): {len(prods)}")
pub = [p for p in prods if p.get("published")]
print(f"published    (OBSERVED): {len(pub)}")
print(f"unpublished  (OBSERVED): {len(prods) - len(pub)}")
print(f"total sales_count (OBSERVED): {sum(p.get('sales_count') or 0 for p in prods)}")

sales_raw = gp._request_with_retry(
    "GET", "https://api.gumroad.com/v2/sales",
    headers={"Authorization": f"Bearer {token}"}, timeout=30).json()
sales = sales_raw.get("sales", []) if isinstance(sales_raw, dict) else sales_raw
cents = sum(int(s.get("amount", 0) or 0) for s in sales)
print(f"/v2/sales entries (OBSERVED): {len(sales)}")
print(f"verified revenue (OBSERVED): ${cents/100.0:.2f}")

by_slug = {}
for p in prods:
    # The catalog exposes `short_url`, not `url`. An earlier version of this
    # script looked for `url`, matched nothing, and would have reported all
    # five identifiers as NOT FOUND -- a false alarm that reads exactly like
    # "these products do not exist".
    url = p.get("short_url") or ""
    if "/l/" in url:
        by_slug[url.rsplit("/l/", 1)[1].split("?")[0]] = p

print("\n--- slug identity check (transposition matters) ---")
for slug in ("iaiyi", "iaiyt", "wteork", "bfhpzl", "fgruzn"):
    p = by_slug.get(slug)
    if p is None:
        print(f"  /l/{slug:8s} NOT FOUND in catalog")
    else:
        print(f"  /l/{slug:8s} id={p.get('id')}  ${p.get('price',0)/100:.2f}  "
              f"published={p.get('published')}  {p.get('name','')[:46]}")

print("\n--- every live listing whose slug is near 'iai' ---")
for slug, p in by_slug.items():
    if "iai" in slug.lower():
        print(f"  /l/{slug}  {p.get('name')}  ${p.get('price',0)/100:.2f}")

out = {
    "probe": "cycle81_baseline_verification",
    "generated_utc": None,
    "total_listings": len(prods),
    "published": len(pub),
    "unpublished": len(prods) - len(pub),
    "sales_entries": len(sales),
    "verified_revenue_usd": round(cents / 100.0, 2),
    "writes_performed": 0,
    "slug_identity": {s: by_slug.get(s, {}).get("id") for s in
                      ("iaiyi", "iaiyt", "wteork", "bfhpzl", "fgruzn")},
}
json.dump(out, open("data/cycle81_baseline_verification.json", "w",
                    encoding="utf-8"), indent=2, ensure_ascii=False)
print("\nwrote data/cycle81_baseline_verification.json")