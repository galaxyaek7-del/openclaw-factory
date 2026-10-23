"""lib/xlsx_eval.py -- independent formula evaluator (2026-10-22).

Expected values follow Excel's documented behavior. Fixtures are written
with openpyxl to a temp dir.

    python -m pytest tests/test_xlsx_eval.py -q
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import openpyxl  # noqa: E402

from lib import xlsx_eval as xe  # noqa: E402


def book(cells, extra=None):
    d = tempfile.mkdtemp()
    p = Path(d) / "t.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"
    for coord, v in cells.items():
        ws[coord] = v
    for name, more in (extra or {}).items():
        s = wb.create_sheet(name)
        for coord, v in more.items():
            s[coord] = v
    wb.save(p)
    return xe.Workbook(p)


class TestSemantics(unittest.TestCase):
    def test_arithmetic_and_precedence(self):
        w = book({"A1": 2, "A2": 3, "B1": "=A1+A2*4", "B2": "=-A1^2" if False else "=(A1+A2)*4", "B3": "=10/4"})
        self.assertEqual(w.evaluate("Data!B1"), 14)
        self.assertEqual(w.evaluate("Data!B2"), 20)
        self.assertEqual(w.evaluate("Data!B3"), 2.5)

    def test_blank_cell_is_zero_in_math_and_equal_to_empty_text(self):
        w = book({"B1": "=A1*5", "B2": '=IF(A1="","blank","not")', "B3": "=IF(A1=0,1,0)"})
        self.assertEqual(w.evaluate("Data!B1"), 0)
        self.assertEqual(w.evaluate("Data!B2"), "blank")
        self.assertEqual(w.evaluate("Data!B3"), 1)

    def test_text_in_arithmetic_is_value_error_and_propagates(self):
        w = book({"A1": "x", "B1": "=A1*2", "C1": '=IF(B1>1,"a","b")', "D1": "=IFERROR(B1,0)"})
        self.assertEqual(w.evaluate("Data!B1"), xe.VALUE)
        self.assertEqual(w.evaluate("Data!C1"), xe.VALUE)
        self.assertEqual(w.evaluate("Data!D1"), 0)

    def test_division_by_zero(self):
        self.assertEqual(book({"A1": 0, "B1": "=5/A1"}).evaluate("Data!B1"), xe.DIV0)

    def test_if_is_lazy(self):
        w = book({"A1": 0, "B1": '=IF(A1=0,"safe",1/A1)'})
        self.assertEqual(w.evaluate("Data!B1"), "safe")

    def test_text_vs_number_comparison_follows_excel(self):
        w = book({"A1": "abc", "B1": "=A1>5", "B2": '=A1="ABC"'})
        self.assertIs(w.evaluate("Data!B1"), True)   # text sorts after numbers
        self.assertIs(w.evaluate("Data!B2"), True)   # case-insensitive

    def test_sum_skips_text_and_blanks_in_ranges(self):
        w = book({"A1": 1, "A2": "note", "A4": 5, "B1": "=SUM(A1:A5)"})
        self.assertEqual(w.evaluate("Data!B1"), 6)

    def test_countif_and_cross_sheet_ranges(self):
        w = book({"A1": "kill", "A2": "watch", "A3": "Kill"},
                 {"Summary": {"B1": "=COUNTIF(Data!A1:A9,\"kill\")", "B2": "=COUNTIF('Data'!A1:A9,\"watch\")"}})
        self.assertEqual(w.evaluate("Summary!B1"), 2)
        self.assertEqual(w.evaluate("Summary!B2"), 1)

    def test_and_or_not(self):
        w = book({"A1": 1, "B1": "=AND(A1>0,A1<2)", "B2": "=OR(A1>5,A1=1)", "B3": "=NOT(A1=1)"})
        self.assertIs(w.evaluate("Data!B1"), True)
        self.assertIs(w.evaluate("Data!B2"), True)
        self.assertIs(w.evaluate("Data!B3"), False)

    def test_dates_are_serials(self):
        import datetime
        w = book({"A1": datetime.date(2026, 8, 1), "A2": datetime.date(2026, 10, 15),
                  "B1": "=A1+30", "B2": "=A2-A1"})
        self.assertEqual(w.evaluate("Data!B1"), xe.excel_serial(datetime.date(2026, 8, 31)))
        self.assertEqual(w.evaluate("Data!B2"), 75)
        self.assertEqual(xe.excel_serial(datetime.date(2026, 1, 1)), 46023)  # Excel's own serial

    def test_unsupported_function_is_reported_not_guessed(self):
        with self.assertRaises(xe.Unsupported):
            book({"B1": "=VLOOKUP(1,A1:A2,1,FALSE)"}).evaluate("Data!B1")

    def test_circular_reference_is_reported(self):
        with self.assertRaises(xe.Unsupported):
            book({"A1": "=B1+1", "B1": "=A1+1"}).evaluate("Data!A1")


class TestBuildToolRejectsWrongExpectations(unittest.TestCase):
    def test_a_wrong_expected_value_fails_the_build(self):
        import json
        sys.path.insert(0, str(ROOT / "scripts"))
        import build_tool_workbook as btw
        spec = {"workbook_filename": "t.xlsx", "sheets": [
            {"name": "S", "columns": ["A", "B", "Total"], "example_rows": [[2, 3, ""]],
             "formulas": [{"cell": "C2", "formula": "=A2*B2"}]}],
            "checks": [{"cell": "S!C2", "equals": 7}]}
        d = Path(tempfile.mkdtemp())
        (d / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        r = btw.build(d / "spec.json", d / "t.xlsx")
        self.assertFalse(r["ok"])
        self.assertEqual(r["recalc"]["failed"][0]["got"], 6)


if __name__ == "__main__":
    unittest.main()


class TestExtendedSubset(unittest.TestCase):
    """2026-10-23 additions. Expected values are Excel's documented results."""

    def test_power_precedence_and_associativity(self):
        w = book({"A1": 2, "B1": "=-A1^2", "B2": "=2^3^2", "B3": "=2*3^2", "B4": "=4^0.5", "B5": "=0^-1"})
        self.assertEqual(w.evaluate("Data!B1"), 4)       # unary minus binds first
        self.assertEqual(w.evaluate("Data!B2"), 64)      # left-associative
        self.assertEqual(w.evaluate("Data!B3"), 18)
        self.assertEqual(w.evaluate("Data!B4"), 2)
        self.assertEqual(w.evaluate("Data!B5"), xe.DIV0)

    def test_pmt_and_nper_match_excel(self):
        w = book({"B1": "=PMT(0.05/12,360,200000)", "B2": "=NPER(0.01,-100,1000)",
                  "B3": "=PMT(0,10,1000)", "B4": "=NPER(0.02,-10,1000)", "B5": "=PMT(0.1,2,100,0,1)"})
        self.assertAlmostEqual(w.evaluate("Data!B1"), -1073.6432460242781, places=6)
        self.assertAlmostEqual(w.evaluate("Data!B2"), 10.588644, places=5)
        self.assertEqual(w.evaluate("Data!B3"), -100)
        self.assertEqual(w.evaluate("Data!B4"), xe.NUM)  # payment never covers the interest
        self.assertAlmostEqual(w.evaluate("Data!B5"), -52.380952, places=5)

    def test_countif_and_sumif_criteria(self):
        cells = {"A1": 5, "A2": -3, "A3": "paid", "A4": 0, "A5": "PAID",
                 "B1": 10, "B2": 20, "B3": 30, "B4": 40, "B5": 50,
                 "C1": '=COUNTIF(A1:A6,">0")', "C2": '=COUNTIF(A1:A6,"<>5")', "C3": '=COUNTIF(A1:A6,"paid")',
                 "C4": '=SUMIF(A1:A5,"paid",B1:B5)', "C5": '=SUMIF(A1:A5,"<=0",B1:B5)', "C6": '=SUMIF(B1:B5,">=30")',
                 "C7": '=COUNTIF(A1:A6,"")', "C8": '=COUNTIF(A1:A6,"<>")'}
        w = book(cells)
        self.assertEqual(w.evaluate("Data!C1"), 1)
        self.assertEqual(w.evaluate("Data!C2"), 5)   # blank and text cells satisfy "<>5"
        self.assertEqual(w.evaluate("Data!C3"), 2)   # case-insensitive
        self.assertEqual(w.evaluate("Data!C4"), 80)
        self.assertEqual(w.evaluate("Data!C5"), 60)
        self.assertEqual(w.evaluate("Data!C6"), 120)
        self.assertEqual(w.evaluate("Data!C7"), 1)   # A6 is blank
        self.assertEqual(w.evaluate("Data!C8"), 5)

    def test_wildcard_criterion_is_unsupported_not_guessed(self):
        w = book({"A1": "x", "B1": '=COUNTIF(A1:A2,"x*")'})
        with self.assertRaises(xe.Unsupported):
            w.evaluate("Data!B1")

    def test_average_count_counta(self):
        w = book({"A1": 2, "A2": 4, "A3": "t", "A4": '=""',
                  "B1": "=AVERAGE(A1:A5)", "B2": "=COUNT(A1:A5)", "B3": "=COUNTA(A1:A5)", "B4": "=AVERAGE(A5:A6)"})
        self.assertEqual(w.evaluate("Data!B1"), 3)
        self.assertEqual(w.evaluate("Data!B2"), 2)
        self.assertEqual(w.evaluate("Data!B3"), 4)   # counts the "" a formula returns, as Excel does
        self.assertEqual(w.evaluate("Data!B4"), xe.DIV0)

    def test_int_roundup_rounddown(self):
        w = book({"B1": "=INT(-1.5)", "B2": "=ROUNDUP(2.141,2)", "B3": "=ROUNDUP(-2.141,2)",
                  "B4": "=ROUNDDOWN(2.149,2)", "B5": "=ROUNDUP(2.5,0)", "B6": "=ROUNDUP(3,0)"})
        self.assertEqual(w.evaluate("Data!B1"), -2)
        self.assertAlmostEqual(w.evaluate("Data!B2"), 2.15)
        self.assertAlmostEqual(w.evaluate("Data!B3"), -2.15)
        self.assertAlmostEqual(w.evaluate("Data!B4"), 2.14)
        self.assertEqual(w.evaluate("Data!B5"), 3)
        self.assertEqual(w.evaluate("Data!B6"), 3)


class TestExcelRound(unittest.TestCase):
    def test_round_is_half_away_from_zero_like_excel(self):
        w = book({"B1": "=ROUND(2.675,2)", "B2": "=ROUND(-0.125,2)", "B3": "=ROUND(0.5,0)", "B4": "=ROUND(1.5,0)",
                  "B5": "=ROUND(2.5,0)", "B6": "=ROUND(1234.5678,-2)", "B7": "=ROUND(-2.5,0)"})
        self.assertEqual(w.evaluate("Data!B1"), 2.68)   # Python's round() gives 2.67
        self.assertEqual(w.evaluate("Data!B2"), -0.13)
        self.assertEqual(w.evaluate("Data!B3"), 1)      # round(0.5) is 0 in Python
        self.assertEqual(w.evaluate("Data!B4"), 2)
        self.assertEqual(w.evaluate("Data!B5"), 3)      # round(2.5) is 2 in Python
        self.assertEqual(w.evaluate("Data!B6"), 1200)
        self.assertEqual(w.evaluate("Data!B7"), -3)
