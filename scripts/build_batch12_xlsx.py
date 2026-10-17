#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge Batch 12 — XLSX builders (products 001/002-reg/004/005-tracker/
006-log/007-inv/008-budget/010-pipe). Deterministic, $0, no network.
Writes into books/batch12/. Each workbook carries real structure + working
formulas where math is the product; example rows are labeled EXAMPLE.
"""
import sys
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "books" / "batch12"
OUT.mkdir(parents=True, exist_ok=True)

HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(bold=True, color="FFFFFF", size=11)
EX_FILL = PatternFill("solid", fgColor="FFF2CC")
FORMULA_FILL = PatternFill("solid", fgColor="DDEBF7")
THIN = Border(*(Side(style="thin", color="B0B0B0") for _ in range(4)))
WRAP = Alignment(wrap_text=True, vertical="top")


def _paint_formulas(wb):
    """Paint every formula cell light blue so README color language is
    true in every workbook: white = fill me, blue = computed (do not
    overwrite), yellow = EXAMPLE row (overwrite or delete). Applied last
    so it wins over example-row fills on formula cells."""
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    cell.fill = FORMULA_FILL


def _sheet(wb, title, headers, rows, widths=None, formatters=None, example_rows=0):
    ws = wb.active if wb.sheetnames == ["Sheet"] and wb["Sheet"].max_row == 1 else wb.create_sheet(title)
    if ws.title != title:
        ws.title = title
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font, cell.fill, cell.alignment = HDR_FONT, HDR_FILL, WRAP
    for r, row in enumerate(rows, 2):
        for c, v in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border, cell.alignment = THIN, WRAP
            if formatters and c - 1 in formatters:
                cell.number_format = formatters[c - 1]
    for r in range(2, 2 + example_rows):
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).fill = EX_FILL
    if widths:
        for c, w in enumerate(widths, 1):
            ws.column_dimensions[ws.cell(row=1, column=c).column_letter].width = w
    ws.freeze_panes = "A2"
    ws.sheet_properties.pageSetUpPr = None
    return ws


def _readme(wb, lines):
    ws = wb.create_sheet("README")
    ws["A1"] = lines[0]
    ws["A1"].font = Font(bold=True, size=13)
    for i, ln in enumerate(lines[1:], 3):
        ws.cell(row=i, column=1, value=ln).alignment = WRAP
    ws.column_dimensions["A"].width = 110



def _b12_guard_inputs(ws):
    """Cycle 94 (edge cases found in Excel 16): typing 30 instead of 30% gave
    $2.82/hr silently, tax >= 100% or negative inputs gave negative rates, and
    0 weeks/hours or text gave #DIV/0! / #VALUE!. Validate the inputs and make
    every output say what to fix instead of showing an error or a wrong number."""
    from openpyxl.worksheet.datavalidation import DataValidation
    rules = [
        ("C2", "decimal", 0, 10_000_000, "Take-home pay", "Enter a yearly amount in USD, 0 or more."),
        ("C3", "decimal", 0, 0.9, "Tax buffer", "Enter a percentage between 0% and 90%, e.g. 30% (not 30)."),
        ("C4", "decimal", 0, 10_000_000, "Expenses", "Enter yearly expenses in USD, 0 or more."),
        ("C5", "whole", 1, 52, "Billable weeks", "Enter a whole number of weeks between 1 and 52."),
        ("C6", "decimal", 1, 80, "Billable hours", "Enter billable hours per week between 1 and 80."),
        ("C7", "decimal", 0, 1, "Safety margin", "Enter a percentage between 0% and 100%, e.g. 15% (not 15)."),
    ]
    for cell, kind, lo, hi, title, msg in rules:
        dv = DataValidation(type=kind, operator="between", formula1=str(lo), formula2=str(hi),
                            allow_blank=False, showErrorMessage=True, showInputMessage=True,
                            errorTitle=title, error=msg, promptTitle=title, prompt=msg)
        ws.add_data_validation(dv)
        dv.add(cell)
    ws["D8"] = ('=IF(AND(ISNUMBER(C2),ISNUMBER(C3),ISNUMBER(C4),C2>=0,C4>=0,C3>=0,C3<1),'
                'C2/(1-C3)+C4,"Check take-home, tax % (0-90%) and expenses")')
    ws["D9"] = ('=IF(NOT(ISNUMBER(D8)),"Fix the line above",'
                'IF(AND(ISNUMBER(C5),ISNUMBER(C6),C5>0,C6>0),D8/(C5*C6),"Check weeks and hours"))')
    ws["D10"] = ('=IF(NOT(ISNUMBER(D9)),"Fix the lines above",'
                 'IF(AND(ISNUMBER(C7),C7>=0),D9*(1+C7),"Check safety margin %"))')
    # A tax buffer entered as 30 instead of 30% is the most likely mistake.
    ws["E3"] = '=IF(AND(ISNUMBER(C3),C3>0.9),"Tax buffer must be 90% or less. Type 30% (not 30).","")'

def b12_001_rate_calculator():
    """Freelancer Rate & Raise Calculator: cost-plus rate math + utilization."""
    wb = Workbook()
    _sheet(wb, "Inputs", ["#", "Input", "Your value", "Notes"], [
        [1, "Target annual take-home pay (USD)", 80000, "After tax, what you want to keep"],
        [2, "Tax + self-employment buffer %", 0.30, "EXAMPLE 30% — set your own rate"],
        [3, "Annual business expenses (USD)", 6000, "Tools, insurance, accounting"],
        [4, "Billable weeks per year", 46, "52 minus vacation, gaps, admin"],
        [5, "Billable hours per week", 25, "Realistic delivery hours, not desk hours"],
        [6, "Utilization safety margin %", 0.15, "Buffer for scope creep and late payers"],
    ], [6, 42, 16, 60], {2: '#,##0'}, example_rows=0)
    ws = wb["Inputs"]
    ws["C8"] = "Gross revenue needed (USD)"
    ws["D8"] = "=C2/(1-C3)+C4"
    ws["C8"].font = Font(bold=True)
    ws["C9"] = "Minimum hourly rate (USD/hr)"
    ws["D9"] = "=D8/(C5*C6)"
    ws["C9"].font = Font(bold=True)
    ws["D9"].number_format = '"$"#,##0.00'
    ws["C10"] = "Rate with safety margin (USD/hr)"
    ws["D10"] = "=D9*(1+C7)"
    ws["D10"].number_format = '"$"#,##0.00'
    ws["C10"].font = Font(bold=True)
    # Cycle 88 fix: the column format '#,##0' made 30% and 15% display as "0".
    for c in ("C3", "C7"):
        ws[c].number_format = "0%"
    ws["D8"].number_format = '"$"#,##0.00'
    _b12_guard_inputs(ws)
    _sheet(wb, "ClientMix", ["Client", "Hours/mo", "Rate/hr (USD)", "Monthly revenue (USD)", "Hassle score 1-5", "Effective rank"],
        [["EXAMPLE Acme Co", 40, 95, "=B2*C2", 2, "=D2/E2"],
         ["EXAMPLE Beta LLC", 20, 120, "=B3*C3", 4, "=D3/E3"]],
        [22, 12, 16, 22, 16, 16], {1: '#,##0', 2: '"$"#,##0', 3: '"$"#,##0.00', 5: '"$"#,##0.00'}, example_rows=2)
    _sheet(wb, "RaisePlanner", ["Trigger to review", "Metric to check", "Raise %", "New rate (USD/hr)", "Date done"],
        # Cycle 88 fix: new rate follows the user's own rate (Inputs!D10), not a hardcoded 95.
        # Cycle 94: shows a message instead of an error when Inputs is incomplete.
        [["EXAMPLE quarterly review", "Utilization > 85% for 6 weeks", 0.10,
          '=IF(ISNUMBER(Inputs!$D$10),Inputs!$D$10*(1+C2),"Fix Inputs first")', ""],
         ["EXAMPLE new skill ships", "Client-paid premium work", 0.15,
          '=IF(ISNUMBER(Inputs!$D$10),Inputs!$D$10*(1+C3),"Fix Inputs first")', ""]],
        [26, 34, 10, 18, 14], {2: "0%", 3: '"$"#,##0.00'}, example_rows=2)
    _readme(wb, ["B12-001 Freelancer Rate & Raise Calculator — HOW TO USE",
        "1) Fill ONLY the white input cells (column C on Inputs). Blue cells are computed — do not overwrite them. Yellow rows are EXAMPLES — overwrite with your numbers or delete them.",
        "2) Your charge rate = Inputs!D10. Quote at or above it.",
        "3) ClientMix: log every client monthly; sort by Effective rank (revenue per hassle point). Fire the bottom row first.",
        "4) RaisePlanner: review on the triggers listed; never raise without a logged trigger.",
        "This is arithmetic on YOUR inputs, not financial advice. Tax buffer is an estimate — confirm with your accountant."])
    p = OUT / "B12-001_freelancer_rate_raise_calculator.xlsx"
    _paint_formulas(wb)
    wb.save(p)
    return p


def b12_002_handoff_register():
    wb = Workbook()
    _sheet(wb, "HandoffRegister", ["#", "Project", "Outgoing owner", "Incoming owner", "Handoff date", "Status", "Open risks", "Client sign-off (Y/N)"],
        [[1, "EXAMPLE Website rebuild", "You", "Client team", "2026-11-01", "In progress", "DNS transfer pending", "N"],
         [2, "EXAMPLE API integration", "You", "Agency B", "2026-11-15", "Not started", "", ""]],
        [5, 26, 18, 18, 14, 14, 30, 16], example_rows=2)
    _sheet(wb, "AssetChecklist", ["Category", "Item", "Location/URL", "Access transferred (Y/N)", "Verified by"],
        [["Code", "EXAMPLE repo + deploy keys", "", "N", ""],
         ["Docs", "EXAMPLE architecture notes", "", "N", ""],
         ["Accounts", "EXAMPLE analytics, hosting, DNS", "", "N", ""],
         ["Money", "EXAMPLE final invoice + expenses", "", "N", ""],
         ["People", "EXAMPLE stakeholder intros done", "", "N", ""]],
        [12, 34, 30, 22, 16], example_rows=5)
    _readme(wb, ["B12-002 Client Project Handoff Register — HOW TO USE",
        "1) One row per project on HandoffRegister. Nothing is 'done' until Client sign-off = Y.",
        "2) Walk AssetChecklist for every handoff: code, docs, accounts, money, people. A missing row is a future dispute.",
        "3) Use with the B12-002 PDF guide (session script + email templates)."])
    p = OUT / "B12-002_client_handoff_register.xlsx"
    _paint_formulas(wb)
    wb.save(p)
    return p


def b12_004_meeting_calculator():
    wb = Workbook()
    _sheet(wb, "Meetings", ["Meeting", "Attendees", "Avg cost/hr (USD)", "Hours", "Times/week", "Weekly cost (USD)", "Decision needed (Y/N)", "Keep / Kill / Shorten"],
        [["EXAMPLE Sprint planning", 6, 75, 1.5, 1, "=B2*C2*D2*E2", "Y", "Shorten"],
         ["EXAMPLE Status round-robin", 8, 70, 0.5, 3, "=B3*C3*D3*E3", "N", "Kill"]],
        [26, 11, 18, 9, 12, 18, 20, 20], {5: '"$"#,##0.00'}, example_rows=2)
    ws = wb["Meetings"]
    ws["G1"] = "TOTAL weekly meeting cost (USD)"
    ws["H1"] = "=SUM(F2:F100)"
    ws["H1"].number_format = '"$"#,##0.00'
    ws["G1"].font = Font(bold=True)
    _sheet(wb, "Rules", ["#", "Rule", "Applies to"],
        [[1, "No agenda in invite = decline by default", "All recurring"],
         [2, "Default 25 min, not 30; 50 min, not 60", "All new invites"],
         [3, "Status updates go async (doc/chat), never a meeting", "Status round-robins"],
         [4, "Owner + decision + deadline in every invite", "Decision meetings"],
         [5, "Quarterly kill review: cancel bottom 20% by cost with no decision", "Recurring"]],
        [5, 62, 20], example_rows=0)
    _readme(wb, ["B12-004 Meeting Cost & ROI Calculator — HOW TO USE",
        "1) Log every recurring meeting with real attendee counts and loaded hourly costs (salary ÷ 2000 × 1.3).",
        "2) Kill or shorten anything with Decision needed = N, starting from the highest Weekly cost.",
        "3) Re-run the kill review quarterly (Rules sheet, rule 5). Companion 1-pager PDF explains the method."])
    p = OUT / "B12-004_meeting_cost_roi_calculator.xlsx"
    _paint_formulas(wb)
    wb.save(p)
    return p


def b12_005_guest_tracker():
    wb = Workbook()
    _sheet(wb, "Pipeline", ["Show", "Contact", "Pitch date", "Angle", "Stage", "Record date", "Follow-up date", "Assets sent (Y/N)"],
        [["EXAMPLE The Ops Show", "producer@example.com", "2026-10-20", "Freelancer pricing math", "Pitched", "", "2026-10-27", "N"]],
        [22, 26, 12, 30, 14, 13, 15, 16], example_rows=1)
    _sheet(wb, "Angles", ["#", "Your angle (one line)", "Proof you can cite", "Best-fit show type"],
        [[1, "EXAMPLE pricing math freelancers get wrong", "500 rate reviews analyzed", "Freelance/business"],
         [2, "", "", ""],
         [3, "", "", ""]],
        [5, 44, 34, 24], example_rows=1)
    _sheet(wb, "FollowUps", ["Show", "Touch #", "Date", "Channel", "One-line value add", "Reply (Y/N)"],
        [["EXAMPLE The Ops Show", 1, "2026-10-27", "Email", "EXAMPLE rate-benchmark table", "N"]],
        [22, 9, 12, 10, 44, 11], example_rows=1)
    _readme(wb, ["B12-005 Podcast Guest Booking Tracker — HOW TO USE",
        "1) Write 3+ angles first (Angles sheet) — never pitch without an angle.",
        "2) Log every pitch on Pipeline; move FollowUps on day 7 and day 21, then close.",
        "3) Pair with the B12-005 PDF (pitch + follow-up scripts word-for-word). Max 2 follow-ups per show — more is spam."])
    p = OUT / "B12-005_podcast_guest_tracker.xlsx"
    _paint_formulas(wb)
    wb.save(p)
    return p


def b12_006_home_office_log():
    wb = Workbook()
    _sheet(wb, "Expenses2026", ["Date", "Category", "Description", "Amount (USD)", "Home %", "Deductible est. (USD)", "Receipt file"],
        [["2026-01-15", "EXAMPLE internet", "Monthly bill", 80.00, 0.40, "=D2*E2", "receipts/jan-internet.pdf"]],
        [12, 18, 30, 15, 10, 19, 28], {3: '"$"#,##0.00', 5: '"$"#,##0.00'}, example_rows=1)
    ws = wb["Expenses2026"]
    ws["H1"] = "TOTAL deductible est. (USD)"
    ws["I1"] = "=SUM(F2:F500)"
    ws["I1"].number_format = '"$"#,##0.00'
    _sheet(wb, "SpaceMeasure", ["Item", "Value", "Notes"],
        [["Total home sq ft", 1200, "Measure once"], ["Office sq ft (exclusive use)", 150, "Must be regular + exclusive use"],
         ["Office % (= office ÷ total)", 0.125, "=B3/B2 — used for Home % above"], ["Method chosen", "Actual", "Actual or Simplified — pick ONE per year"]],
        [30, 14, 44], example_rows=0)
    _sheet(wb, "Categories", ["Category", "What counts", "What never counts"],
        [["Internet/utilities", "Business-use share only", "Full bill without home %"],
         ["Supplies", "100% business items", "Personal items"],
         ["Repairs", "Office-area repairs", "Whole-home improvements (different rules)"],
         ["Rent/mortgage share", "Home % of eligible costs (actual method)", "Simplified method mixes"]],
        [20, 44, 44], example_rows=0)
    _readme(wb, ["B12-006 Home-Office Deduction Organizer — HOW TO USE",
        "1) Measure once (SpaceMeasure). Pick ONE method for the year: Actual (this log) or Simplified.",
        "2) Log every expense with Home % and receipt file. The deductible estimate column is arithmetic, not a filing.",
        "3) Read the companion PDF before filing. PROCEDURE INFORMATION ONLY — NOT TAX ADVICE. Verify current-year IRS rules; limits change."])
    p = OUT / "B12-006_home_office_expense_log.xlsx"
    _paint_formulas(wb)
    wb.save(p)
    return p


def b12_007_digital_inventory():
    wb = Workbook()
    for sheet, headers, rows in [
        ("Accounts", ["Service", "Username", "2FA (Y/N)", "Recovery email OK (Y/N)", "Keep / Delete", "Deleted date"],
         [["EXAMPLE old-forum.com", "me2009", "N", "N", "Delete", ""]]),
        ("Files", ["Location", "Size est.", "Last opened", "Keep / Archive / Delete", "Done date"],
         [["EXAMPLE downloads/2019", "4 GB", "2024-02-01", "Archive", ""]]),
        ("Backups", ["What", "Where (3-2-1 slot)", "Last verified restore", "Status"],
         [["EXAMPLE photos", "Cloud + external drive", "never", "Unverified"]]),
        ("Subscriptions", ["Service", "Cost/mo (USD)", "Last used", "Keep / Cancel", "Cancelled date"],
         [["EXAMPLE streaming-x", 15.99, "2026-08-01", "Cancel", ""]]),
    ]:
        _sheet(wb, sheet, headers, rows, [26, 18, 22, 22, 16, 14], example_rows=1)
    _readme(wb, ["B12-007 Digital Inventory — HOW TO USE",
        "1) Work the 30-day plan PDF week by week; every decision lands in one of these four sheets.",
        "2) 3-2-1 backup rule: 3 copies, 2 media, 1 offsite. A backup never restore-tested = no backup.",
        "3) Never store passwords in this file — it is an inventory (what/where/status), not a vault."])
    p = OUT / "B12-007_digital_inventory.xlsx"
    _paint_formulas(wb)
    wb.save(p)
    return p


def b12_008_moving_budget():
    wb = Workbook()
    _sheet(wb, "Budget", ["Item", "Quote A (USD)", "Quote B (USD)", "Chosen (USD)", "Paid (Y/N)"],
        [["EXAMPLE movers (3-bed)", 1800, 2100, 1800, "N"],
         ["EXAMPLE packing supplies", 150, 120, 120, "N"],
         ["EXAMPLE deposit + first month", 3000, 3000, 3000, "N"],
         ["EXAMPLE utility transfers/fees", 200, 200, 200, "N"]],
        [32, 16, 16, 15, 11], {1: '"$"#,##0', 2: '"$"#,##0', 3: '"$"#,##0'}, example_rows=4)
    ws = wb["Budget"]
    ws["A8"] = "TOTAL chosen (USD)"
    ws["D8"] = "=SUM(D2:D7)"
    ws["D8"].number_format = '"$"#,##0'
    _sheet(wb, "MoverCompare", ["Mover", "Quote (USD)", "Insured (Y/N)", "Reviews checked (Y/N)", "Red flags", "Decision"],
        [["EXAMPLE MoveRight", 1800, "Y", "Y", "None", "Shortlist"]],
        [20, 14, 13, 20, 30, 12], example_rows=1)
    _sheet(wb, "AddressChanges", ["Account/service", "Updated (Y/N)", "Date", "Confirmation #"],
        [["EXAMPLE bank", "N", "", ""], ["EXAMPLE employer/payroll", "N", "", ""],
         ["EXAMPLE subscriptions", "N", "", ""], ["EXAMPLE voter registration", "N", "", ""]],
        [30, 14, 12, 20], example_rows=4)
    _readme(wb, ["B12-008 Moving Budget & Tracker — HOW TO USE",
        "1) Get 2+ quotes per row (MoverCompare). Never book an uninsured mover.",
        "2) Work AddressChanges in week 2 — missed ones cost money for months.",
        "3) Pair with the B12-008 8-week checklist PDF."])
    p = OUT / "B12-008_moving_budget_tracker.xlsx"
    _paint_formulas(wb)
    wb.save(p)
    return p


def b12_010_grant_pipeline():
    wb = Workbook()
    _sheet(wb, "Pipeline", ["Funder", "Program", "Amount (USD)", "Deadline", "Stage", "Owner", "Docs checklist done (Y/N)", "Submitted date"],
        [["EXAMPLE Community Fund", "Small grants", 10000, "2027-02-01", "Research", "Sam", "N", ""]],
        [22, 20, 14, 12, 14, 10, 22, 15], {2: '"$"#,##0'}, example_rows=1)
    _sheet(wb, "Stages", ["Stage", "Exit rule", "Typical docs"],
        [["Research", "Funder fits mission + budget range", "Guidelines PDF saved"],
         ["Eligibility", "All must-pass criteria = yes", "Eligibility checklist"],
         ["Drafting", "Narrative + budget + attachments complete", "Narrative, budget, board list, 990"],
         ["Review", "Second reader signed off", "Review sign-off"],
         ["Submitted", "Confirmation receipt saved", "Receipt"],
         ["FollowUp", "Report dates calendared", "Award letter / decline note"]],
        [14, 40, 44], example_rows=0)
    _sheet(wb, "Boilerplate", ["Block", "Owner", "Last updated", "Status"],
        [["EXAMPLE mission paragraph", "", "", "Missing"],
         ["EXAMPLE budget template", "", "", "Missing"],
         ["EXAMPLE board list", "", "", "Missing"]],
        [28, 12, 14, 12], example_rows=3)
    _readme(wb, ["B12-010 Grant Pipeline Tracker — HOW TO USE",
        "1) Nothing enters Drafting until Eligibility exits clean — ineligible applications are the #1 wasted effort.",
        "2) Reuse Boilerplate blocks; never rewrite mission/budget prose per funder from scratch.",
        "3) Log every decline with the reason — a pipeline without decline reasons cannot improve."])
    p = OUT / "B12-010_grant_pipeline_tracker.xlsx"
    _paint_formulas(wb)
    wb.save(p)
    return p


if __name__ == "__main__":
    makers = [b12_001_rate_calculator, b12_002_handoff_register, b12_004_meeting_calculator,
              b12_005_guest_tracker, b12_006_home_office_log, b12_007_digital_inventory,
              b12_008_moving_budget, b12_010_grant_pipeline]
    for fn in makers:
        p = fn()
        print("built", p.name, p.stat().st_size, "bytes")
