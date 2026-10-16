"""Gumroad analytics fallback: parse CSV exports from the Gumroad dashboard
(BKL-004, Phase 4, 2026-10-16; sales-export layout added in Phase 5).

The factory has no API path to Gumroad listing analytics. Public sources found
in Phase 5 (web search, 2026-10-16) point to the dashboard's CSV export being a
per-purchase SALES export from the Sales tab (Purchase ID, Item Name, Purchase
Date, ...) with no page-view column; Gumroad's help pages are JS-rendered and
could not be read directly, so neither layout is verified against a real file.

So two layouts are recognised from the header row, and nothing else is guessed:
  SALES_EXPORT     one row per purchase. Gives sales, revenue, refunds and, if
                   a referrer column exists, referrers. Views are None
                   ("not in this file"), never 0.
  DAILY_AGGREGATE  Date, Product, Views, Sales, Revenue, Refunds (the Phase 4
                   directive's description).
Any other header row is refused as FORMAT_UNRECOGNIZED. Every result carries
format_verified=False until a real export has been checked.

Reads only. Its single write is its own parsed-summary file.
"""
import csv
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

COLUMN_ALIASES = {
    "date": ("date", "day"),
    "product": ("product", "product name", "product_name", "name"),
    "views": ("views", "view count", "page views"),
    "sales": ("sales", "sales count", "orders"),
    "revenue": ("revenue", "amount", "gross", "total"),
    "refunds": ("refunds", "refund count"),
}
REQUIRED_COLUMNS = ("date", "views")

