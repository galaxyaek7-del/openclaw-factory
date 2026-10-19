#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cycle 104 repair: give the B12-007 digital-inventory workbook real formulas.

ROOT CAUSE
----------
`file_testing_engine` fails `books/batch12/B12-007_digital_inventory.xlsx` with
"ZERO formulas across every sheet -- a workbook product with no formulas is a
static grid, not a working tool". The workbook was generated as four input
sheets with a single EXAMPLE row each and a README; nothing computed anything.
Every other B12 workbook has at least a TOTAL cell, so this is a genuine defect
in this one artifact, not a policy disagreement.

SAFE FIX
--------
Additive only: a new leading `Dashboard` sheet of real, live formulas that
reference the existing sheets. No existing sheet, cell, style or example row is
touched; re-running is idempotent (the sheet is rebuilt from scratch each run).

DISCLOSED LIMIT
---------------
This removes the hard "no formulas" defect. It does NOT make the product
publishable on its own: the guide PDF is still 273 words against a 1,900-word
floor at the $19.00 price, so the content-quality layer still fails. Nothing
here is allowed to change that verdict.

Dry-run by default. `--apply` writes the file. `--backup DIR` keeps the
pre-repair bytes for before/after evidence.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path

FACTORY = Path(__file__).resolve().parent.parent
TARGET = FACTORY / "books" / "batch12" / "B12-007_digital_inventory.xlsx"
OUT_DIR = FACTORY / "reports" / "CYCLE104"

# (label, formula, number_format) -- every range is generous so rows added by
# the customer are picked up, and every count subtracts the single EXAMPLE row
# the template ships with. A negative count is therefore explicit evidence the
# user deleted the example row, not a silent wrong number.
ROWS = [
    ("Accounts logged (excl. EXAMPLE)", '=COUNTA(Accounts!A2:A500)-1', "0"),
    ("Accounts still to close", '=COUNTIF(Accounts!E2:E500,"Delete")', "0"),
    ("Files marked Delete", '=COUNTIF(Files!D2:D500,"Delete")', "0"),
    ("Files marked Archive", '=COUNTIF(Files!D2:D500,"Archive")', "0"),
    ("Subscriptions to cancel", '=COUNTIF(Subscriptions!D2:D500,"Cancel")', "0"),
    ("Current subscription spend / month (USD)", "=SUM(Subscriptions!B2:B500)", "#,##0.00"),
    ("Subscriptions cancelled", '=COUNTA(Subscriptions!E2:E500)-1', "0"),
    ("Backups not yet restore-tested", '=COUNTIF(Backups!D2:D500,"Unverified")', "0"),
    ("Backups verified restorable", '=COUNTIF(Backups!D2:D500,"Verified")', "0"),
    ("30-day progress: closed items / total touched",
     '=IF((COUNTIF(Accounts!E2:E500,"Delete")+COUNTIF(Files!D2:D500,"Delete")'
     '+COUNTIF(Subscriptions!D2:D500,"Cancel"))=0,0,'
     '(COUNTA(Accounts!F2:F500)+COUNTA(Files!E2:E500)+COUNTA(Subscriptions!E2:E500))'
     '/(COUNTIF(Accounts!E2:E500,"Delete")+COUNTIF(Files!D2:D500,"Delete")'
     '+COUNTIF(Subscriptions!D2:D500,"Cancel")))', "0%"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(apply: bool, backup_dir: Path | None) -> dict:
    import openpyxl
    from openpyxl.styles import Font

    before_hash = sha256(TARGET)
    wb = openpyxl.load_workbook(TARGET, data_only=False)
    sheets_before = list(wb.sheetnames)
    formulas_before = sum(
        1 for ws in wb.worksheets for row in ws.iter_rows()
        for c in row if isinstance(c.value, str) and c.value.startswith("="))

    if "Dashboard" in wb.sheetnames:
        idx = wb.sheetnames.index("Dashboard")
        wb.remove(wb["Dashboard"])
        ws = wb.create_sheet("Dashboard", 0)
    else:
        idx = 0
        ws = wb.create_sheet("Dashboard", 0)

    ws["A1"] = "B12-007 Digital Inventory \u2014 live summary"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = ("Every number below is a live formula over the other sheets. "
                "Counts subtract the single EXAMPLE row the template ships with, "
                "so a negative value means you deleted it.")
    ws["A2"].font = Font(italic=True, size=9)
    ws["A4"] = "Metric"
    ws["B4"] = "Value"
    ws["A4"].font = ws["B4"].font = Font(bold=True)

    for i, (label, formula, fmt) in enumerate(ROWS, start=5):
        ws.cell(row=i, column=1, value=label)
        cell = ws.cell(row=i, column=2, value=formula)
        cell.number_format = fmt

    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 14
    ws["A%d" % (5 + len(ROWS) + 1)] = ("Reminder from the README: never store passwords "
                                       "in this file \u2014 record only where a password lives.")

    result = {
        "target": str(TARGET.relative_to(FACTORY)),
        "before_sha256": before_hash,
        "sheets_before": sheets_before,
        "formulas_before": formulas_before,
        "formulas_added": len(ROWS),
        "sheet_index_restored_to": idx,
        "applied": False,
    }
    if not apply:
        wb.close()
        return result

    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TARGET, backup_dir / TARGET.name)

    wb.save(TARGET)
    wb.close()
    wb2 = openpyxl.load_workbook(TARGET, data_only=False)
    formulas_after = sum(
        1 for ws in wb2.worksheets for row in ws.iter_rows()
        for c in row if isinstance(c.value, str) and c.value.startswith("="))
    result["sheets_after"] = list(wb2.sheetnames)
    result["formulas_after"] = formulas_after
    result["after_sha256"] = sha256(TARGET)
    result["applied"] = True
    result["applied_at"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat(timespec="seconds")
    wb2.close()
    return result


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backup", default=None)
    ap.add_argument("--write-report", action="store_true")
    a = ap.parse_args()

    if not TARGET.exists():
        print("target missing: %s" % TARGET, file=sys.stderr)
        return 2

    bdir = Path(a.backup) if a.backup else None
    res = build(a.apply, bdir)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    if a.write_report:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "B12-007_WORKBOOK_FORMULA_REPAIR.json").write_text(
            json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        print("written: %s" % (OUT_DIR / "B12-007_WORKBOOK_FORMULA_REPAIR.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
