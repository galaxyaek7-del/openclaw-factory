"""Resolve the REAL product URL for the Cycle 85 target.

The Cycle 85 report cited https://aekraft.gumroad.com/l/iaiyt as the product
link. The live API shows no product carries that permalink. Either the URL is
wrong or the listing changed. This resolves what is actually true before that
error is repeated into an affiliate invitation.

Read-only, costs $0, prints no credential.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from channels import gumroad_publisher as gp

token = gp.load_token()
items = gp.list_products(token)

print("URL-BEARING FIELDS ON THE $155 EU AI ACT TOOLKIT")
print("=" * 74)
target = None
for x in items:
    name = str(x.get("name") or "")
    if "EU AI Act Compliance Toolkit" in name and (x.get("price") or 0) == 15500:
        target = x
        break

if not target:
    print("NOT FOUND at $155 -- do not publish any URL until resolved")
    raise SystemExit(1)

for k in ("name", "id", "custom_permalink", "short_url", "landing_url",
          "preview_url", "url", "formatted_price", "price", "published",
          "sales_count"):
    print(f"  {k:<20} {target.get(k)!r}")

print()
print("=" * 74)
print("RESOLVED TARGET")
print("=" * 74)
permalink = target.get("custom_permalink")
print(json.dumps({
    "name": target.get("name"),
    "id": target.get("id"),
    "custom_permalink": permalink,
    "price_cents": target.get("price"),
    "published": target.get("published"),
    "sales_count": target.get("sales_count"),
    "short_url": target.get("short_url"),
    "landing_url": target.get("landing_url"),
    "preview_url": target.get("preview_url"),
}, indent=2))

print()
print("SIBLING 'EU AI ACT' LISTINGS -- all share a name prefix, all $0 sales")
print("-" * 74)
for x in items:
    name = str(x.get("name") or "")
    if "AI Act" in name:
        print(f"  ${(x.get('price') or 0)/100:>7.2f}  {name[:66]}")

Path("data/cycle85_target_product.json").write_text(
    json.dumps({"resolved_target": {
        "name": target.get("name"),
        "id": target.get("id"),
        "custom_permalink": permalink,
        "price_cents": target.get("price"),
        "published": target.get("published"),
        "sales_count": target.get("sales_count"),
    }, "read_only": True, "cost_usd": 0}, indent=2),
    encoding="utf-8")
print("\nwrote data/cycle85_target_product.json")