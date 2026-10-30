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



def norm_header(h):
    return re.sub(r"\s+", "_", str(h or "").strip().lower())


def norm_cell(v):
    if v is None:
        return ""
    return str(v).strip()


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_XLSX_UNPACKED_BYTES = 200 * 1024 * 1024


class UnreadableTable(ValueError):
    pass


def _xlsx_value(v):
    """A typed Excel cell as text: real dates become ISO dates (a time part
    is kept only when it is not midnight), numbers keep their value."""
    from datetime import datetime, date
    if isinstance(v, datetime):
        return v.date().isoformat() if (v.hour, v.minute, v.second) == (0, 0, 0) else v.isoformat(sep=" ")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return v


def read_table(path):
    """(rows, notes) from a CSV or the first sheet of an XLSX file. The offer
    takes one sheet: other sheets are reported in notes, never merged.
    Formulas are read as their stored values (data_only); a file without them
    reads as empty cells, which the QA report then shows as missing."""
    import os
    import zipfile
    from pathlib import Path
    path = Path(path)
    size = os.path.getsize(path)
    if size > MAX_UPLOAD_BYTES:
        raise UnreadableTable("file larger than %d MB" % (MAX_UPLOAD_BYTES // 1024 // 1024))
    notes = []
    if path.suffix.lower() == ".xlsx":
        try:
            with zipfile.ZipFile(path) as z:
                if sum(i.file_size for i in z.infolist()) > MAX_XLSX_UNPACKED_BYTES:
                    raise UnreadableTable("workbook expands beyond %d MB" % (MAX_XLSX_UNPACKED_BYTES // 1024 // 1024))
        except zipfile.BadZipFile:
            raise UnreadableTable("not a valid .xlsx file")
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb.worksheets[0]
            if len(wb.worksheets) > 1:
                notes.append("only the first sheet (%s) was read; other sheets: %s"
                             % (ws.title, ", ".join(s.title for s in wb.worksheets[1:])))
            it = ws.iter_rows(values_only=True)
            header = next(it, None)
            if not header:
                return [], notes
            names = [norm_cell(h) or "column_%d" % (i + 1) for i, h in enumerate(header)]
            rows = []
            for r in it:
                if r is None or all(c in (None, "") for c in r):
                    continue
                rows.append({names[i]: _xlsx_value(r[i]) if i < len(r) else None for i in range(len(names))})
        finally:
            wb.close()
        return rows, notes
    text = path.read_text(encoding="utf-8-sig", errors="strict")
    sample = text[:4096]
    delim = max((",", ";", "\t"), key=sample.count)
    import io
    return list(csv.DictReader(io.StringIO(text), delimiter=delim)), notes


_DM_OR_MD = re.compile(r"^(\d{1,2})([/-])(\d{1,2})\2(\d{4})$")
_YMD_DOT = re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$")
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def _valid(y, m, d):
    try:
        datetime(y, m, d)
        return True
    except ValueError:
        return False


def parse_date(v, order=None):
    """(value, status). status: iso (already ISO), converted, ambiguous, invalid, other.

    order is "MDY" or "DMY" for a slash/dash value whose two leading parts could
    each be a day or a month; normalize() infers it per column from values that
    settle it (a part over 12). Without an order such a value is ambiguous and is
    returned unchanged: a guessed date is worse than an unconverted one. A value
    that is not a real calendar date (month 13, 30 February) is returned
    unchanged and marked invalid, never written out as an impossible ISO date.
    """
    s = str(v or "").strip()
    if not s:
        return s, "other"
    m = _ISO.match(s)
    if m:
        y, mo, d = map(int, m.groups())
        return (s, "iso") if _valid(y, mo, d) else (s, "invalid")
    m = _YMD_DOT.match(s)
    if m:
        y, mo, d = map(int, m.groups())
        return ("%04d-%02d-%02d" % (y, mo, d), "converted") if _valid(y, mo, d) else (s, "invalid")
    m = _DM_OR_MD.match(s)
    if not m:
        return s, "other"
    a, sep, b, y = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
    if a > 12 and b > 12:
        return s, "invalid"
    if a > 12:
        mo, d = b, a
    elif b > 12:
        mo, d = a, b
    elif a == b:
        mo, d = a, b
    elif order == "MDY":
        mo, d = a, b
    elif order == "DMY":
        mo, d = b, a
    else:
        return s, "ambiguous"
    return ("%04d-%02d-%02d" % (y, mo, d), "converted") if _valid(y, mo, d) else (s, "invalid")


def infer_date_order(values):
    """MDY or DMY when the column's own values settle it, else None (also on conflict)."""
    mdy = dmy = False
    for v in values:
        m = _DM_OR_MD.match(str(v or "").strip())
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(3))
        if a > 12 and b <= 12:
            dmy = True
        elif b > 12 and a <= 12:
            mdy = True
    return "MDY" if mdy and not dmy else "DMY" if dmy and not mdy else None


def norm_date(v):
    """Single-value form kept for callers: unambiguous values convert, others
    are returned unchanged (see parse_date)."""
    return parse_date(v)[0]


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
    # Day/month order per date column, settled by the column's own values.
    raw = [{norm_header(k): norm_cell(v) for k, v in r.items()} for r in rows]
    orders = {c: infer_date_order(nr.get(c) for nr in raw) for c in date_cols if c in headers}
    # Symbols are stripped to make amounts numeric, so record which currencies a
    # column held first: $8.50 and €8,50 must not look like the same price.
    currencies = {}
    for c in currency_cols:
        if c in headers:
            seen_sym = sorted({s for nr in raw for s in re.findall(r"[$€£]", str(nr.get(c, "")))})
            currencies[c] = seen_sym
    date_counts = {"converted": 0, "ambiguous": 0, "invalid": 0}
    date_examples = {"ambiguous": [], "invalid": []}
    for nr in raw:
        for c in date_cols:
            if c in nr:
                nr[c], status = parse_date(nr[c], orders.get(c))
                if status in date_counts:
                    date_counts[status] += 1
                if status in date_examples and len(date_examples[status]) < 5:
                    date_examples[status].append(nr[c])
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
    # The same SKU in several rows (typical when merging exports) is reported,
    # never merged or removed: which row is right is the customer's decision.
    repeats = {}
    for c in sku_cols:
        if c not in headers:
            continue
        groups = {}
        for nr in out:
            if nr.get(c):
                groups.setdefault(nr[c], []).append(nr)
        for sku, grp in groups.items():
            if len(grp) > 1:
                prices = sorted({str(g.get(p)) for g in grp for p in currency_cols if p in g and g.get(p) != ""})
                repeats[sku] = {"rows": len(grp), "prices": prices, "price_conflict": len(prices) > 1}
    return {"rows": out, "qa": {
        "input_rows": len(rows), "output_rows": len(out),
        "sku_repeats": dict(list(sorted(repeats.items()))[:50]),
        "sku_price_conflicts": sum(1 for v in repeats.values() if v["price_conflict"]),
        "currency_symbols_by_column": currencies,
        "mixed_currency_columns": sorted(c for c, s in currencies.items() if len(s) > 1),
        "duplicates_removed": dupes, "rows_with_missing": missing,
        "dates_converted": date_counts["converted"],
        "dates_ambiguous_kept": date_counts["ambiguous"],
        "dates_invalid_kept": date_counts["invalid"],
        "date_examples_needing_review": date_examples,
        "date_order_inferred": orders,
        "columns": headers, "ran_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 3)}}
