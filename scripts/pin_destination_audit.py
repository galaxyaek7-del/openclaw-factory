#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Do the scheduled pins still lead to a buyable page? (2026-11-07). Read-only: HTTP GET only, paced.

    python scripts/pin_destination_audit.py [--days 14] [--json]

For every ledger row in data/pinterest_manual_posts.jsonl scheduled in the next N days (default 14):
  * the destination answers HTTP 200 (one retry with a pause: Gumroad rate-limits bursts and recovers, which is NOT a dead listing);
  * the page offers the product (schema.org availability InStock);
  * the price shown equals the catalog price (a pin that promises $29 and lands on $39 is a trust problem);
  * the pin copy in the ledger carries the product's UTM tag.
A failed fetch is UNKNOWN, never OK. Nothing is posted, edited or paid for.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "data" / "pinterest_manual_posts.jsonl"
CATALOG = ROOT / "customer_site" / "catalog.json"


def rows(path=LEDGER):
    out = []
    try:
        for ln in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
            if ln.startswith("{"):
                try:
                    out.append(json.loads(ln))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def catalog_prices(path=CATALOG):
    try:
        prods = (json.loads(Path(path).read_text(encoding="utf-8-sig")).get("data") or {}).get("products", [])
    except (OSError, ValueError):
        return {}
    return {p["id"]: p for p in prods}


def get(url, timeout=25):
    import requests
    r = requests.get(url.split("?")[0], timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (galaxy-forge destination audit)"})
    return r.status_code, r.text


def due(ledger_rows, days, today=None):
    today = today or date.today()
    out = []
    for r in ledger_rows:
        try:
            d = datetime.strptime(str(r.get("scheduled_for", ""))[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if today <= d <= today + timedelta(days=days):
            out.append(r)
    return out


def check_one(r, prods, fetch=get, pause=2.0, sleep=time.sleep):
    link = r.get("link") or ""
    res = {"offer_id": r.get("offer_id"), "scheduled_for": str(r.get("scheduled_for"))[:10], "status": "UNKNOWN", "detail": ""}
    if f"utm_content={str(r.get('offer_id', '')).lower()}-pinterest" not in link:
        res["detail"] = "the link has no utm_content tag for this product (clicks could not be attributed)"
        res["status"] = "WARN"
    st = body = None
    for attempt in (1, 2):
        try:
            st, body = fetch(link)
            if st == 200:
                break
        except Exception as e:  # noqa: BLE001
            st, body = None, ""
            res["detail"] = f"{type(e).__name__} on fetch"
        if attempt == 1:
            sleep(pause * 3)
    if st != 200:
        res["status"] = "UNKNOWN" if st is None or st == 429 else "BROKEN"
        res["detail"] = (res["detail"] + f" HTTP {st}").strip()
        return res
    exp = prods.get(r.get("offer_id"), {}).get("price_cents")
    shown = {float(x) for x in re.findall(r'"price"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)"?', body)}
    in_stock = "InStock" in body
    if not in_stock:
        res.update(status="BROKEN", detail="page does not offer the product (no schema.org InStock)")
    elif exp is not None and shown and (exp / 100) not in shown and not any(abs(x - exp / 100) < 0.01 for x in shown):
        res.update(status="BROKEN", detail=f"price shown {sorted(shown)} differs from catalog ${exp / 100}")
    elif res["status"] != "WARN":
        res.update(status="OK", detail=f"HTTP 200, InStock" + (f", price {sorted(shown)}" if shown else ", price not machine-readable"))
    sleep(pause)
    return res


def audit(days=14, today=None, fetch=get, ledger=LEDGER, catalog=CATALOG, pause=2.0, sleep=time.sleep):
    prods = catalog_prices(catalog)
    return [check_one(r, prods, fetch, pause, sleep) for r in due(rows(ledger), days, today)]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    days = int(argv[argv.index("--days") + 1]) if "--days" in argv else 14
    res = audit(days)
    if "--json" in argv:
        sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    else:
        from collections import Counter
        c = Counter(r["status"] for r in res)
        L = [f"PIN DESTINATIONS next {days} days: {len(res)} pins: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items()))]
        L += [f"  [{r['status']}] {r['offer_id']} {r['scheduled_for']}: {r['detail']}" for r in res if r["status"] != "OK"]
        sys.stdout.buffer.write(("\n".join(L) + "\n").encode("utf-8"))
    return 1 if any(r["status"] == "BROKEN" for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())
