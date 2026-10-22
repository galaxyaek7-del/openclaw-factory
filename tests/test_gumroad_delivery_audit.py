"""scripts/gumroad_delivery_audit.classify() — pure rules, fixtures only.

    python -m pytest tests/test_gumroad_delivery_audit.py -q
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gumroad_delivery_audit import classify  # noqa: E402


def prod(desc="", files=(), price=4900, published=True, **kw):
    p = {"short_url": "https://x.gumroad.com/l/abc", "name": "P", "published": published, "price": price,
         "description": desc, "files": list(files)}
    p.update(kw)
    return p


PDF = {"filetype": "pdf", "size": 120_000, "name": "guide"}


class TestClassify(unittest.TestCase):
    def test_promised_spreadsheet_missing(self):
        r = classify(prod("Includes a four-sheet docket tracker.", [PDF]))
        self.assertIn("PROMISES_SPREADSHEET_NOT_ATTACHED", r["issues"])

    def test_spreadsheet_attached_is_fine(self):
        r = classify(prod("Workbook (Excel) included.", [PDF, {"filetype": "xlsx", "size": 20_000}]))
        self.assertEqual(r["issues"], [])

    def test_zip_is_unverified_not_a_mismatch(self):
        r = classify(prod("Excel + PDF in one ZIP.", [{"filetype": "zip", "size": 90_000}]))
        self.assertEqual(r["issues"], ["ZIP_CONTENTS_UNVERIFIED"])

    def test_the_real_gpsr_listing_wording(self):
        r = classify(prod("YOU RECEIVE: PDF guide + PDF cost planner (Cost planner / SKU tracker). Instant download.",
                          [{"filetype": "pdf", "size": 18_208}]))
        self.assertIn("PROMISES_MORE_FILES_THAN_ATTACHED", r["issues"])

    def test_thin_paid_deliverable(self):
        r = classify(prod("A guide.", [{"filetype": "pdf", "size": 3_726}]))
        self.assertIn("THIN_DELIVERABLE", r["issues"])
        self.assertNotIn("THIN_DELIVERABLE", classify(prod("A guide.", [{"filetype": "pdf", "size": 3_726}],
                                                            price=0))["issues"])

    def test_published_without_files(self):
        self.assertIn("PUBLISHED_WITHOUT_DELIVERABLE", classify(prod("x", []))["issues"])
        self.assertNotIn("PUBLISHED_WITHOUT_DELIVERABLE", classify(prod("x", [], published=False))["issues"])

    def test_preview_file_flagged(self):
        r = classify(prod("Toolkit.", [PDF, {"filetype": "pdf", "size": 100_000, "name": "toolkit_preview"}]))
        self.assertIn("PREVIEW_FILE_DELIVERED", r["issues"])


if __name__ == "__main__":
    unittest.main()
