"""BKL-004: Gumroad CSV fallback parser. Temp paths only; no network."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("gumroad_csv_parser", ROOT / "src" / "measurement" / "gumroad_csv_parser.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class TestBKL004GumroadCSV(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.p = M.GumroadCSVParser(csv_dir=str(self.tmp / "exports"), parsed_path=str(self.tmp / "parsed.json"))

    def test_parser_handles_missing_file_gracefully(self):
        r = self.p.parse_export(str(self.tmp / "nope.csv"))
        self.assertEqual(r["status"], "FILE_NOT_FOUND")
        self.assertIsNone(r["data"])
        self.assertFalse((self.tmp / "parsed.json").exists())

    def test_latest_analytics_awaits_export_when_no_csv(self):
        r = self.p.get_latest_analytics()
        self.assertEqual(r["status"], "AWAITING_EXPORT")
        self.assertFalse(r["real_evidence"])

    def test_to_evidence_structure(self):
        ev = self.p.to_evidence()
        for k in ("source", "timestamp", "confidence", "data_url", "real_evidence", "status"):
            self.assertIn(k, ev)
        self.assertEqual(ev["confidence"], 0.0)
        self.assertFalse(ev["real_evidence"])
        self.assertEqual(ev["status"], "AWAITING_EXPORT")

    def test_parser_reads_valid_csv(self):
        csv_path = self.tmp / "exports" / "export.csv"
        csv_path.write_text(
            "Date,Product,Views,Sales,Revenue,Refunds\n"
            "2026-10-01,Etsy Bundle,12,1,$79.00,0\n"
            "2026-10-02,Etsy Bundle,8,0,$0.00,0\n"
            "2026-10-02,Appeal Kit,5,0,0,0\n", encoding="utf-8")
        r = self.p.parse_export(str(csv_path))
        self.assertEqual(r["status"], "PARSED")
        s = r["summary"]
        self.assertEqual((s["total_views"], s["total_sales"], s["total_revenue"]), (25, 1, 79.0))
        self.assertEqual(s["products"]["Etsy Bundle"]["views"], 20)
        self.assertEqual(s["date_range"], {"start": "2026-10-01", "end": "2026-10-02"})
        self.assertFalse(r["format_verified"])                     # layout not yet confirmed
        ev = self.p.to_evidence()
        self.assertTrue(ev["real_evidence"])
        self.assertEqual(ev["status"], "PARSED")
        # An unrecognized layout is refused, never guessed.
        bad = self.tmp / "exports" / "bad.csv"
        bad.write_text("foo,bar\n1,2\n", encoding="utf-8")
        self.assertEqual(self.p.parse_export(str(bad))["status"], "FORMAT_UNRECOGNIZED")


if __name__ == "__main__":
    unittest.main()
