"""Cycle 81 — full Gumroad catalog + revenue truth enumeration (READ-ONLY).

Corrects a documented, propagated false belief: `data/gumroad_catalog_verified.json`
records an "anomaly" that the seller API "returns only 10 products (identical on
page params 1/2/3, verified 2026-10-10)". That conclusion was wrong. The
endpoint does paginate -- but only via the opaque cursor in `next_page_url`,
not via `?page=N`. Passing page numbers returns the same first page, which is
what produced the false anomaly. This script walks the real cursor.

Read-only. GET only. Never creates, enables, updates, or archives anything.

Run:  python scripts/gumroad_catalog_truth.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API = "https://api.gumroad.com/v2/products"


def _token() -> str:
    for line in open(".env", encoding="utf-8", errors="replace"):
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GUMROAD_ACCESS_TOKEN not found in .env")


def _get(url: str, token: str, timeout: int = 30):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def fetch_all(token: str) -> tuple[list, list]:
    """Walk next_page_url to exhaustion. Returns (products, page_log)."""
    products: list = []
    log: list = []
    url, page = API, 0
    while url and page < 50:  # 50 is a runaway guard, not a business limit
        page += 1
        st, body = _get(url, token)
        log.append({"page": page, "http_status": st, "url": url})
        if st != 200:
            log[-1]["error"] = body[:200]
            break
        d = json.loads(body)
        batch = d.get("products") or []
        products.extend(batch)
        log[-1]["products_in_page"] = len(batch)
        nxt = d.get("next_page_url")
        # Gumroad returns next_page_url as a ROOT-RELATIVE path
        # ("/v2/products?page_key=..."), not an absolute URL. Prefixing is
        # required or urllib raises "unknown url type" -- which is very likely
        # why earlier sessions concluded the API "returns only 10 products".
        url = "https://api.gumroad.com" + nxt if nxt and nxt.startswith("/") else nxt
        log[-1]["has_next"] = bool(url)
    return products, log


def main() -> int:
    token = _token()
    products, log = fetch_all(token)

    live, deleted = [], []
    for p in products:
        row = {
            "id": p.get("id"),
            "name": p.get("name"),
            "price_usd": (p.get("price") or 0) / 100.0,
            "formatted_price": p.get("formatted_price"),
            "published": p.get("published"),
            "sales_count": p.get("sales_count"),
            "sales_usd": p.get("sales_usd_cents"),
            "url": p.get("short_url"),
            "has_file": bool(p.get("files") or p.get("file_info")),
            "description_chars": len(p.get("description") or ""),
        }
        (deleted if p.get("deleted") else live).append(row)

    live.sort(key=lambda r: (-(r["sales_usd"] or 0), -(r["price_usd"] or 0)))
    total_units = sum(r["sales_count"] or 0 for r in live)
    total_usd = round(sum(float(r["sales_usd"] or 0) for r in live) / 100.0, 2)

    out = {
        "probe": "gumroad_catalog_truth",
        "read_only": True,
        "method": "cursor pagination via next_page_url (NOT ?page=N)",
        "page_log": log,
        "total_products_seen": len(products),
        "live_products": len(live),
        "deleted_products": len(deleted),
        "AUTHORITATIVE_REVENUE": {
            "note": "sales_usd is Gumroad's own reported gross, from the API. Not an estimate.",
            "total_units_sold": total_units,
            "total_gross_usd": total_usd,
            "payouts": "see gumroad_payout_diagnostic.py -- /v2/payouts is real and returns []",
        },
        "products": live,
        "deleted_products_detail": deleted,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())