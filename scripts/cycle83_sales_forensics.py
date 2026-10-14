"""Forensic check: is `sales: []` a REAL zero, or a parsing/early-stop artifact?

The question this answers, because "0 sales" and "we failed to read the sales
response" look identical in a report unless you check:

  1. Is /v2/sales a DOCUMENTED endpoint, and with what scope?
  2. Does the response carry success:true (i.e. the API accepted and answered)?
  3. Does the response offer a next_page cursor we failed to follow?
  4. INDEPENDENT CROSS-CHECK: do the per-product sales_count / sales_usd_cents
     fields -- which come from a DIFFERENT endpoint and a different code path --
     also report zero? If 79 products each independently report 0, then "0
     sales" does not depend on parsing /v2/sales correctly at all.
  5. Does a deliberately-invalid token behave DIFFERENTLY from a valid one?
     A real API does not answer an unauthenticated request with 200 + empty.

If (5) shows the unauthenticated request failing while ours succeeds, the
empty array is the API's genuine answer, not our misreading.

Read-only. GET only. No token value is ever printed or stored.

Run:  python scripts/cycle83_sales_forensics.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://api.gumroad.com/v2"


def _token() -> str:
    for line in open(".env", encoding="utf-8", errors="replace"):
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GUMROAD_ACCESS_TOKEN not found in .env")


def _get(url: str, token: str | None, timeout: int = 30):
    """Return (status, parsed_or_text). Never raises."""
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def _shape(raw: str) -> dict:
    try:
        d = json.loads(raw)
    except (ValueError, TypeError):
        return {"_parse_error": True, "_raw_type": type(raw).__name__}
    return d


def main() -> int:
    token = _token()
    out = {"probe": "cycle83_sales_forensics", "read_only": True}

    # ── 1/2/3: the sales endpoint itself ────────────────────────────────
    st, raw = _get(f"{API}/sales", token)
    d = _shape(raw)
    sales = d.get("sales") if isinstance(d, dict) else None
    out["sales_endpoint"] = {
        "method": "GET",
        "path": "/v2/sales",
        "documented_scope": "view_sales (per gumroad.com/api)",
        "http_status": st,
        "success_field": d.get("success") if isinstance(d, dict) else None,
        "body_top_level_keys": sorted(d.keys()) if isinstance(d, dict) else None,
        "sales_is_list": isinstance(sales, list),
        "sales_length": len(sales) if isinstance(sales, list) else None,
        # Pagination cursors. If present and not followed, a non-empty first
        # page would be an early stop. An empty array means there is nothing
        # to page through.
        "next_page_field_present": any(
            k in d for k in ("next_page_url", "next_page", "next_page_key")
        ) if isinstance(d, dict) else None,
        "next_page_value": {
            k: d.get(k) for k in ("next_page_url", "next_page", "next_page_key")
            if isinstance(d, dict) and d.get(k)
        } or None,
    }
    out["sales_endpoint"]["verdict"] = (
        "REAL_ZERO" if (st == 200 and isinstance(sales, list) and not sales
                        and d.get("success") is True)
        else "NOT_A_CONFIRMED_ZERO"
    )

    # ── 4: independent cross-check from a different endpoint ────────────
    products, page_url, pages = [], f"{API}/products", 0
    while page_url and pages < 50:
        pages += 1
        pst, praw = _get(page_url, token)
        if pst != 200:
            break
        pd = _shape(praw)
        products.extend(pd.get("products") or [])
        nxt = pd.get("next_page_url")
        page_url = "https://api.gumroad.com" + nxt if nxt and nxt.startswith("/") else nxt

    total_units = sum(int(p.get("sales_count") or 0) for p in products)
    total_usd_cents = sum(float(p.get("sales_usd_cents") or 0) for p in products)
    missing_field = sum(1 for p in products if "sales_count" not in p)
    out["independent_cross_check"] = {
        "source": "GET /v2/products (different endpoint, different code path)",
        "pages_walked": pages,
        "products": len(products),
        "sum_sales_count": total_units,
        "sum_sales_usd_cents": total_usd_cents,
        "products_missing_the_sales_count_field": missing_field,
        "verdict": ("CONSISTENT_ZERO" if (len(products) and total_units == 0
                                          and missing_field == 0)
                    else "INCONSISTENT_OR_UNAVAILABLE"),
        "why_it_matters": (
            "This total does not depend on parsing /v2/sales. If both "
            "independent sources report zero, '0 sales' is the platform's "
            "answer rather than our misreading of one response."),
    }

    # ── 5: does a bad credential actually fail? ─────────────────────────
    # Proves the empty array is the API's genuine reply and not a silent
    # failure that happens to look like success.
    st_bad, raw_bad = _get(f"{API}/sales", "definitely-not-a-real-token-000")
    d_bad = _shape(raw_bad)
    out["negative_control"] = {
        "description": "same endpoint, deliberately invalid credential",
        "http_status": st_bad,
        "success_field": d_bad.get("success") if isinstance(d_bad, dict) else None,
        "sales_is_list": isinstance(
            d_bad.get("sales"), list) if isinstance(d_bad, dict) else False,
        "verdict": ("API_REJECTS_BAD_CREDENTIAL" if st_bad != 200
                    else "API_RETURNED_200_FOR_BAD_CREDENTIAL"),
        "why_it_matters": (
            "If an invalid token gets a non-200 while ours gets 200 + "
            "success:true, then 200 means the request really was "
            "authenticated and answered."),
    }

    out["conclusion"] = {
        "verified_revenue_usd": 0.0 if (out["sales_endpoint"]["verdict"] == "REAL_ZERO"
                                        and out["independent_cross_check"]["verdict"] == "CONSISTENT_ZERO")
                              else None,
        "basis": ("COMPLETED /v2/sales query returned success:true with an "
                  "empty list and no pagination cursor, AND an independent "
                  "/v2/products walk reports 0 across all products."),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())