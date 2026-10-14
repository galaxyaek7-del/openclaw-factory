"""Establish the Day-0 baseline for the 7-day demand test.

A demand test with no baseline is unfalsifiable: if sales_count is still 0 in
seven days you cannot tell "the test failed" from "nothing was ever going to
happen anyway". This records the starting position so the end point is a
comparison, not an impression.

It snapshots, from authoritative sources only:
  * each candidate product's sales_count and sales_usd_cents (Gumroad API)
  * the account-wide /v2/sales query result and whether it completed
  * the count of products published (a listing going down is a signal too)
  * the local indexation state of the free guides, since those are the only
    assets this factory can actually get in front of a stranger right now

Read-only. GET only, $0. Writes only its own snapshot file.

Run:  python scripts/demand_test_baseline.py
Out:  data/demand_test_baseline.json
"""

from __future__ import annotations

import datetime
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "demand_test_baseline.json"

# The three candidates. Changing this list changes what the test measures,
# so it is explicit rather than inferred.
CANDIDATES = [
    ("iaiyt", "EU AI Act Compliance Toolkit", 15500),
    ("adyvd", "Turo Guest Dispute Toolkit", 2900),
    ("kaooj", "CCPA Compliance Action Kit for Small Business", 2900),
]

GUIDE_URLS = [
    "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/free-guides.html",
    "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/guide-turo-invoice-dispute.html",
]


def _token() -> str:
    for line in open(ROOT / ".env", encoding="utf-8", errors="replace"):
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GUMROAD_ACCESS_TOKEN not found")


def _get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:  # noqa: BLE001
        return 0, None


def main() -> int:
    token = _token()
    auth = {"Authorization": "Bearer " + token}

    products, url = [], "https://api.gumroad.com/v2/products"
    while url:
        st, raw = _get(url, auth)
        if st != 200:
            break
        d = json.loads(raw.decode("utf-8", "replace"))
        products.extend(d.get("products") or [])
        nxt = d.get("next_page_url")
        url = "https://api.gumroad.com" + nxt if nxt and nxt.startswith("/") else nxt

    by_id = {}
    for p in products:
        ident = (p.get("short_url") or "").rstrip("/").split("/")[-1]
        by_id[ident] = p

    snap = {
        "probe": "demand_test_baseline",
        "read_only": True,
        "cost_usd": 0,
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "candidates": [],
        "account": {},
        "free_assets": [],
    }

    for sid, label, expect_cents in CANDIDATES:
        p = by_id.get(sid)
        snap["candidates"].append({
            "short_id": sid,
            "expected_label": label,
            "expected_price_cents": expect_cents,
            "found_in_catalog": p is not None,
            "title": (p or {}).get("name"),
            "price_cents": (p or {}).get("price"),
            "published": (p or {}).get("published"),
            "url": (p or {}).get("short_url"),
            "sales_count_DAY0": (p or {}).get("sales_count"),
            "sales_usd_cents_DAY0": (p or {}).get("sales_usd_cents"),
            "status": "OBSERVED" if p else "UNKNOWN -- not in catalog",
        })

    st, raw = _get("https://api.gumroad.com/v2/sales", auth)
    doc = None
    try:
        doc = json.loads(raw.decode("utf-8", "replace")) if raw else None
    except Exception:  # noqa: BLE001
        doc = None
    sales = doc.get("sales") if isinstance(doc, dict) else None
    snap["account"] = {
        "sales_endpoint_http": st,
        "success": (doc or {}).get("success") if isinstance(doc, dict) else None,
        "sales_count_DAY0": len(sales) if isinstance(sales, list) else None,
        "query_status": "OBSERVED" if (st == 200 and isinstance(sales, list))
                        else "UNKNOWN -- query did not complete cleanly",
        "products_total": len(products),
        "products_published": sum(1 for p in products if p.get("published")),
    }

    for url in GUIDE_URLS:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                snap["free_assets"].append(
                    {"url": url, "http": r.status, "reachable": True,
                     "bytes": len(r.read())})
        except Exception as e:  # noqa: BLE001
            snap["free_assets"].append(
                {"url": url, "http": None, "reachable": False,
                 "error": type(e).__name__})

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=2, ensure_ascii=False)

    print("captured_at:", snap["captured_at"])
    for c in snap["candidates"]:
        print(f"  {c['short_id']}  sales_count={c['sales_count_DAY0']}"
              f"  published={c['published']}  ${(c['price_cents'] or 0)/100:.0f}")
    print("account sales_count_DAY0:", snap["account"]["sales_count_DAY0"],
          "| query:", snap["account"]["query_status"])
    for a in snap["free_assets"]:
        print(f"  asset http={a['http']} {a['url'].split('/')[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())