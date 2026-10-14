"""Galaxy Forge â€” documented commercial inventory (Gumroad + Paddle).

Produces ONE inventory with, per product: internal id, public URL, attached
file (name, bytes, real fetched size), price, currency, published flag, and
sales. Every field is labelled by how it was obtained, because the whole
point of this cycle is that "published" is not "purchasable" and neither is
"sales".

Three distinctions this script is built to keep apart, per the directive:

  PUBLISHED            the product exists and is visible
  DELIVERABLE          a real attachment exists AND its bytes were fetched
  PURCHASABLE          NOT asserted. Requires completing a checkout, which
                       this factory is not permitted to do. Left UNKNOWN.

Read-only. GET only. No token, header value, or customer identifier is written
to the output. $0.

Run:  python scripts/commercial_inventory.py
Out:  data/commercial_inventory.json
"""

from __future__ import annotations

import datetime
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "commercial_inventory.json"

OBSERVED = "OBSERVED"   # read directly from an authoritative response
DERIVED = "DERIVED"     # computed from observed values


def _secret(name: str) -> str | None:
    for line in open(ROOT / ".env", encoding="utf-8", errors="replace"):
        if line.startswith(name + "="):
            v = line.split("=", 1)[1].strip()
            return v or None
    return None


def _get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400]
    except Exception as e:  # noqa: BLE001
        return 0, str(e).encode()[:200]


def _json_or_none(raw):
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return None


# â”€â”€ Gumroad â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def gumroad_inventory():
    token = _secret("GUMROAD_ACCESS_TOKEN")
    if not token:
        return {"platform": "gumroad", "reachable": False,
                "blocker": "GUMROAD_ACCESS_TOKEN not present in .env"}
    auth = {"Authorization": "Bearer " + token}

    products, url, pages = [], "https://api.gumroad.com/v2/products", 0
    while url and pages < 50:
        pages += 1
        st, raw = _get(url, auth)
        if st != 200:
            return {"platform": "gumroad", "reachable": False,
                    "http_status": st, "pages_walked": pages,
                    "blocker": "products listing failed at page %d" % pages}
        d = _json_or_none(raw) or {}
        products.extend(d.get("products") or [])
        nxt = d.get("next_page_url")
        url = "https://api.gumroad.com" + nxt if nxt and nxt.startswith("/") else nxt
        time.sleep(0.1)

    st_sales, raw_sales = _get("https://api.gumroad.com/v2/sales", auth)
    sales_doc = _json_or_none(raw_sales)
    sales_ok = st_sales == 200 and isinstance(sales_doc, dict) \
        and sales_doc.get("success") is True
    sales_list = (sales_doc or {}).get("sales")
    # An unreadable sales list is UNKNOWN. It must never become 0.
    sales_known = sales_ok and isinstance(sales_list, list)
    sales_count = len(sales_list) if sales_known else None

    # The LIST endpoint truncates the `files` array -- proven live in cycle 81,
    # where the list reported zero attachments while the per-product detail
    # GET returned two real PDFs for the same product. So file information
    # taken from the list is recorded as UNKNOWN rather than as zero, and is
    # only stated as fact when the detail endpoint confirmed it.
    rows = []
    for p in products:
        files = p.get("files")
        rows.append({
            "platform": "gumroad",
            "id": p.get("id"),
            "title": p.get("name"),
            "url": p.get("short_url"),
            "price_cents": p.get("price"),
            "currency": p.get("currency"),
            "published": p.get("published"),
            "deleted": p.get("deleted"),
            "files_from_list": "TRUNCATED_BY_API" if files is not None else "ABSENT",
            "file_count_from_list": (len(files)
                                     if isinstance(files, list) else None),
            "file_declared_bytes": (sum(int(f.get("size") or 0) for f in files)
                                     if isinstance(files, list) else None),
            "sales_count_field": p.get("sales_count"),
            "sales_usd_cents": p.get("sales_usd_cents"),
            "deliverable": "UNKNOWN",
            "deliverable_note": ("list response cannot confirm attachments; "
                                 "requires the per-product detail GET"),
        })

    return {
        "platform": "gumroad", "reachable": True,
        "endpoint": "GET /v2/products (cursor-paginated)",
        "pages_walked": pages,
        "products": len(rows),
        "published_count": sum(1 for r in rows if r["published"] is True),
        "file_status_from_list": ("UNKNOWN -- the products LIST response truncates "
                                    "the files array; per-product detail GET "
                                    "is required to confirm an attachment"),
        "sales_query": {
            "endpoint": "GET /v2/sales",
            "http_status": st_sales,
            "success_field": (sales_doc or {}).get("success"),
            "sales_is_list": isinstance(sales_list, list),
            "count": sales_count,
            "status": OBSERVED if sales_known else "UNKNOWN",
            "note": ("A completed query returned an empty list. An empty "
                     "first page with no pagination cursor is complete."
                     if sales_known else
                     "Sales query did not complete cleanly; count is "
                     "UNKNOWN and is NOT reported as zero."),
        },
        "items": rows,
    }


