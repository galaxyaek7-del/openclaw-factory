"""Cycle 81 — honest delivery-integrity audit across the whole real catalog.

Corrects an error made earlier in THIS cycle. `gumroad_catalog_truth.py`
inferred `has_file` from the `files` key of the LIST response. The list
endpoint truncates `files`, so the inference wrongly flagged the $155 flagship
as having no deliverable. Verified false: GET /v2/products/iaiyt returns 2 real
attached PDFs. Lesson applied: an inferred boolean from a list payload is not
evidence. This module only trusts the per-product detail payload.

Read-only. One GET per product. No writes, no purchases, $0.

Run:  python scripts/cycle81_delivery_audit.py
Out:  data/cycle81_delivery_audit.json
"""

from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.gumroad.com/v2/products"
SNAPSHOT = "data/cycle81_gumroad_catalog_truth.json"
OUT = "data/cycle81_delivery_audit.json"


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


def main() -> int:
    snap = json.load(io.open(SNAPSHOT, encoding="utf-8-sig"))
    token = _token()
    rows, errors = [], []

    for meta in snap["products"]:
        short = meta["url"].rstrip("/").split("/")[-1] if meta["url"] else None
        if not short:
            continue
        st, body = _get(f"{API}/{urllib.parse.quote(short, safe='')}", token)
        if st != 200:
            errors.append({"short_id": short, "http_status": st, "body": body[:200]})
            continue
        p = json.loads(body).get("product", {})
        files = p.get("files") or []
        rows.append({
            "short_id": short,
            "name": p.get("name"),
            "price_usd": (p.get("price") or 0) / 100.0,
            "published": p.get("published"),
            "sales_count": p.get("sales_count"),
            "sales_usd_cents": p.get("sales_usd_cents"),
            "file_count": len(files),
            "file_bytes": sum(int(f.get("size") or 0) for f in files),
            "file_names": [f.get("name") or f.get("file_name") for f in files],
            "description_chars": len(p.get("description") or ""),
            "url": p.get("short_url"),
        })
        time.sleep(0.05)  # be polite; 0 cost, avoids hammering the API

    deliverable = [r for r in rows if r["file_count"] > 0]
    published_no_file = [r for r in rows if r["published"] and r["file_count"] == 0]
    paid_no_file = [r for r in published_no_file if r["price_usd"] > 0]
    tiny = [r for r in deliverable if r["file_bytes"] < 20_000]

    out = {
        "probe": "cycle81_delivery_audit",
        "read_only": True,
        "source": "GET /v2/products/:id per product (detail payload only)",
        "corrects": "has_file inference in gumroad_catalog_truth.py used the "
                    "LIST payload, whose `files` array is truncated. The $155 "
                    "flagship was wrongly flagged as undeliverable. Not true.",
        "checked": len(rows),
        "fetch_errors": errors,
        "verdicts": {
            "publishable_and_deliverable": len(deliverable),
            "published_but_zero_files": len(published_no_file),
            "PRICED_ABOVE_ZERO_BUT_UNDELIVERABLE": len(paid_no_file),
            "deliverable_under_20KB": len(tiny),
        },
        "undeliverable_paid_products": paid_no_file,
        "zero_file_products": published_no_file,
        "tiny_files": tiny,
        "revenue": {
            "total_units_sold": sum(r["sales_count"] or 0 for r in rows),
            "total_gross_usd": round(
                sum(float(r["sales_usd_cents"] or 0) for r in rows) / 100.0, 2),
        },
        "products": sorted(rows, key=lambda r: -r["price_usd"]),
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print(json.dumps({k: out[k] for k in
                      ("checked", "verdicts", "revenue")}, indent=2, ensure_ascii=False))
    if paid_no_file:
        print("\nPRICED BUT UNDELIVERABLE:")
        for r in paid_no_file:
            print(f"  ${r['price_usd']:.0f}  {r['name']}")
    print(f"\ntiny (<20KB) deliverables: {len(tiny)}")
    for r in tiny[:15]:
        print(f"  ${r['price_usd']:>6.0f} {r['file_bytes']:>7}B  {r['name'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())