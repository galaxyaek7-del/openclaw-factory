"""scripts/apply_thin_listing_disclosures_20261031.py: the disclosure is measured
from the delivered file, idempotent, and the dry run never writes. Fakes only."""
import io
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import apply_thin_listing_disclosures_20261031 as tl  # noqa: E402


def pdf(n_words):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(40, 800, " ".join(["word"] * n_words))
    c.save()
    return buf.getvalue()


class FakeGumroad:
    def __init__(self, desc):
        self.desc, self.writes = desc, []

    def list_products(self, token):
        return [{"id": "P1", "short_url": "https://x.gumroad.com/l/roxdbe"}]

    def get_product(self, token, pid):
        return {"id": pid, "name": "Pack", "published": True, "description": self.desc, "files": [{"url": "https://f/1"}]}

    def update_product_description_scoped(self, *a, **k):
        self.writes.append(a)


class Disclosures(unittest.TestCase):
    def setUp(self):
        self._targets = tl.TARGETS
        tl.TARGETS = ["roxdbe"]

    def tearDown(self):
        tl.TARGETS = self._targets

    def test_counts_come_from_the_file(self):
        gp = FakeGumroad("A churn pack.")
        a = tl.plan("t", gp, fetch=lambda u: pdf(12))[0]
        self.assertIn("**What you actually receive:** a 1-page PDF (12 words).", a["new_description"])
        self.assertTrue(a["new_description"].startswith("A churn pack."))
        self.assertEqual(gp.writes, [])

    def test_already_disclosed_listing_is_left_alone(self):
        gp = FakeGumroad("A pack.\n\n**What you actually receive:** a 1-page PDF (9 words).")
        self.assertTrue(tl.plan("t", gp, fetch=lambda u: 1 / 0)[0]["already_applied"])

    def test_zip_with_workbook_and_pdf(self):
        from openpyxl import Workbook
        wb, xb = Workbook(), io.BytesIO()
        wb.create_sheet("B")
        wb.save(xb)
        zb = io.BytesIO()
        with zipfile.ZipFile(zb, "w") as z:
            z.writestr("pack.xlsx", xb.getvalue())
            z.writestr("guide.pdf", pdf(5))
        m = tl.measure(zb.getvalue())
        self.assertEqual(tl.disclosure(m).strip(),
                         "**What you actually receive:** a ZIP with a 2-sheet starter workbook and a 1-page PDF (5 words). "
                         "It is a condensed operating reference, not an expanded toolkit. 0 sales recorded for this item "
                         "to date; no reviews.")

    def test_a_bare_workbook_gets_no_line(self):
        from openpyxl import Workbook
        xb = io.BytesIO()
        Workbook().save(xb)
        self.assertIsNone(tl.disclosure(tl.measure(xb.getvalue())))

    def test_the_report_is_kept_out_of_git(self):
        import subprocess
        r = subprocess.run(["git", "check-ignore", "-q", "--no-index", "data/thin_listing_disclosures_20261031.json"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
