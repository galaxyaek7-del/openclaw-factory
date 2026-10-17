"""Read-only Gumroad sales monitor.

Prints the one honest commercial metric this factory can read autonomously:
completed sales and gross/refunded amounts on the seller account. It never
writes a product, never sends anything, and never touches the filesystem.

Usage:
    python scripts/check_gumroad_sales.py

Exit code is 0 on a successful read, 2 when the credential is missing, 3 when
the API cannot be reached. It never invents a number: if the sales list cannot
be read, it says so rather than printing zero.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.gumroad.com/v2/sales"


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_PAGES = 200   # safety cap; a page holds a few sales, so this is far above today's volume


def _token() -> str | None:
    if os.environ.get("GUMROAD_ACCESS_TOKEN"):
        return os.environ["GUMROAD_ACCESS_TOKEN"].strip()
    try:
        # Repo-root .env, not the caller's working directory.
        with open(os.path.join(ROOT, ".env"), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("GUMROAD_ACCESS_TOKEN="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        return None
    return None


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def fetch_sales(token: str, get=_get) -> dict:
    """Every page of /v2/sales. The endpoint is paginated (next_page_url);
    reading only the first page would silently under-count once sales grow.
    Returns {"success", "sales", "pages", "complete"}; complete is False only
    when MAX_PAGES was hit, so a partial count is never presented as total."""
    sales, url, pages = [], API, 0
    while url and pages < MAX_PAGES:
        payload = get(url, token)
        pages += 1
        if not payload.get("success", False):
            return {**payload, "pages": pages}
        sales.extend(payload.get("sales") or [])
        nxt = payload.get("next_page_url")
        url = ("https://api.gumroad.com" + nxt) if nxt and nxt.startswith("/") else nxt
    return {"success": True, "sales": sales, "pages": pages, "complete": not url}


def summarize(payload: dict) -> dict:
    sales = payload.get("sales") or []
    gross_cents = 0
    refunded = 0
    products = {}
    for s in sales:
        price = s.get("price") or 0
        if s.get("refunded"):
            refunded += 1
        else:
            gross_cents += price
        name = s.get("product_name") or "(unknown)"
        products[name] = products.get(name, 0) + 1
    return {
        "count": len(sales),
        "paid_count": len(sales) - refunded,
        "refunded_count": refunded,
        "gross_usd": round(gross_cents / 100.0, 2),
        "by_product": products,
    }


def main() -> int:
    token = _token()
    if not token:
        print(json.dumps({"error": "GUMROAD_ACCESS_TOKEN not found in .env"}, indent=2))
        return 2
    try:
        payload = fetch_sales(token)
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": f"HTTP {e.code}", "readable": False}, indent=2))
        return 3
    except Exception as e:  # noqa: BLE001 - report any transport failure honestly
        print(json.dumps({"error": str(e), "readable": False}, indent=2))
        return 3

    if not payload.get("success", False):
        print(json.dumps({"error": "API returned success=false", "readable": False,
                          "raw": payload}, indent=2))
        return 3

    print(json.dumps({"readable": True, "pages_read": payload["pages"], "complete": payload["complete"],
                      **summarize(payload)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