SALES_ALIASES = {
    "purchase_id": ("purchase id", "sale id", "order id"),
    "product": ("item name", "product name", "product"),
    "date": ("purchase date", "sale date", "created at", "date"),
    "price": ("sale price ($)", "sale price", "price ($)", "price", "amount"),
    "refunded": ("refunded?", "refunded", "fully refunded?", "refund"),
    "referrer": ("referrer", "referrer url", "referral"),
}
SALES_REQUIRED = ("purchase_id", "product", "date")
TRUTHY = {"1", "true", "yes", "y", "refunded"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _num(value):
    s = re.sub(r"[^0-9.\-]", "", str(value or ""))
    try:
        return float(s) if s not in ("", "-", ".") else 0.0
    except ValueError:
        return 0.0


def _map(fieldnames, aliases):
    lower = {f.strip().lower(): f for f in (fieldnames or []) if f}
    mapping = {}
    for key, names in aliases.items():
        for a in names:
            if a in lower:
                mapping[key] = lower[a]
                break
    return mapping


def _widen(rng, d):
    if d:
        if rng["start"] is None or d < rng["start"]:
            rng["start"] = d
        if rng["end"] is None or d > rng["end"]:
            rng["end"] = d


class GumroadCSVParser:
    def __init__(self, csv_dir=None, parsed_path=None):
        self.csv_dir = csv_dir or os.path.join(ROOT, "data", "measurement", "gumroad_exports")
        self.parsed_path = parsed_path or os.path.join(ROOT, "data", "measurement", "gumroad_parsed.json")
        os.makedirs(self.csv_dir, exist_ok=True)

    @staticmethod
    def _map_columns(fieldnames):
        return _map(fieldnames, COLUMN_ALIASES)

    def _aggregate(self, reader, cols):
        summary = {"total_views": 0, "total_sales": 0, "total_revenue": 0.0, "total_refunds": 0,
                   "products": {}, "date_range": {"start": None, "end": None}}
        rows = []
        for row in reader:
            rec = {k: (row.get(src) or "").strip() for k, src in cols.items()}
            views, sales = int(_num(rec.get("views"))), int(_num(rec.get("sales")))
            revenue, refunds = _num(rec.get("revenue")), int(_num(rec.get("refunds")))
            summary["total_views"] += views
            summary["total_sales"] += sales
            summary["total_revenue"] = round(summary["total_revenue"] + revenue, 2)
            summary["total_refunds"] += refunds
            p = summary["products"].setdefault(rec.get("product") or "(all)", {"views": 0, "sales": 0, "revenue": 0.0})
            p["views"] += views
            p["sales"] += sales
            p["revenue"] = round(p["revenue"] + revenue, 2)
            _widen(summary["date_range"], rec.get("date"))
            rows.append(rec)
        return summary, rows

    def _sales(self, reader, cols):
        summary = {"total_views": None, "views_note": "not in a sales export",
                   "total_sales": 0, "total_revenue": 0.0, "total_refunds": 0,
                   "products": {}, "date_range": {"start": None, "end": None},
                   "top_referrers": None, "utm_campaigns": None}
        refs, utms = Counter(), Counter()
        rows = []
        for row in reader:
            rec = {k: (row.get(src) or "").strip() for k, src in cols.items()}
            if not rec.get("purchase_id"):
                continue
            refunded = rec.get("refunded", "").lower() in TRUTHY
            price = _num(rec.get("price"))
            summary["total_sales"] += 1
            summary["total_refunds"] += int(refunded)
            summary["total_revenue"] = round(summary["total_revenue"] + (0 if refunded else price), 2)
            p = summary["products"].setdefault(rec.get("product") or "(unknown)", {"views": None, "sales": 0, "revenue": 0.0})
            p["sales"] += 1
            p["revenue"] = round(p["revenue"] + (0 if refunded else price), 2)
            _widen(summary["date_range"], rec.get("date"))
            if "referrer" in cols and rec.get("referrer"):
                refs[rec["referrer"][:200]] += 1
                m = re.search(r"utm_campaign=([^&\s]+)", rec["referrer"])
                if m:
                    utms[m.group(1)] += 1
            rows.append({k: v for k, v in rec.items() if k != "purchase_id"})   # no buyer identifiers kept
        if "referrer" in cols:
            summary["top_referrers"] = refs.most_common(10)
            summary["utm_campaigns"] = dict(utms)
        return summary, rows

    def parse_export(self, csv_path: str) -> dict:
        if not os.path.exists(csv_path):
            return {"status": "FILE_NOT_FOUND", "path": csv_path, "data": None}
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            sales_cols = _map(reader.fieldnames, SALES_ALIASES)
            agg_cols = self._map_columns(reader.fieldnames)
            if all(c in sales_cols for c in SALES_REQUIRED):
                layout = "SALES_EXPORT"
                summary, rows = self._sales(reader, sales_cols)
                cols = sales_cols
            elif all(c in agg_cols for c in REQUIRED_COLUMNS):
                layout = "DAILY_AGGREGATE"
                summary, rows = self._aggregate(reader, agg_cols)
                cols = agg_cols
            else:
                return {"status": "FORMAT_UNRECOGNIZED", "path": csv_path,
                        "missing_columns": [c for c in REQUIRED_COLUMNS if c not in agg_cols],
                        "found_columns": reader.fieldnames, "data": None, "format_verified": False}
        results = {"status": "PARSED", "layout": layout, "source": "gumroad_csv_export", "file": csv_path,
                   "parsed_at": _now(), "evidence_type": "REAL", "format_verified": False,
                   "has_views": summary["total_views"] is not None,
                   "column_mapping": cols, "summary": summary, "rows": rows}
        os.makedirs(os.path.dirname(self.parsed_path), exist_ok=True)
        tmp = self.parsed_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.parsed_path)
        return results

    def latest_export_file(self):
        files = [os.path.join(self.csv_dir, n) for n in os.listdir(self.csv_dir) if n.lower().endswith(".csv")]
        return max(files, key=os.path.getmtime) if files else None

    def get_latest_analytics(self) -> dict:
        if os.path.exists(self.parsed_path):
            with open(self.parsed_path, encoding="utf-8") as f:
                return json.load(f)
        return {"status": "AWAITING_EXPORT",
                "instruction": ("Download CSV from Gumroad Dashboard -> Sales -> Export "
                                "-> Place in data/measurement/gumroad_exports/"),
                "evidence_type": "NONE", "real_evidence": False}

    def to_evidence(self) -> dict:
        analytics = self.get_latest_analytics()
        has_data = analytics.get("status") == "PARSED"
        return {"source": "gumroad_csv_parser", "timestamp": _now(),
                "confidence": 0.85 if has_data else 0.0,
                "data_url": os.path.relpath(self.parsed_path, ROOT).replace(os.sep, "/"),
                "real_evidence": has_data, "status": analytics.get("status"),
                "layout": analytics.get("layout"), "has_views": analytics.get("has_views", False),
                "format_verified": analytics.get("format_verified", False)}


if __name__ == "__main__":
    import sys
    parser = GumroadCSVParser()
    target = sys.argv[1] if len(sys.argv) > 1 else parser.latest_export_file()
    if target:
        res = parser.parse_export(target)
        print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2, ensure_ascii=False)[:4000])
    else:
        print(json.dumps(parser.to_evidence(), indent=2, ensure_ascii=False))
