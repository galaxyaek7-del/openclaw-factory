#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B13-001 Renovation Allowance & Change-Order Control - workbook builder.

Deterministic, $0, no network. Writes into books/batch13/.

The product is arithmetic, so every headline number is a formula: paid money is
summed from the payment log, approved changes are summed from the change-order
log, and the projected final cost is paid + unpaid committed + forecast to
complete. Nothing a buyer must trust is a typed total.

Sheet helpers are imported from the batch-12 builder rather than copied: the
colour language (white = fill me, blue = computed, yellow = EXAMPLE) and the
header/border conventions must stay identical across the catalogue.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from build_batch12_xlsx import (  # noqa: E402
    EX_FILL,
    FORMULA_FILL,
    HDR_FILL,
    HDR_FONT,
    THIN,
    WRAP,
    _paint_formulas,
    _sheet,
)

OUT = ROOT / "books" / "batch13"
OUT.mkdir(parents=True, exist_ok=True)
FILENAME = "B13-001_renovation_allowance_control.xlsx"

MONEY = '"$"#,##0.00'
MONEY0 = '"$"#,##0'
PCT = '0.0%'
DATE = "yyyy-mm-dd"

CATEGORIES = ["Design & permits", "Demolition", "Structure", "Electrical",
              "Plumbing", "HVAC", "Millwork", "Surfaces", "Tile & flooring",
              "Paint & finish", "Appliances", "Landscape", "Other"]

COST_HEADERS = [
    "Line", "Category", "What it covers", "Original budget",
    "Original committed", "Approved changes", "Revised budget",
    "Committed total", "Paid to date", "Unpaid committed",
    "Forecast to complete", "Projected final", "Variance vs revised", "Status",
]

# (line, category, description, budget, committed, forecast)
COST_EXAMPLE = [
    ("K-01", "Demolition", "Strip kitchen, remove a non-load-bearing partition", 3000, 2800, 0),
    ("K-02", "Millwork", "Cabinet package, delivered and installed", 12000, 12500, 0),
    ("K-03", "Surfaces", "Countertop allowance, made when the slab was chosen", 7500, 7500, 0),
    ("K-04", "Tile & flooring", "Floor tile plus installation labour", 6000, 5900, 550),
    ("K-05", "Electrical", "Rewire, plus one added circuit (change order)", 4500, 4800, 0),
    ("K-06", "Paint & finish", "Painting and trim, not yet contracted", 3000, 0, 3750),
    ("K-07", "Design & permits", "Design fee and building permit", 1200, 1200, 0),
    ("K-08", "Appliances", "Range, hood, dishwasher - not ordered yet", 5000, 0, 5600),
    ("K-09", "Other", "Project management fee", 2800, 2800, 0),
]

CHANGE_HEADERS = ["CO #", "Date", "Line", "What changed", "Amount",
                  "Approved?", "Amount that counts"]
CHANGE_EXAMPLE = [
    ("CO-01", "2026-05-20", "K-03", "Countertop selection above the allowance", 1700, "Yes", None),
    ("CO-02", "2026-06-04", "K-05", "Added kitchen circuit required by inspection", 600, "Yes", None),
    ("CO-03", "2026-06-18", "K-06", "Upgraded paint finish - not signed yet", 450, "No", None),
]

ALLOW_HEADERS = ["Allowance #", "Line", "Item", "Allowance in contract",
                 "Chosen selection", "Difference", "Credit already received",
                 "Credit still owed to you", "Change order #", "Status"]
ALLOW_EXAMPLE = [
    ("A-01", "K-03", "Countertops", 7500, 9200, None, 0, None, "CO-01", None),
    ("A-02", "K-06", "Lighting", 1200, 400, None, 300, None, "", None),
    ("A-03", "K-05", "Plumbing fixtures", 1500, 1900, None, 0, None, "", None),
]

