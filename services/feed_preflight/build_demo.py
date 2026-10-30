#!/usr/bin/env python3
"""Build the feed-preflight demonstration (synthetic store, no real merchant).

Writes demo_package/input_feed.csv (12 synthetic products with the faults
small sellers commonly hit, plus clean rows), runs the preflight on it, and
writes report.json and report.md. Deterministic: re-running produces the same
files. Product names, links and codes are invented; GTINs are generated with a
valid or deliberately wrong check digit and are not real products' codes.

    python services/feed_preflight/build_demo.py
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import preflight as pf  # noqa: E402

OUT = HERE / "demo_package"
COLS = ["id", "title", "description", "link", "image_link", "availability", "price", "sale_price",
        "brand", "gtin", "mpn", "identifier_exists", "condition", "color", "size"]


def gtin(body):
    """body plus its correct GS1 check digit."""
    for d in "0123456789":
        if pf.gtin_check_digit_ok(body + d):
            return body + d
    raise ValueError(body)


def wrong(code):
    return code[:-1] + str((int(code[-1]) + 1) % 10)


def rows():
    u = "https://shop.example.org/p/"
    i = "https://shop.example.org/img/"
    base = dict(description="Hand-poured soy candle, 220 g, 45-hour burn.", availability="in_stock",
                brand="Northfield Candle Co", condition="new", color="", size="", sale_price="",
                identifier_exists="", mpn="")
    r = []

    def add(**kw):
        x = dict(base)
        x.update(kw)
        r.append(x)

    add(id="NC-001", title="Cedar & Smoke Soy Candle 220 g", link=u + "1", image_link=i + "1.jpg",
        price="24.00 USD", gtin=gtin("061234500001"))
    add(id="NC-002", title="Fig Leaf Soy Candle 220 g", link=u + "2", image_link=i + "2.jpg",
        price="24,00 USD", gtin=gtin("061234500002"))                       # comma decimal
    add(id="NC-003", title="Sea Salt Soy Candle 220 g", link=u + "3", image_link=i + "3.jpg",
        price="24.00 USD", gtin=wrong(gtin("061234500003")))                # bad check digit
    add(id="NC-004", title="Amber Soy Candle 220 g", link=u + "4", image_link=i + "4.jpg",
        price="24.00 USD", availability="In Stock", gtin=gtin("061234500004"))  # wrong value spelling
    add(id="NC-005", title="Gift Set: Three Minis", link=u + "5", image_link=i + "5.jpg",
        price="39.00 USD", gtin="", mpn="", brand="")                        # no identifiers, no flag
    add(id="NC-006", title="Gift Set: Wick Trimmer", link=u + "6", image_link=i + "6.jpg",
        price="12.00 USD", gtin="", identifier_exists="no")                 # correctly flagged
    add(id="NC-007", title="Lavender Soy Candle 220 g", link="shop.example.org/p/7", image_link=i + "7.jpg",
        price="24.00 USD", gtin=gtin("061234500007"))                       # link without scheme
    add(id="NC-007", title="Lavender Soy Candle 450 g", link=u + "7b", image_link=i + "7b.jpg",
        price="38.00 USD", gtin=gtin("061234500008"))                       # duplicate id
    add(id="NC-009", title="Store Brand Tea Light x50", link=u + "9", image_link=i + "9.jpg",
        price="9.00 USD", gtin=gtin("240000000009"))                        # restricted in-store range
    add(id="NC-010", title="Winter Candle " + "Extra Long Title " * 9, link=u + "10", image_link=i + "10.jpg",
        price="26.00 USD", gtin=gtin("061234500010"))                       # title over 150
    add(id="NC-011", title="Birch Soy Candle 220 g", link=u + "11", image_link="", price="24.00 USD",
        sale_price="25.00 USD", gtin=gtin("061234500011"))                  # empty image, sale not lower
    add(id="NC-012", title="Clove Soy Candle 220 g", link=u + "12", image_link=i + "12.jpg",
        price="0.00 USD", gtin=gtin("061234500012"), identifier_exists="no")  # zero price, flag conflicts
    return r


def to_md(report):
    lines = ["# Feed preflight report (demonstration, synthetic store)", "",
             "Rows checked: %d. Rows clean: %d. Rows with errors: %d. Errors: %d. Warnings: %d." % (
                 report["rows"], report["rows_clean"], report["rows_with_errors"], report["errors"], report["warnings"]),
             "", "| Row | id | Field | Severity | What to fix |", "|---|---|---|---|---|"]
    for f in report["findings"]:
        lines.append("| %s | %s | %s | %s | %s |" % (f["row"] or "-", f["id"] or "-", f["field"], f["severity"],
                                                    f["issue"].replace("|", "/")))
    lines += ["", "Not checked by this preflight (Google decides these at review):", ""]
    lines += ["- " + x for x in report["not_checked"]]
    lines += ["", "Rules from: " + ", ".join(report["sources"]), ""]
    return "\n".join(lines)


def build():
    OUT.mkdir(exist_ok=True)
    data = rows()
    with open(OUT / "input_feed.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(data)
    report = pf.preflight(pf.read_feed((OUT / "input_feed.csv").read_text(encoding="utf-8")))
    (OUT / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "report.md").write_text(to_md(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    r = build()
    print(json.dumps({k: r[k] for k in r if k != "findings"}, indent=1))
