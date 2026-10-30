#!/usr/bin/env python3
"""Merchant Center feed preflight (Micro-B2B demonstration, 2026-10-29).

Checks a Google Merchant Center product feed (CSV or TSV export) before upload
against rules published in Google's product data specification, read on
2026-10-29:
  https://support.google.com/merchants/answer/7052112   (attributes, limits)
  https://support.google.com/merchants/answer/6324461   (GTIN rules)

Only rules taken from those pages are checked; anything Google decides at
review time (landing-page price match, policy, image content) is out of
scope and the report says so. It never invents a GTIN or edits the feed: it
reports what to fix, row by row, with the rule each finding comes from.

Reuses services/spreadsheet_normalization/engine.py for header and cell
normalisation and its credential scan (a feed with secret-shaped values is
refused, not processed).

    python services/feed_preflight/preflight.py feed.csv|feed.xml [report.json]
"""
import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "spreadsheet_normalization"))
import engine  # noqa: E402

SPEC = "https://support.google.com/merchants/answer/7052112"
GTIN_SPEC = "https://support.google.com/merchants/answer/6324461"
REQUIRED = ("id", "title", "description", "link", "image_link", "availability", "price")
AVAILABILITY = ("in_stock", "out_of_stock", "preorder", "backorder")
LIMITS = {"id": 50, "title": 150, "mpn": 70, "color": 100, "size": 100}
PRICE = re.compile(r"^(\d+(?:\.\d{1,2})?) ([A-Z]{3})$")
CONDITIONS = ("new", "refurbished", "used")


def gtin_check_digit_ok(digits):
    """GS1 mod-10 check digit, for 8, 12, 13 and 14 digit codes."""
    body, check = digits[:-1], int(digits[-1])
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


def check_gtin(raw):
    """None when acceptable, else the reason. Spaces and dashes are ignored, as Google does."""
    digits = re.sub(r"[\s-]", "", raw)
    if not digits.isdigit():
        return "GTIN must be numeric"
    if len(digits) not in (8, 12, 13, 14):
        return "GTIN must have 8, 12, 13 or 14 digits (has %d)" % len(digits)
    if not gtin_check_digit_ok(digits):
        return "GTIN check digit is wrong"
    # prefixes are read on the 13-digit form: a UPC-12 gains a leading 0,
    # a GTIN-14 loses its packaging indicator digit
    p13 = digits[1:] if len(digits) == 14 else digits.zfill(13)
    if p13.startswith(("02", "04", "2")):
        return "GTIN is in a restricted GS1 range (02, 04, 2)"
    if p13.startswith(("05", "98", "99")):
        return "GTIN is in a coupon GS1 range (05, 98, 99)"
    return None


MAX_XML_BYTES = 50 * 1024 * 1024


class UnsafeFeed(ValueError):
    pass