PAY_HEADERS = ["Date", "Line", "Paid to", "Amount", "Method", "Note"]
PAY_EXAMPLE = [
    ("2026-05-06", "K-01", "Demo crew", 1400, "Bank transfer", "50% deposit"),
    ("2026-05-18", "K-02", "Cabinet supplier", 6250, "Card", "50% on order"),
    ("2026-05-22", "K-03", "Stone fabricator", 2250, "Bank transfer", "30% on template"),
    ("2026-06-01", "K-05", "Electrician", 2400, "Bank transfer", "First invoice"),
    ("2026-05-02", "K-07", "City permits office", 1200, "Card", "Permit issued"),
    ("2026-06-02", "K-09", "Project manager", 2800, "Bank transfer", "Final fee"),
]

CONT_HEADERS = ["Date", "What the reserve paid for", "Amount", "Approved by", "Note"]
CONT_EXAMPLE = [
    ("2026-05-12", "Hidden rot behind the sink wall", 900, "Owner", "Photos filed"),
    ("2026-06-03", "Code-required outlet upgrade", 1200, "Owner", "Electrician letter filed"),
]


def _start_here(wb):
    ws = wb.active
    ws.title = "Start Here"
    lines = [
        ("Renovation Allowance & Change-Order Control", True),
        ("", False),
        ("This workbook answers one question your budget spreadsheet cannot: what will this project actually cost me, given what I have already signed and what I still owe back?", False),
        ("", False),
        ("How to use it", True),
        ("1. Setup - project name, contingency reserve, currency. Ten minutes.", False),
        ("2. Cost Control - one row per budget line. Type the original budget and what you have signed. The rest is calculated.", False),
        ("3. Payments - every payment, one row. 'Paid to date' on Cost Control is summed from here, never typed.", False),
        ("4. Change Orders - every change with its own number. Only rows marked Approved count, and they raise the revised budget automatically.", False),
        ("5. Allowances - items priced as a spending allowance before the actual product is chosen (tile, lighting, counters). This sheet is where silent overruns and forgotten credits show up.", False),
        ("6. Contingency - the reserve and what has been drawn from it. It is not a slush fund.", False),
        ("7. Summary - the four numbers that matter, plus checks that tell you what to fix.", False),
        ("8. Assumptions - write down what is excluded. An estimate is only honest with its exclusions next to it.", False),
        ("", False),
        ("Colour code", True),
        ("White cells: you fill them in. Blue cells: calculated - do not overwrite. Yellow rows: EXAMPLE data - overwrite or delete them.", False),
        ("", False),
        ("What this workbook is not", True),
        ("It is not legal, tax or financial advice, and it does not replace your contract. Allowance, change-order and payment terms are governed by the contract you signed - check it, and check with a qualified professional where the stakes justify it.", False),
        ("", False),
        ("A note on the example numbers", True),
        ("The yellow rows describe a $45,000 kitchen renovation that ends up projected $6,500 over its revised budget. The guide walks through exactly those numbers. Delete the examples once you understand them.", False),
    ]
    ws["A1"] = lines[0][0]
    ws["A1"].font = Font(bold=True, size=15)
    row = 3
    for text, bold in lines[1:]:
        cell = ws.cell(row=row, column=1, value=text)
        cell.alignment = WRAP
        if bold:
            cell.font = Font(bold=True, size=11)
        row += 1
    ws.column_dimensions["A"].width = 118
    return ws


def _setup(wb):
    ws = _sheet(wb, "Setup", ["Setting", "Your value", "Notes"], [
        ["Project name", "Kitchen renovation (EXAMPLE)", "Anything you will recognise later"],
        ["Property address", "", "Optional"],
        ["Currency symbol", "$", "Used in the labels only"],
        ["Contingency reserve (USD)", 4500, "EXAMPLE: 10% of a $45,000 line budget. Research puts 10-20% as a floor and 25-30% for structural work."],
        ["Today's date", "2026-06-20", "Update when you review the sheet"],
        ["Who approves change orders", "Owner", "Write the name, not the role, if more than one person can approve"],
        ["Who approves contingency draws", "Owner", "Same: a name"],
        ["Review cadence", "Monthly, plus after every signed change order", "The review is what makes the numbers true"],
    ], [34, 44, 78], None, example_rows=0)
    ws["B5"].number_format = MONEY
    ws["B6"].number_format = DATE
    for cell in ("B9", "B10"):
        ws[cell].fill = EX_FILL
    return ws


