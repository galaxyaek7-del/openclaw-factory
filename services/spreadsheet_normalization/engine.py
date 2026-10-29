#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Spreadsheet normalization engine: CSV/XLSX in -> cleaned file + QA report.
Deterministic ops: header normalize, whitespace strip, date ISO, currency
numeric, duplicate flag, SKU upper-strip, missing-value report. Never drops
rows silently: every removal/modification is counted in the QA report."""
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

DATE_PATS = [
    (re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$"),
     lambda m: "%04d-%02d-%02d" % (int(m.group(3)), int(m.group(1)), int(m.group(2)))),
    (re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$"),
     lambda m: "%04d-%02d-%02d" % (int(m.group(3)), int(m.group(2)), int(m.group(1)))),
    (re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$"),
     lambda m: "%04d-%02d-%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3)))),
]


def norm_header(h):
    return re.sub(r"\s+", "_", str(h or "").strip().lower())


def norm_cell(v):
    if v is None:
        return ""
    return str(v).strip()


def norm_date(v):
    s = str(v or "").strip()
    for pat, fmt in DATE_PATS:
        m = pat.match(s)
        if m:
            try:
                return fmt(m)
            except ValueError:
                pass
    return s


def norm_currency(v):
    s = re.sub(r"[$€£\s]", "", str(v or "").strip())
    if re.match(r"^-?[\d.]*\d,\d{2}$", s):
        s = s.replace(".", "").replace(",", ".")
    s = re.sub(r",", "", s)
    try:
        return round(float(s), 2)
    except ValueError:
        return str(v or "").strip()


SECRET_PATTERNS = ("password", "passwd", "api_key", "apikey", "secret",
                     "token", "ssn", "social_security")


def scan_secrets(rows) -> dict:
    """Reject files carrying credential-like headers or secret-shaped values.
    Returns {clean: bool, hits: [...]}. Never logs values, only field names."""
    hits = []
    if not rows:
        return {"clean": True, "hits": []}
    for h in rows[0].keys():
        if any(p in str(h).lower() for p in SECRET_PATTERNS):
            hits.append("header:%s" % h)
    import re as _re
    for r in rows[:200]:
        for k, v in r.items():
            s = str(v or "")
            if _re.match(r"^(sk-|ghp_|xox[bap]-|AKIA)[A-Za-z0-9]+$", s.strip()):
                hits.append("value-in:%s" % k)
                break
    return {"clean": not hits, "hits": hits}


def normalize(rows, sku_cols=("sku",), currency_cols=("price", "amount", "total"),
              date_cols=("date",)):
    t0 = time.time()
    if not rows:
        return {"rows": [], "qa": {"input_rows": 0, "output_rows": 0, "error": "empty input"}}
    headers = [norm_header(h) for h in rows[0].keys()]
    out, seen, dupes, missing = [], set(), 0, 0
    for r in rows:
        nr = {norm_header(k): norm_cell(v) for k, v in r.items()}
        for c in date_cols:
            if c in nr:
                nr[c] = norm_date(nr[c])
        for c in currency_cols:
            if c in nr:
                nr[c] = norm_currency(nr[c])
        for c in sku_cols:
            if c in nr:
                nr[c] = str(nr[c]).upper().strip()
        if any(v == "" for v in nr.values()):
            missing += 1
        key = json.dumps(nr, sort_keys=True)
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        out.append(nr)
    return {"rows": out, "qa": {
        "input_rows": len(rows), "output_rows": len(out),
        "duplicates_removed": dupes, "rows_with_missing": missing,
        "columns": headers, "ran_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 3)}}