def read_feed_xml(text):
    """RSS 2.0 <item> or Atom <entry> feeds with Google's g: fields. Customer XML
    is untrusted: any DOCTYPE or ENTITY declaration is refused before parsing
    (entity-expansion attacks), and so is a file over MAX_XML_BYTES. Only leaf
    elements become fields; nested groups such as g:shipping are kept as one
    flattened text so they never overwrite a top-level value."""
    import xml.etree.ElementTree as ET
    if len(text.encode("utf-8")) > MAX_XML_BYTES:
        raise UnsafeFeed("XML feed larger than %d MB" % (MAX_XML_BYTES // 1024 // 1024))
    head = text[:200000].upper()
    if "<!DOCTYPE" in head or "<!ENTITY" in head:
        raise UnsafeFeed("XML feeds with a DOCTYPE or ENTITY declaration are refused")
    root = ET.fromstring(text)
    items = [e for e in root.iter() if e.tag.split("}")[-1] in ("item", "entry")]
    rows = []
    for it in items:
        row = {}
        for child in it:
            name = engine.norm_header(child.tag.split("}")[-1])
            if name == "link" and not (child.text or "").strip() and child.get("href"):
                value = child.get("href")      # Atom <link href="..."/>
            elif len(child):
                value = " ".join(t.strip() for t in child.itertext() if t.strip())
            else:
                value = child.text or ""
            row.setdefault(name, engine.norm_cell(value))
        rows.append(row)
    return rows


def read_feed(text):
    if text.lstrip().startswith("<"):
        return read_feed_xml(text)
    sample = text[:4096]
    delim = "\t" if sample.count("\t") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    return [{engine.norm_header(k): engine.norm_cell(v) for k, v in r.items() if k is not None} for r in reader]


def preflight(rows):
    secrets = engine.scan_secrets(rows)
    if not secrets["clean"]:
        return {"status": "REFUSED", "reason": "the file carries credential-like fields; remove them and resend",
                "fields": secrets["hits"]}
    findings = []

    def add(row_no, item_id, field, severity, issue, source=SPEC):
        findings.append({"row": row_no, "id": item_id or None, "field": field, "severity": severity,
                         "issue": issue, "source": source})

    headers = set(rows[0]) if rows else set()
    for col in REQUIRED:
        if col not in headers:
            add(None, None, col, "error", "required column is missing")
    ids = Counter(r.get("id", "") for r in rows if r.get("id"))
    seen_gtin = Counter((re.sub(r"[\s-]", "", r.get("gtin", "")), r.get("condition", "new") or "new",
                         r.get("color", ""), r.get("size", "")) for r in rows if r.get("gtin"))
    for n, r in enumerate(rows, start=2):  # row 1 is the header
        iid = r.get("id", "")
        for col in REQUIRED:
            if col in headers and not r.get(col):
                add(n, iid, col, "error", "required value is empty")
        for col, mx in LIMITS.items():
            if len(r.get(col, "")) > mx:
                add(n, iid, col, "error", "longer than %d characters (%d)" % (mx, len(r[col])))
        if iid and ids[iid] > 1:
            add(n, iid, "id", "error", "id is used by %d rows; each product needs its own" % ids[iid])
        av = r.get("availability", "")
        if av and av not in AVAILABILITY:
            hint = av.strip().lower().replace(" ", "_")
            if hint in AVAILABILITY:
                add(n, iid, "availability", "warning",
                    "'%s' is a spelling variant; the specification lists %s, use it exactly" % (av, hint))
            else:
                add(n, iid, "availability", "error", "'%s' is not a supported value (%s)" % (av, ", ".join(AVAILABILITY)))
        for col in ("price", "sale_price"):
            v = r.get(col, "")
            if not v:
                continue
            m = PRICE.match(v)
            if not m:
                issue = "use a number, a point for decimals and an ISO 4217 code, e.g. 15.00 USD"
                if "," in v:
                    issue = "a comma is not accepted as the decimal point; " + issue
                add(n, iid, col, "error", "'%s': %s" % (v, issue))
            elif col == "price" and float(m.group(1)) == 0:
                add(n, iid, col, "error", "a price of 0 is not accepted (except phones sold with a contract)")
        if r.get("sale_price") and r.get("price"):
            a, b = PRICE.match(r["price"]), PRICE.match(r["sale_price"])
            if a and b and a.group(2) != b.group(2):
                add(n, iid, "sale_price", "warning", "currency differs from price (%s vs %s)" % (b.group(2), a.group(2)))
            elif a and b and float(b.group(1)) >= float(a.group(1)):
                add(n, iid, "sale_price", "warning", "sale price is not below the price")
        for col in ("link", "image_link"):
            v = r.get(col, "")
            if v and not v.lower().startswith(("http://", "https://")):
                add(n, iid, col, "error", "must start with http:// or https://")
        cond = r.get("condition", "")
        if cond and cond not in CONDITIONS:
            add(n, iid, "condition", "error", "'%s' is not one of %s" % (cond, ", ".join(CONDITIONS)))
        gtin = r.get("gtin", "")
        ie = (r.get("identifier_exists") or "").lower()
        if gtin:
            why = check_gtin(gtin)
            if why:
                add(n, iid, "gtin", "error", why + "; do not guess a code, ask the manufacturer", GTIN_SPEC)
            key = (re.sub(r"[\s-]", "", gtin), cond or "new", r.get("color", ""), r.get("size", ""))
            if seen_gtin[key] > 1:
                add(n, iid, "gtin", "warning", "same GTIN and variant attributes as another row", GTIN_SPEC)
            if ie == "no":
                add(n, iid, "identifier_exists", "error", "set to 'no' while a GTIN is given; the product may be disapproved")
        elif ie != "no" and not (r.get("brand") and r.get("mpn")):
            add(n, iid, "gtin", "warning", "no GTIN and no brand+MPN pair; if the product truly has none, "
                                           "set identifier_exists to no", GTIN_SPEC)
    errors = sum(1 for f in findings if f["severity"] == "error")
    bad_rows = {f["row"] for f in findings if f["severity"] == "error" and f["row"]}
    return {
        "status": "CHECKED", "rows": len(rows), "errors": errors,
        "warnings": sum(1 for f in findings if f["severity"] == "warning"),
        "rows_with_errors": len(bad_rows), "rows_clean": len(rows) - len(bad_rows),
        "by_field": dict(Counter(f["field"] for f in findings)),
        "findings": findings,
        "not_checked": ["whether feed price and availability match the landing page and checkout",
                        "image content and policy compliance", "category-specific required attributes",
                        "account-level settings (shipping, returns, tax)"],
        "sources": [SPEC, GTIN_SPEC],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    try:
        report = preflight(read_feed(Path(argv[0]).read_text(encoding="utf-8-sig")))
    except UnsafeFeed as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}))
        return 1
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if len(argv) > 1:
        Path(argv[1]).write_text(text, encoding="utf-8")
    print(text if len(argv) == 1 else json.dumps({k: report[k] for k in report if k not in ("findings",)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