def _cost_control(wb, setup_contingency="Setup!$B$5"):
    rows = []
    for line, cat, desc, budget, committed, forecast in COST_EXAMPLE:
        rows.append([line, cat, desc, budget, committed, None, None, None, None,
                     None, forecast, None, None, None])
    for r in range(len(rows) + 1, 41):
        rows.append([None] * 14)
    ws = _sheet(wb, "Cost Control", COST_HEADERS, rows,
                [9, 20, 46, 15, 16, 15, 15, 15, 14, 15, 17, 15, 16, 12],
                {3: MONEY0, 4: MONEY0, 5: MONEY0, 6: MONEY0, 7: MONEY0, 8: MONEY0,
                 9: MONEY0, 10: MONEY0, 11: MONEY0, 12: MONEY0, 13: MONEY0},
                example_rows=len(COST_EXAMPLE))
    for r in range(2, 41):
        ws.cell(row=r, column=6,
                value=f'=IF($A{r}="","",SUMIF(\'Change Orders\'!$C$2:$C$21,$A{r},\'Change Orders\'!$G$2:$G$21))')
        ws.cell(row=r, column=7,
                value=f'=IF($A{r}="","",N($D{r})+N($F{r}))')
        ws.cell(row=r, column=8,
                value=f'=IF($A{r}="","",N($E{r})+N($F{r}))')
        ws.cell(row=r, column=9,
                value=f'=IF($A{r}="","",SUMIF(Payments!$B$2:$B$31,$A{r},Payments!$D$2:$D$31))')
        ws.cell(row=r, column=10,
                value=f'=IF($A{r}="","",MAX(0,N($H{r})-N($I{r})))')
        ws.cell(row=r, column=12,
                value=f'=IF($A{r}="","",N($I{r})+N($J{r})+N($K{r}))')
        ws.cell(row=r, column=13,
                value=f'=IF($A{r}="","",N($G{r})-N($L{r}))')
        ws.cell(row=r, column=14,
                value=(f'=IF($A{r}="","",IF(N($L{r})>N($G{r}),"OVER",'
                       f'IF(N($L{r})=N($G{r}),"ON PLAN","UNDER")))'))
    dv = DataValidation(type="list", formula1='"' + ",".join(CATEGORIES) + '"',
                        allow_blank=True, showErrorMessage=True,
                        errorTitle="Category", error="Pick a category from the list.")
    ws.add_data_validation(dv)
    dv.add("B2:B41")
    dv2 = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0",
                         allow_blank=True, showErrorMessage=True,
                         errorTitle="Amount", error="Enter 0 or more.")
    ws.add_data_validation(dv2)
    for col in ("D", "E", "K"):
        dv2.add(f"{col}2:{col}41")
    return ws


def _change_orders(wb):
    rows = [[c, d, line, what, amount, approved, None]
            for c, d, line, what, amount, approved, _ in CHANGE_EXAMPLE]
    for _ in range(len(rows) + 1, 21):
        rows.append([None] * 7)
    ws = _sheet(wb, "Change Orders", CHANGE_HEADERS, rows,
                [10, 13, 9, 52, 14, 12, 18],
                {1: DATE, 4: MONEY0, 6: MONEY0}, example_rows=len(CHANGE_EXAMPLE))
    for r in range(2, 21):
        ws.cell(row=r, column=7,
                value=(f'=IF(OR($A{r}="",$E{r}=""),"",'
                       f'IF(LOWER(TRIM($F{r}))="yes",N($E{r}),0))'))
    dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True,
                        showErrorMessage=True, errorTitle="Approved?",
                        error="Type Yes only when the change is signed and approved.")
    ws.add_data_validation(dv)
    dv.add("F2:F21")
    dv2 = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0",
                         allow_blank=True, showErrorMessage=True,
                         errorTitle="Amount", error="Enter 0 or more.")
    ws.add_data_validation(dv2)
    dv2.add("E2:E21")
    return ws


