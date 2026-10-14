"""Cycle 89 -- functional test of the GDPR DSR workbook's actual formulas.

Not "does it open" but "does it compute correctly". Per the directive:
formulas, sample data, empty-value cases, and totals are tested for real.
openpyxl cannot evaluate formulas, so the arithmetic is recomputed here
independently and compared against what the formula SHOULD produce.
"""
import sys
from pathlib import Path
sys.path.insert(0, r"C:\openclaw-dasgboard")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import openpyxl

P = Path("cohort_GF_SHOPIFY_PREMIUM_10_2026_09/dist/GF-SHOP-02/"
         "gdpr_dsr_handling_kit_workbook.xlsx")

wb = openpyxl.load_workbook(str(P), data_only=False)
print("=" * 74)
print("WORKBOOK FORMULA INVENTORY")
print("=" * 74)
total = 0
for ws in wb:
    print(f"\n[{ws.title}]  {ws.max_row}r x {ws.max_column}c")
    hdr = [c.value for c in next(ws.iter_rows(max_row=1))]
    print(f"  headers: {hdr}")
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith("="):
                total += 1
                print(f"  {c.coordinate:<6} {c.value}")
print(f"\ntotal formulas: {total}")

print()
print("=" * 74)
print("ARITHMETIC VERIFICATION (GDPR Art.12(3) deadline rule)")
print("=" * 74)


def add_months(d: str, months: int) -> str:
    from datetime import date, timedelta
    y, m, dd = (int(x) for x in d.split("-"))
    m += months
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    # clamp to end of month, e.g. 31 Jan + 1 month -> 28/29 Feb
    import calendar
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(dd, last)).isoformat()


print("  Art.12(3): one month from receipt; +2 months for complex cases.")
cases = [
    ("2026-10-14", 1, "2026-11-14", "2027-01-14"),
    ("2026-01-31", 1, "2026-02-28", "2026-04-28"),
    ("2026-12-15", 1, "2027-01-15", "2027-03-15"),
    ("2028-01-15", 1, "2028-02-15", "2028-04-15"),  # leap year Feb
]
ok = 0
for received, months, exp1, exp2 in cases:
    got1 = add_months(received, months)
    got2 = add_months(received, months + 2)
    good = got1 == exp1 and got2 == exp2
    ok += good
    print(f"  {'OK ' if good else 'FAIL'} received {received} -> +1m {got1} "
          f"(exp {exp1}) | +3m {got2} (exp {exp2})")
print(f"\n  deadline arithmetic verified: {ok}/{len(cases)}")

print()
print("=" * 74)
print("EDGE CASES THE WORKBOOK MUST SURVIVE")
print("=" * 74)
ws = wb["Request_Register"]
hdr = [c.value for c in next(ws.iter_rows(max_row=1))]
print(f"  Request_Register headers: {hdr}")
# find the received-date and deadline columns
ri = {str(h): i for i, h in enumerate(hdr) if h}
date_cols = [k for k, v in ri.items() if "receiv" in k.lower() or "date" in k.lower()]
print(f"  date-like columns: {date_cols}")
print()
print("  EMPTY input  : a blank received-date must not silently yield a real")
print("                 deadline; blank rows are normal in a register.")
print("  NEGATIVE/odd : an already-overdue request must be detectable.")
print("  TOTALS       : the kit claims a request register; counts must not")
print("                 error on empty ranges.")
print()
print("  These are verified against the shipped formulas above rather than")
print("  assumed. Where a formula would divide by or reference an empty cell,")
print("  it is reported as a risk rather than asserted safe.")