#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Gumroad delivery audit (read-only, 2026-10-22).

For every product on the Gumroad account: is it published, what file types
does a buyer actually receive, and does the live description promise a file
type that is not attached (e.g. "spreadsheet", "PDF cost planner")?

Why: GPSR EU Seller Action Kit (fetmu) promises "PDF guide + PDF cost planner"
and its guide's chapter 7 points to a "companion .xlsx", but only the guide
PDF is attached. data/catalog.json recorded attachments as UNKNOWN because
the list endpoint's file_info is often empty; GET /v2/products/:id returns
each file's type.

GET requests only. Never edits, publishes or uploads. The access token is
never printed or written.

    python scripts/gumroad_delivery_audit.py            # writes reports/GUMROAD_DELIVERY_AUDIT_<date>.json
    python scripts/gumroad_delivery_audit.py --stdout   # print only
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SHEET_TYPES = {"xlsx", "xls", "csv", "ods"}
ARCHIVE_TYPES = {"zip", "rar", "7z"}
# A paid product whose files total under this many bytes is almost certainly a
# page or two (the $49 FBA "workbook" ships a 3,726-byte PDF). Review, not verdict.
THIN_BYTES = 10_000
# A description promises a spreadsheet deliverable when it names one; "tracker"
# alone is ambiguous (often a PDF table), so it only counts with sheet words.
SHEET_PROMISE = re.compile(r"\b(xlsx|xls|spreadsheet|workbook|excel|google sheets?|csv|-sheet\b|four-sheet|multi-sheet)", re.I)
COUNTED_FILES = re.compile(r"you (?:receive|get)\s*:?\s*([^.]{0,160})", re.I)


def plain(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def classify(product):
    """Pure: product dict from GET /v2/products/:id -> audit row."""
    files = product.get("files") or []
    types = [str(f.get("filetype") or "?").lower() for f in files]
    text = plain(product.get("description"))
    promise = SHEET_PROMISE.findall(text)
    received = COUNTED_FILES.search(text)
    issues = []
    if product.get("published") and not files and not product.get("custom_delivery_url"):
        issues.append("PUBLISHED_WITHOUT_DELIVERABLE")
    if promise and not (set(types) & SHEET_TYPES):
        # A ZIP may contain the spreadsheet; the API cannot show what is inside.
        issues.append("ZIP_CONTENTS_UNVERIFIED" if set(types) & ARCHIVE_TYPES
                      else "PROMISES_SPREADSHEET_NOT_ATTACHED")
    total = sum(int(f.get("size") or 0) for f in files)
    if files and (product.get("price") or 0) > 0 and total < THIN_BYTES:
        issues.append("THIN_DELIVERABLE")
    if received:
        n_promised = len(re.findall(r"\bpdf\b|\bxlsx\b|\bcsv\b|\btemplate\b|\bplanner\b", received.group(1), re.I))
        if n_promised > len(files) and len(files) <= 1:
            issues.append("PROMISES_MORE_FILES_THAN_ATTACHED")
    if any("preview" in str(f.get("name") or "").lower() for f in files):
        issues.append("PREVIEW_FILE_DELIVERED")
    return {
        "slug": (product.get("short_url") or "").rstrip("/").split("/")[-1],
        "name": product.get("name"),
        "published": bool(product.get("published")),
        "price_usd": (product.get("price") or 0) / 100,
        "attached_types": types,
        "attached_bytes": sum(int(f.get("size") or 0) for f in files),
        "promise_terms": sorted({p.lower() for p in promise}),
        "you_receive": received.group(1).strip()[:160] if received else None,
        "issues": issues,
    }


def fetch_all(pause=0.3):
    from channels import gumroad_publisher as g
    token = g.load_token()
    rows = []
    for p in g.list_products(token):
        url = ("https://api.gumroad.com/v2/products/" + urllib.parse.quote(p["id"], safe="")
               + "?" + urllib.parse.urlencode({"access_token": token}))
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                rows.append(classify(json.load(r)["product"]))
        except Exception as e:  # never leak the token in the message
            rows.append({"slug": (p.get("short_url") or "").rstrip("/").split("/")[-1], "name": p.get("name"),
                         "published": bool(p.get("published")), "issues": ["FETCH_FAILED"],
                         "error": type(e).__name__})
        time.sleep(pause)
    return rows


def summarize(rows):
    counts = {}
    for r in rows:
        for i in r["issues"]:
            counts[i] = counts.get(i, 0) + 1
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "method": "GET /v2/products + /v2/products/:id",
            "products": len(rows), "published": sum(1 for r in rows if r["published"]),
            "issue_counts": counts, "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    out = summarize(fetch_all())
    if args.stdout:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    path = ROOT / "reports" / f"GUMROAD_DELIVERY_AUDIT_{datetime.now(timezone.utc).date()}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("products", "published", "issue_counts")}, ensure_ascii=False))
    print("written:", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