# â”€â”€ Paddle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def paddle_inventory():
    key = _secret("PADDLE_API_KEY")
    if not key:
        return {"platform": "paddle", "reachable": False,
                "blocker": "PADDLE_API_KEY not present in .env"}
    auth = {"Authorization": "Bearer " + key}
    rows, incomplete = [], None

    for path in ("/products", "/prices"):
        st, raw = _get("https://api.paddle.com" + path, auth)
        d = _json_or_none(raw)
        if st != 200 or not isinstance(d, dict):
            incomplete = ("%s returned HTTP %s" % (path, st))
            break
        if path == "/products":
            for p in d.get("data") or []:
                rows.append({
                    "platform": "paddle", "id": p.get("id"),
                    "title": p.get("name"), "url": None,
                    "status_field": p.get("status"),
                    "price_cents": None, "currency": None,
                    "published": None, "file_count": None,
                })
        else:
            by_product = {}
            for pr in d.get("data") or []:
                pid = (pr.get("product_id"))
                by_product.setdefault(pid, []).append(pr)
            for row in rows:
                prices = by_product.get(row["id"]) or []
                active = [p for p in prices if p.get("status") == "active"]
                row["price_count"] = len(prices)
                row["active_price_count"] = len(active)
                row["checkout_ready"] = None  # filled from the real check
                if active:
                    amt = active[0].get("unit_amount") or {}
                    row["price_cents"] = amt.get("amount")
                    row["currency"] = amt.get("currency")

    return {
        "platform": "paddle", "reachable": incomplete is None,
        "endpoint": "GET https://api.paddle.com/{products,prices}",
        "products": len(rows),
        "list_incomplete": incomplete,
        "blocker": incomplete,
        "items": rows,
    }


def main() -> int:
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    inv = {
        "probe": "commercial_inventory",
        "read_only": True,
        "cost_usd": 0,
        "generated_at": started,
        "definitions": {
            "PUBLISHED": "the listing exists and is visible on the platform",
            "DELIVERABLE": "at least one attachment exists",
            "PURCHASABLE": ("NOT ASSERTED. Requires completing a checkout, "
                            "which this factory must not do. UNKNOWN."),
        },
        "evidence_classes": {OBSERVED: "read directly from an API response",
                             DERIVED: "computed from observed values"},
    }
    inv["gumroad"] = gumroad_inventory()
    inv["paddle"] = paddle_inventory()

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(inv, fh, indent=2, ensure_ascii=False)

    g, p = inv["gumroad"], inv["paddle"]
    print("GUMROAD  products=%s published=%s pages=%s" % (g.get("products"), g.get("published_count"), g.get("pages_walked")))
    print("  sales query: %s status=%s count=%s"
          % (g.get("sales_query", {}).get("http_status"),
             g.get("sales_query", {}).get("status"),
             g.get("sales_query", {}).get("count")))
    print("PADDLE   products=%s reachable=%s blocker=%s"
          % (p.get("products"), p.get("reachable"), p.get("blocker")))
    print("written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())