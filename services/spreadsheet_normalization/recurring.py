#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recurring (monthly) form of the spreadsheet normalization service (backlog B34, 2026-10-29).

Spec: docs/factory/SERVICE_SPECS_B19_B21.md, B19. Adds, around engine.normalize
(unchanged):
  * a column profile per buyer, saved once and reused each month, checked against
    the headers of every new file;
  * the secret scan enforced: a file engine.scan_secrets flags is refused before
    any processing (the engine itself only reports);
  * a month-over-month change report: row counts, keys added/removed, totals per
    amount column -- and a reconciliation check that each total equals the sum of
    that month's cleaned rows.

Nothing here contacts a buyer, stores their file beyond the call, or charges.
A refused or failed run returns status REFUSED/FAILED with reasons, never output rows.
"""
import json
import os
import re

from engine import norm_header, normalize, scan_secrets

PROFILE_FIELDS = ("buyer_id", "key_col", "amount_cols", "date_cols", "sku_cols")


def save_profile(profile, profiles_dir):
    missing = [k for k in PROFILE_FIELDS if not profile.get(k) and profile.get(k) != []]
    if missing:
        raise ValueError(f"profile missing: {missing}")
    if not re.match(r"^[A-Za-z0-9_-]{1,64}$", profile["buyer_id"]):
        raise ValueError("buyer_id must be 1-64 letters, digits, '_' or '-'")
    clean = {k: profile[k] for k in PROFILE_FIELDS}
    for k in ("amount_cols", "date_cols", "sku_cols"):
        clean[k] = [norm_header(c) for c in clean[k]]
    clean["key_col"] = norm_header(clean["key_col"])
    os.makedirs(profiles_dir, exist_ok=True)
    path = os.path.join(profiles_dir, clean["buyer_id"] + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=1)
    return clean


def load_profile(buyer_id, profiles_dir):
    with open(os.path.join(profiles_dir, buyer_id + ".json"), encoding="utf-8") as f:
        return json.load(f)


def _totals(rows, cols):
    out, non_numeric = {}, {}
    for c in cols:
        s, bad = 0.0, 0
        for r in rows:
            v = r.get(c)
            if isinstance(v, (int, float)):
                s += v
            elif v not in ("", None):
                bad += 1
        out[c] = round(s, 2)
        non_numeric[c] = bad
    return out, non_numeric


def change_report(current_rows, previous_rows, profile):
    key = profile["key_col"]
    cur_keys = {r.get(key) for r in current_rows if r.get(key) not in ("", None)}
    prev_keys = {r.get(key) for r in previous_rows if r.get(key) not in ("", None)}
    cur_tot, cur_bad = _totals(current_rows, profile["amount_cols"])
    prev_tot, _ = _totals(previous_rows, profile["amount_cols"])
    return {
        "rows": {"previous": len(previous_rows), "current": len(current_rows),
                 "change": len(current_rows) - len(previous_rows)},
        "keys_added": sorted(cur_keys - prev_keys),
        "keys_removed": sorted(prev_keys - cur_keys),
        "totals": {c: {"previous": prev_tot[c], "current": cur_tot[c],
                       "change": round(cur_tot[c] - prev_tot[c], 2)} for c in profile["amount_cols"]},
        "non_numeric_amounts": cur_bad,
    }


def run_month(rows, profile, previous_rows=None):
    """One monthly delivery. previous_rows: last month's CLEANED rows, or None."""
    secrets = scan_secrets(rows)
    if not secrets["clean"]:
        return {"status": "REFUSED", "reasons": ["file contains credential-like fields: " + ", ".join(secrets["hits"])]}
    if not rows:
        return {"status": "FAILED", "reasons": ["empty file"]}
    headers = {norm_header(h) for h in rows[0].keys()}
    needed = {profile["key_col"], *profile["amount_cols"], *profile["date_cols"], *profile["sku_cols"]}
    absent = sorted(needed - headers)
    if absent:
        return {"status": "FAILED", "reasons": [f"columns in the buyer profile are missing from this file: {absent}"]}
    result = normalize(rows, sku_cols=tuple(profile["sku_cols"]), currency_cols=tuple(profile["amount_cols"]),
                       date_cols=tuple(profile["date_cols"]))
    qa = result["qa"]
    checks = {"rows_reconcile": qa["input_rows"] == qa["output_rows"] + qa["duplicates_removed"]}
    report = change_report(result["rows"], previous_rows or [], profile) if previous_rows is not None else None
    if report:
        recomputed, _ = _totals(result["rows"], profile["amount_cols"])
        checks["totals_reconcile"] = all(report["totals"][c]["current"] == recomputed[c]
                                         for c in profile["amount_cols"])
    status = "OK" if all(checks.values()) else "FAILED"
    reasons = [k for k, ok in checks.items() if not ok]
    return {"status": status, "reasons": reasons, "rows": result["rows"], "qa": qa,
            "checks": checks, "change_report": report,
            "note": "founder QA sign-off required before delivery"}
