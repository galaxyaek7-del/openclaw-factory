"""release_gate.py — promise-vs-delivery release gate (2026-10-22).

Fixtures are generated in a temp dir (reportlab PDF, openpyxl workbook).
No network, no platform calls, no writes outside the temp dir.

    python -m pytest tests/test_release_gate.py -q
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import release_gate as rg  # noqa: E402

RIGHTS = {"reviewer": "test", "basis": "original content, no third-party assets"}
DEMAND = "fixture demand evidence"


def make_pdf(path, words):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path), pagesize=letter)
    line, y = [], 750
    for i in range(words):
        line.append(f"word{i}")
        if len(line) == 12:
            c.drawString(40, y, " ".join(line))
            line, y = [], y - 14
            if y < 60:
                c.showPage()
                y = 750
    if line:
        c.drawString(40, y, " ".join(line))
    c.save()


def make_xlsx(path, formulas=True):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cost planner"
    ws.append(["Item", "Qty", "Unit", "Total"])
    ws.append(["Fee", 2, 10, "=B2*C2" if formulas else 20])
    wb.save(str(path))


class _Tmp(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.addCleanup(self._d.cleanup)
        self.d = Path(self._d.name)
        self.pdf = self.d / "guide.pdf"
        make_pdf(self.pdf, 2000)
        self.xlsx = self.d / "planner.xlsx"
        make_xlsx(self.xlsx)


class TestGate(_Tmp):
    def test_missing_deliverable_fails(self):
        r = rg.evaluate("p", [self.d / "nope.pdf"], "A guide.", 29, DEMAND, RIGHTS)
        self.assertEqual(r["status"], "QA_FAILED")

    def test_promised_spreadsheet_absent_fails(self):
        r = rg.evaluate("p", [self.pdf], "Includes an XLSX cost planner workbook.", 49, DEMAND, RIGHTS)
        self.assertEqual(r["status"], "QA_FAILED")
        self.assertIn("PROMISES_SPREADSHEET_NOT_ATTACHED", r["blocking"])

    def test_complete_package_reaches_authorization_never_published(self):
        r = rg.evaluate("p", [self.pdf, self.xlsx], "PDF guide + XLSX cost planner workbook.", 49, DEMAND, RIGHTS)
        self.assertEqual(r["status"], "READY_FOR_AUTHORIZATION", r["blocking"] + r["holds"])
        self.assertEqual(r["stages"]["AUTHORIZATION_CHECK"]["status"], "AWAITING_FOUNDER")
        names = {m["name"] for m in r["stages"]["PACKAGING"]["manifest"]}
        self.assertEqual(names, {"guide.pdf", "planner.xlsx"})
        self.assertTrue(all(len(m["sha256"]) == 64 for m in r["stages"]["PACKAGING"]["manifest"]))

    def test_thin_pdf_at_a_high_price_is_held(self):
        thin = self.d / "thin.pdf"
        make_pdf(thin, 300)
        r = rg.evaluate("p", [thin], "A guide.", 59, DEMAND, RIGHTS)
        self.assertEqual(r["status"], "HOLD")
        self.assertTrue(any(h.startswith("substance below price") for h in r["holds"]))
        r2 = rg.evaluate("p", [thin], "A guide.", 59, DEMAND, RIGHTS, price_basis=rg.EXPERIMENTAL_PRICE_LABEL)
        self.assertEqual(r2["status"], "READY_FOR_AUTHORIZATION")

    def test_working_tool_offsets_short_pdf(self):
        thin = self.d / "thin.pdf"
        make_pdf(thin, 300)
        r = rg.evaluate("p", [thin, self.xlsx], "Guide + XLSX workbook.", 59, DEMAND, RIGHTS)
        self.assertEqual(r["status"], "READY_FOR_AUTHORIZATION", r["holds"])

    def test_formula_free_workbook_fails_qa(self):
        static = self.d / "static.xlsx"
        make_xlsx(static, formulas=False)
        r = rg.evaluate("p", [self.pdf, static], "Guide + XLSX workbook.", 49, DEMAND, RIGHTS)
        self.assertEqual(r["status"], "QA_FAILED")

    def test_rights_review_and_demand_are_required(self):
        r = rg.evaluate("p", [self.pdf, self.xlsx], "Guide + XLSX workbook.", 49)
        self.assertEqual(r["status"], "HOLD")
        self.assertIn("human rights/policy review not recorded", r["holds"])
        self.assertIn("no demand evidence recorded", r["holds"])

    def test_listing_residue_fails(self):
        r = rg.evaluate("p", [self.pdf], "Guaranteed income with APPLICATIONImplementation.", 29, DEMAND, RIGHTS)
        self.assertEqual(r["status"], "QA_FAILED")


class TestState(_Tmp):
    def test_record_is_idempotent(self):
        state = self.d / "state.jsonl"
        r = rg.evaluate("p", [self.pdf, self.xlsx], "Guide + XLSX workbook.", 49, DEMAND, RIGHTS)
        self.assertTrue(rg.record(r, state))
        self.assertFalse(rg.record(r, state))
        self.assertEqual(len(state.read_text(encoding="utf-8").splitlines()), 1)
        self.assertEqual(rg.latest("p", state)["status"], "READY_FOR_AUTHORIZATION")

    def test_cannot_record_a_published_status(self):
        r = rg.evaluate("p", [self.pdf, self.xlsx], "Guide + XLSX workbook.", 49, DEMAND, RIGHTS)
        r["status"] = "PUBLISHED_VERIFIED"
        with self.assertRaises(AssertionError):
            rg.record(r, self.d / "state.jsonl")

    def test_module_has_no_publish_or_write_path_to_platforms(self):
        src = (ROOT / "release_gate.py").read_text(encoding="utf-8")
        for forbidden in ("gumroad_publisher", "distribute(", "urlopen", "requests.", "enable_product",
                          "create_checkout"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