def _allowances(wb):
    rows = [[a, line, item, allow, chosen, None, received, None, co, None]
            for a, line, item, allow, chosen, _x, received, _y, co, _z in ALLOW_EXAMPLE]
    for _ in range(len(rows) + 1, 21):
        rows.append([None] * 10)
    ws = _sheet(wb, "Allowances", ALLOW_HEADERS, rows,
                [13, 9, 26, 18, 17, 13, 18, 22, 14, 38],
                {3: MONEY0, 4: MONEY0, 5: MONEY0, 6: MONEY0, 7: MONEY0},
                example_rows=len(ALLOW_EXAMPLE))
    for r in range(2, 21):
        ws.cell(row=r, column=6,
                value=f'=IF($A{r}="","",IF(OR($D{r}="",$E{r}=""),"",N($E{r})-N($D{r})))')
        ws.cell(row=r, column=8,
                value=(f'=IF($A{r}="","",IF(NOT(ISNUMBER($F{r})),"",'
                       f'IF($F{r}<0,MAX(0,-N($F{r})-N($G{r})),0)))'))
        ws.cell(row=r, column=10,
                value=(f'=IF($A{r}="","",IF(NOT(ISNUMBER($F{r})),"",'
                       f'IF($F{r}>0,IF($I{r}="","Overage - no change order #",'
                       f'IF(COUNTIFS(\'Change Orders\'!$A$2:$A$21,$I{r},'
                       f'\'Change Orders\'!$F$2:$F$21,"Yes")>0,'
                       f'"Overage - change order on file",'
                       f'"Overage - CO not approved")),'
                       f'IF(N($H{r})>0,"Credit still owed to you","Settled"))))'))
    dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0",
                        allow_blank=True, showErrorMessage=True,
                        errorTitle="Amount", error="Enter 0 or more.")
    ws.add_data_validation(dv)
    for col in ("D", "E", "G"):
        dv.add(f"{col}2:{col}21")
    return ws


def _payments(wb):
    rows = [[d, line, who, amount, method, note] for d, line, who, amount, method, note in PAY_EXAMPLE]
    for _ in range(len(rows) + 1, 31):
        rows.append([None] * 6)
    ws = _sheet(wb, "Payments", PAY_HEADERS, rows,
                [13, 9, 28, 14, 16, 46], {0: DATE, 3: MONEY0},
                example_rows=len(PAY_EXAMPLE))
    dv = DataValidation(type="decimal", operator="greaterThan", formula1="0",
                        allow_blank=True, showErrorMessage=True,
                        errorTitle="Amount", error="Enter the amount paid, more than 0.")
    ws.add_data_validation(dv)
    dv.add("D2:D31")
    return ws


def _contingency(wb):
    rows = [[d, what, amount, who, note] for d, what, amount, who, note in CONT_EXAMPLE]
    for _ in range(len(rows) + 1, 21):
        rows.append([None] * 5)
    ws = _sheet(wb, "Contingency", CONT_HEADERS, rows,
                [13, 46, 14, 14, 40], {0: DATE, 2: MONEY0},
                example_rows=len(CONT_EXAMPLE))
    ws["G1"] = "Reserve remaining"
    ws["G1"].font, ws["G1"].fill = HDR_FONT, HDR_FILL
    ws["G2"] = '=IF(Setup!$B$5="","",N(Setup!$B$5)-SUM($C$2:$C$21))'
    ws["G2"].number_format = MONEY0
    ws["G2"].fill = FORMULA_FILL
    ws["H1"] = "Drawn so far"
    ws["H1"].font, ws["H1"].fill = HDR_FONT, HDR_FILL
    ws["H2"] = "=SUM($C$2:$C$21)"
    ws["H2"].number_format = MONEY0
    ws["H2"].fill = FORMULA_FILL
    dv = DataValidation(type="decimal", operator="greaterThan", formula1="0",
                        allow_blank=True, showErrorMessage=True,
                        errorTitle="Amount", error="Enter the amount drawn, more than 0.")
    ws.add_data_validation(dv)
    dv.add("C2:C21")
    return ws


