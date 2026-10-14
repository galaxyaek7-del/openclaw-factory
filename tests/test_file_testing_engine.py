"""Tests for file_testing_engine -- per-format, including negative cases.

E.2 of the directive asks for negative tests proving that non-compliant and
unknown-state cases do not pass automatically. Every test here is written the
same way: build a file that is KNOWN BAD, assert it FAILS or is UNKNOWN, and
assert it is never silently PASS. A tester that only has happy-path coverage
cannot distinguish "checked and clean" from "never actually looked".
"""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import file_testing_engine as fte

TMP = Path(tempfile.gettempdir()) / "gf_file_tests"


def _p(name: str) -> Path:
    TMP.mkdir(parents=True, exist_ok=True)
    return TMP / name


class TestDispatch(unittest.TestCase):
    def test_detects_each_supported_kind(self):
        for ext, want in ((".pdf", "pdf"), (".xlsx", "xlsx"), (".docx", "docx"),
                          (".zip", "zip"), (".html", "html")):
            self.assertEqual(fte.detect_kind(Path(f"x{ext}")), want)

    def test_unknown_kind_has_no_tester_and_is_unknown(self):
        r = fte.test_file(_p("thing.psd"))
        self.assertEqual(r.status, fte.UNKNOWN)

    def test_missing_file_is_unknown_not_pass(self):
        r = fte.test_file(_p("definitely_absent.xlsx"))
        self.assertEqual(r.status, fte.UNKNOWN)

    def test_unparseable_file_is_unknown_not_pass(self):
        f = _p("broken.xlsx")
        f.write_bytes(b"this is not a zip container at all")
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.UNKNOWN,
                         "a file we cannot parse is UNKNOWN, never PASS")


class TestPdf(unittest.TestCase):
    def test_bad_magic_fails(self):
        f = _p("bad.pdf")
        f.write_bytes(b"NOTAPDF" + b"0" * 200)
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.FAIL)

    def test_real_pdf_passes(self):
        src = Path("books/eu_ai_act_compliance_toolkit_preview.pdf")
        if not src.exists():
            self.skipTest("fixture absent")
        r = fte.test_file(src)
        self.assertEqual(r.status, fte.PASS, r.problems)
        self.assertGreater(r.detail["pages"], 0)


class TestXlsx(unittest.TestCase):
    def _wb(self, name, cells, sheet="Sheet1"):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet
        for row in cells:
            ws.append(row)
        p = _p(name)
        wb.save(str(p))
        return p

    def test_workbook_with_formulas_passes(self):
        f = self._wb("good.xlsx", [["Cost", "Qty", "Total"],
                                   [10, 2, "=A2*B2"]])
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.PASS, r.problems)
        self.assertEqual(r.detail["formula_count"], 1)

    def test_zero_formula_workbook_is_flagged(self):
        """The systemic finding: a workbook sold as a tool with no formulas."""
        f = self._wb("static.xlsx", [["Option", "Cost", "Timeline"],
                                     ["Do nothing", 0, "forever"]])
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.FAIL)
        self.assertIn("no_formulas", r.detail)

    def test_broken_reference_is_caught(self):
        f = self._wb("brokenref.xlsx", [["A", "B"], [1, "=#REF!"]])
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.FAIL)
        self.assertTrue(any("broken reference" in x for x in r.problems))

    def test_blank_sheet_is_caught(self):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data"
        ws.append(["a", "b"])
        ws2 = wb.create_sheet("Empty")
        p = _p("blanksheet.xlsx")
        wb.save(str(p))
        r = fte.test_file(p)
        self.assertEqual(r.status, fte.FAIL)
        self.assertIn("Empty", r.detail["blank_sheets"])

    def test_content_requirement_can_be_waived(self):
        f = self._wb("register.xlsx", [["Item", "Due"], ["Permit", "2026-01-01"]])
        r = fte.test_xlsx(f, require_content=False)
        self.assertEqual(r.status, fte.PASS, r.problems)


