"""Identify every 'EU AI Act' product on the account and pin the exact one
Cycle 85 selected. Read-only, costs $0, prints no credential.

Why this exists: the Cycle 85 report says "select ONLY the EU AI Act Toolkit"
in the Gumroad affiliate UI. If the account holds more than one similarly
named product, that instruction is ambiguous and could attach a 30% commission
to the wrong listing.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from channels import gumroad_publisher as gp

token = gp.load_token()
items = gp.list_products(token)

TARGET = "iaiyt"
rows = []
for x in items:
    cp = x.get("custom_permalink") or ""
    name = str(x.get("name") or "")
    if cp == TARGET or "ai act" in name.lower():
        rows.append({
            "permalink": cp,
            "price_cents": x.get("price"),
            "published": x.get("published"),
            "sales_count": x.get("sales_count"),
            "name": name,
            "id": x.get("id"),
        })

rows.sort(key=lambda r: r["permalink"] or "")

print("ALL 'EU AI ACT' PRODUCTS ON THIS ACCOUNT")
print("-" * 78)
for r in rows:
    price = (r["price_cents"] or 0) / 100
    mark = "  <== CYCLE 85 TARGET" if r["permalink"] == TARGET else ""
    print(f"  /l/{r['permalink'] or '(none)':<12} ${price:>7.2f}  "
          f"sales={r['sales_count']}  {r['name'][:52]}{mark}")
print("-" * 78)
print(f"  {len(rows)} products match 'EU AI Act'")

exact = [r for r in rows if r["permalink"] == TARGET]
print()
if len(exact) == 1:
    r = exact[0]
    print("EXACT MATCH CONFIRMED")
    print(json.dumps(r, indent=2))
else:
    print(f"PROBLEM: {len(exact)} products carry the permalink {TARGET!r}")