def _assumptions(wb):
    rows = [
        ["1", "Excluded", "Temporary storage and rental furniture", "Not in any line", "Add a line if this becomes real"],
        ["2", "Excluded", "Landscaping and exterior work", "Out of scope this phase", ""],
        ["3", "Assumption", "Owner supplies appliances at retail price", "", "Quotes may move"],
        ["4", "Allowance", "Countertops priced at $7,500 until the slab is chosen", "A-01", "Reconcile in Allowances"],
        ["5", "Risk", "House built before 1980 - hidden conditions likely", "", "Reserve sized at 10%; structural work may justify 25-30%"],
    ]
    for _ in range(len(rows) + 1, 26):
        rows.append([None] * 5)
    return _sheet(wb, "Assumptions", ["#", "Type", "Statement", "Where it lives", "Owner's note"],
                  rows, [6, 14, 58, 18, 46], None, example_rows=len(rows))


def _summary(wb):
    """Every headline total is a formula, and each formula reads its inputs by
    named row. The first draft used positional B-references and two of them
    pointed at the wrong row - one at itself. Excel showed a blank instead of
    an error, which is exactly the silent-wrong-number failure this product
    exists to prevent, so rows are named here instead of counted."""
    ws = wb.create_sheet("Summary")
    ws["A1"] = "Renovation cost control - summary"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = '=IF(Setup!$B$3="","(project name not set)",Setup!$B$3)'
    ws["A2"].font = Font(italic=True)

    R = {
        "original": 4, "approved_cos": 5, "revised": 6, "committed": 7,
        "paid": 8, "unpaid": 9, "forecast": 10, "projected": 11,
        "variance": 12, "committed_pct": 13, "reserve": 14,
        "allow_over": 15, "credits": 16, "cos_pending": 17,
        "lines_over": 18, "all_in": 19,
    }
    rows = [
        ("Original budget (sum of lines)", "original", "=SUM('Cost Control'!$D$2:$D$41)", MONEY0),
        ("Approved change orders", "approved_cos", "=SUM('Change Orders'!$G$2:$G$21)", MONEY0),
        ("Revised budget", "revised", "=B{original}+B{approved_cos}", MONEY0),
        ("Committed total", "committed", "=SUM('Cost Control'!$H$2:$H$41)", MONEY0),
        ("Paid to date", "paid", "=SUM('Cost Control'!$I$2:$I$41)", MONEY0),
        ("Unpaid committed", "unpaid", "=SUM('Cost Control'!$J$2:$J$41)", MONEY0),
        ("Forecast to complete", "forecast", "=SUM('Cost Control'!$K$2:$K$41)", MONEY0),
        ("Projected final cost", "projected", "=SUM('Cost Control'!$L$2:$L$41)", MONEY0),
        ("Variance vs revised budget", "variance", "=B{revised}-B{projected}", MONEY0),
        ("Committed as % of revised budget", "committed_pct", '=IF(B{revised}=0,"",B{committed}/B{revised})', PCT),
        ("Contingency reserve remaining", "reserve", "=Contingency!$G$2", MONEY0),
        ("Allowance overruns (all)", "allow_over", '=SUMIF(Allowances!$F$2:$F$21,">0")', MONEY0),
        ("Allowance credits still owed to you", "credits", "=SUM(Allowances!$H$2:$H$21)", MONEY0),
        ("Change orders awaiting signature", "cos_pending", '=COUNTIF(\'Change Orders\'!$F$2:$F$21,"No")', "0"),
        ("Lines already over their revised budget", "lines_over", '=COUNTIF(\'Cost Control\'!$N$2:$N$41,"OVER")', "0"),
        ("All-in plan (revised budget + reserve)", "all_in", "=B{revised}+B{reserve}", MONEY0),
    ]
    for label, key, template, fmt in rows:
        ws.cell(row=R[key], column=1, value=label).font = Font(bold=True)
        cell = ws.cell(row=R[key], column=2, value=template.format(**R))
        cell.number_format = fmt
        cell.fill = FORMULA_FILL

    ws["A21"] = "Checks - fix anything that is not OK"
    ws["A21"].font = Font(bold=True, size=12)
    checks = [
        ("Any payment recorded against a line that does not exist?",
         '=IF(SUMPRODUCT((Payments!$D$2:$D$31<>"")*(COUNTIF(\'Cost Control\'!$A$2:$A$41,Payments!$B$2:$B$31)=0))>0,'
         '"FIX: payment against an unknown line","OK")'),
        ("Any allowance overage with no approved change order?",
         '=IF(COUNTIF(Allowances!$J$2:$J$21,"Overage - no change order #")'
         '+COUNTIF(Allowances!$J$2:$J$21,"Overage - CO not approved")>0,'
         '"FIX: "&COUNTIF(Allowances!$J$2:$J$21,"Overage - no change order #")'
         '+COUNTIF(Allowances!$J$2:$J$21,"Overage - CO not approved")'
         '&" overage(s) with no approved change order","OK")'),
        ("Paid more than committed on any line?",
         '=IF(SUMPRODUCT((\'Cost Control\'!$I$2:$I$41>\'Cost Control\'!$H$2:$H$41)*'
         '(\'Cost Control\'!$A$2:$A$41<>""))>0,"FIX: paid exceeds committed - check the line","OK")'),
        ("Projected final over revised budget?",
         '=IF(B{variance}<0,"OVER by "&TEXT(-B{variance},"$#,##0"),"Within revised budget")'.format(**R)),
        ("Contingency reserve exhausted?",
         '=IF(B{reserve}<=0,"Reserve is gone - approve no more draws","Reserve still available")'.format(**R)),
        ("Remaining spend larger than what is left in the revised budget?",
         '=IF((B{unpaid}+B{forecast})>(B{revised}-B{paid}),'
         '"OVER-COMMITTED: remaining spend exceeds budget left","Remaining spend fits the budget")'.format(**R)),
        ("Any change order still marked No?",
         '=IF(B{cos_pending}>0,"Do not let the work proceed on an unsigned change","None pending")'.format(**R)),
        ("Any line with no original budget?",
         '=IF(SUMPRODUCT((\'Cost Control\'!$A$2:$A$41<>"")*(\'Cost Control\'!$D$2:$D$41=""))>0,'
         '"FIX: line without a budget","OK")'),
    ]
    r = 22
    for label, formula in checks:
        ws.cell(row=r, column=1, value=label)
        cell = ws.cell(row=r, column=2, value=formula)
        cell.fill = FORMULA_FILL
        r += 1

    ws.cell(row=32, column=1,
            value="Blue cells are formulas. If a number looks wrong, check the row it came from - never overwrite a total.").font = Font(italic=True)
    ws.column_dimensions["A"].width = 62
    ws.column_dimensions["B"].width = 54
    return ws


def build(out_dir: Path | None = None) -> Path:
    wb = Workbook()
    _start_here(wb)
    _setup(wb)
    _cost_control(wb)
    _change_orders(wb)
    _allowances(wb)
    _payments(wb)
    _contingency(wb)
    _assumptions(wb)
    _summary(wb)
    _paint_formulas(wb)
    wb.active = 0
    target = Path(out_dir) if out_dir else OUT
    target.mkdir(parents=True, exist_ok=True)
    path = target / FILENAME
    wb.save(path)
    return path


def facts(path: Path) -> dict:
    wb = __import__("openpyxl").load_workbook(path)
    formulas = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formulas += 1
    dv = sum(len(ws.data_validations.dataValidation) for ws in wb.worksheets)
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "sheets": wb.sheetnames,
        "sheet_count": len(wb.sheetnames),
        "formulas": formulas,
        "validations": dv,
    }


def main(argv: list[str]) -> int:
    path = build()
    data = facts(path)
    if "--json" in argv:
        print(json.dumps(data, indent=1))
    else:
        print("wrote", data["path"], data["bytes"], "bytes")
        print("sheets:", data["sheet_count"], "formulas:", data["formulas"],
              "validations:", data["validations"])
        print("sha256:", data["sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