class TestZip(unittest.TestCase):
    def _zip(self, name, members):
        p = _p(name)
        with zipfile.ZipFile(p, "w") as z:
            for member, data in members.items():
                z.writestr(member, data)
        return p

    def test_clean_zip_passes(self):
        f = self._zip("clean.zip", {"guide.pdf": b"%PDF-1.4 fake",
                                    "sheet.xlsx": b"PK fake"})
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.PASS, r.problems)

    def test_zero_byte_member_fails(self):
        f = self._zip("zero.zip", {"guide.pdf": b"%PDF", "empty.pdf": b""})
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.FAIL)
        self.assertTrue(any("zero-byte" in x for x in r.problems))

    def test_duplicate_member_fails(self):
        f = _p("dupe.zip")
        with zipfile.ZipFile(f, "w") as z:
            z.writestr("a.txt", "one")
            z.writestr("a.txt", "two")
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.FAIL)
        self.assertTrue(any("duplicate" in x for x in r.problems))

    def test_missing_required_member_fails(self):
        f = self._zip("missing.zip", {"readme.txt": "hi"})
        r = fte.test_zip(f, required=["workbook"])
        self.assertEqual(r.status, fte.FAIL)
        self.assertTrue(any("required member missing" in x for x in r.problems))

    def test_corrupt_archive_is_unknown_not_pass(self):
        f = _p("corrupt.zip")
        f.write_bytes(b"PK\x03\x04 truncated nonsense")
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.UNKNOWN)


class TestHtml(unittest.TestCase):
    def test_clean_page_passes(self):
        f = _p("ok.html")
        f.write_text("<html><head><title>Real Title</title></head>"
                     "<body><p>" + "word " * 40 + "</p></body></html>",
                     encoding="utf-8")
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.PASS, r.problems)

    def test_missing_title_fails(self):
        f = _p("notitle.html")
        f.write_text("<html><body><p>" + "word " * 40 + "</p></body></html>",
                     encoding="utf-8")
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.FAIL)
        self.assertTrue(any("<title>" in x for x in r.problems))

    def test_empty_body_fails(self):
        f = _p("empty.html")
        f.write_text("<html><head><title>T</title></head><body></body></html>",
                     encoding="utf-8")
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.FAIL)


class TestDocx(unittest.TestCase):
    def test_real_docx_roundtrip(self):
        try:
            import docx
        except ImportError:
            self.skipTest("python-docx absent")
        d = docx.Document()
        d.add_paragraph("A real paragraph with several words in it.")
        f = _p("real.docx")
        d.save(str(f))
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.PASS, r.problems)

    def test_broken_docx_is_unknown(self):
        f = _p("bad.docx")
        f.write_bytes(b"PK not really a docx")
        r = fte.test_file(f)
        self.assertEqual(r.status, fte.UNKNOWN)


class TestRealCatalogRegression(unittest.TestCase):
    """Guards the defects this round found, so they cannot silently return."""

    def test_shipped_tracker_has_no_formulas_and_is_flagged(self):
        # Finding updated 2026-10-14: the tracker was repaired by
        # workbook_upgrader.py. The original is kept in backups/ and must
        # still be flagged; the repaired file must pass with live formulas.
        orig = Path("backups/product_repair_2026-10-14/books/ccpa_compliance_tracker.xlsx")
        if orig.exists():
            r = fte.test_file(orig)
            self.assertEqual(r.detail.get("formula_count"), 0)
            self.assertEqual(r.status, fte.FAIL)
        p = Path("books/ccpa_compliance_tracker.xlsx")
        if not p.exists():
            self.skipTest("fixture absent")
        r = fte.test_file(p)
        self.assertGreater(r.detail.get("formula_count"), 0)
        self.assertEqual(r.status, fte.PASS, r.problems)

    def test_toolkit_pdf_still_parses(self):
        p = Path("books/eu_ai_act_compliance_toolkit_v2.pdf")
        if not p.exists():
            self.skipTest("fixture absent")
        r = fte.test_file(p)
        self.assertEqual(r.status, fte.PASS, r.problems)


if __name__ == "__main__":
    unittest.main(verbosity=2)