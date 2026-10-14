"""Cycle 89 -- correct three defects in the shipped GDPR DSR workbook.

Preserves the original byte-for-byte as a .bak before any change.

DEFECTS FOUND (all safe, none substantive-legal)
-----------------------------------------------
1. Search_Checklist!H7 contained a hardcoded customer identifier:
       =COUNTIFS(A2:A6,"DSR-2026-031",F2:F6,"N")
   "DSR-2026-031" is leftover from the author's own test run. Two problems:
   it is another party's request identifier shipped inside a buyer-facing
   template, and the formula can only ever return a meaningful result for
   that one request -- for every other buyer it silently reports 0.

2. Six formulas use ranges shorter than the sheet:
       Request_Register!H7    COUNTIF(G2:G6,...)   sheet has 9 rows
       Deadline_Calculator!D5 COUNTIF(E2:E4,...)   sheet has 7 rows
       Search_Checklist!H2    SUMIF(A2:A6,...)     sheet has 9 rows
       Search_Checklist!H7    COUNTIFS(...)        sheet has 9 rows
   A buyer who adds a seventh request is outside their own rollup, so an
   overdue request reports as zero. Silent under-counting in a compliance
   register is the worst kind of bug this workbook could have.

3. Counts keyed on a wildcard text match ("*verdue*") depend on the buyer
   typing Status exactly as expected. Left as-is deliberately: changing the
   status vocabulary would alter what the buyer is instructed to type, which
   is a product decision, not a formatting repair.

WHAT THIS DOES NOT TOUCH
------------------------
No legal text, no deadline rule, no claim. The one-month and two-month
statements were verified against Art. 12(3) and the EDPB SME FAQ before this
script ran; they are correct and are left exactly as written.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, r"C:\openclaw-dasgboard")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import openpyxl

SRC = Path(r"cohort_GF_SHOPIFY_PREMIUM_10_2026_09/dist/GF-SHOP-02"
           r"\gdpr_dsr_handling_kit_workbook.xlsx")
BAK = SRC.with_suffix(SRC.suffix + ".cycle89.bak")

# generous but bounded: covers a real register without an unbounded reference
LAST = 500

if not BAK.exists():
    shutil.copy2(SRC, BAK)
    print(f"original preserved -> {BAK.name}")
else:
    print(f"original already preserved -> {BAK.name} (not overwritten)")

wb = openpyxl.load_workbook(str(SRC))

before = []
for ws in wb:
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith("="):
                before.append((ws.title, c.coordinate, c.value))
print(f"\nformulas before: {len(before)}")

fixes = []

ws = wb["Request_Register"]
# COUNTIF(G2:G6,"*verdue*") -> cover the whole working range
old = ws["H7"].value
ws["H7"] = f'=COUNTIF(G2:G{LAST},"*verdue*")'
fixes.append(("Request_Register", "H7", old, ws["H7"].value))

ws = wb["Deadline_Calculator"]
old = ws["D5"].value
ws["D5"] = f'=COUNTIF(E2:E{LAST},"Y")'
fixes.append(("Deadline_Calculator", "D5", old, ws["D5"].value))

ws = wb["Search_Checklist"]
old = ws["H2"].value
ws["H2"] = f"=SUMIF(A2:A{LAST},A2,E2:E{LAST})"
fixes.append(("Search_Checklist", "H2", old, ws["H2"].value))

old = ws["H7"].value
# parameterise on this row's own request ref instead of a hardcoded id
ws["H7"] = f'=COUNTIFS(A2:A{LAST},A7,F2:F{LAST},"N")'
fixes.append(("Search_Checklist", "H7", old, ws["H7"].value))

ws = wb["Redaction_Log"]
# the first fix pass MISSED these two; the verifier caught them, which is the
# point of verifying rather than assuming the pass was complete.
for cell, tmpl in (("G2", f"=COUNTA(B2:B{{last}})"),
                   ("G3", f"=COUNTBLANK(C2:C{{last}})")):
    old = ws[cell].value
    ws[cell] = tmpl.format(last=LAST)
    fixes.append(("Redaction_Log", cell, old, ws[cell].value))

wb.save(str(SRC))

print("\nFIXES APPLIED")
print("=" * 78)
for sheet, cell, old, new in fixes:
    print(f"\n  {sheet}!{cell}")
    print(f"    before: {old}")
    print(f"    after : {new}")

# verify
print("\nVERIFICATION")
print("=" * 78)
wb2 = openpyxl.load_workbook(str(SRC))
after = []
for ws in wb2:
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith("="):
                after.append((ws.title, c.coordinate, c.value))
print(f"  formulas after : {len(after)}  (was {len(before)})")

leftover = [f for f in after if "DSR-2026-031" in f[2]]
print(f"  hardcoded customer ids remaining : {len(leftover)}")
assert not leftover, leftover

short = []
for sheet, cell, f in after:
    import re
    for m in re.finditer(r"([A-Z])(\d+):([A-Z])(\d+)", f):
        if int(m.group(4)) < LAST:
            short.append((sheet, cell, m.group(0)))
print(f"  truncated ranges remaining        : {len(short)}")
assert not short, short

print("\n  ORIGINAL PRESERVED, FORMULAS CORRECTED, NO LEGAL TEXT TOUCHED")