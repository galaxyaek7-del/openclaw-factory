"""EXP-C81-001: the measurement status is computed, never assumed.

Pins the rules approved for the 2026-10-15 fix (reports/EXP-C81-001_diagnosis.md):
every metric is exactly "connected", "not connected" or "unverified";
"connected" requires a real successful response recorded in a file; the
experiment stays BLOCKED until the stopping-rule data is connected; and the
old hard-coded status is kept in the output for audit.

Temp paths only. No network, no Gumroad call, no write outside a temp dir.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cycle81_eval", ROOT / "scripts" / "cycle81_product_evaluation.py")
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)

TAG = "https://x.gumroad.com/l/bfhpzl?utm_source=etsy_seo_cta&amp;utm_medium=site&amp;utm_campaign=etsy_suspension_cluster"


class TestComputedMeasurementStatus(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.site = self.tmp / "site"
        self.site.mkdir()
        (self.site / "guide.html").write_text(
            f'<html><head><title>T</title></head><body><h1>Etsy  Guide</h1><a href="{TAG}">buy</a></body></html>',
            encoding="utf-8")
        (self.site / "other.html").write_text("<h1>Unrelated</h1>", encoding="utf-8")
        self.views = self.tmp / "views.jsonl"
        self.export = self.tmp / "export"
        self.probe = self.tmp / "probe.json"

    def run_compute(self):
        return E.compute_measurement(probe_path=str(self.probe), page_views_path=str(self.views),
                                     export_dir=str(self.export), site_dir=str(self.site))

    def write_probe(self, **result):
        self.probe.write_text(json.dumps({"result": result}), encoding="utf-8")

    def test_metrics_are_computed_from_recorded_evidence_only(self):
        # Nothing recorded anywhere: nothing may claim to be connected.
        m = self.run_compute()
        self.assertEqual(m["metrics"]["purchases"]["status"], "unverified")
        self.assertEqual(m["metrics"]["page_views"]["status"], "not connected")
        self.assertEqual(m["metrics"]["listing_views_and_tagged_clicks"]["status"], "not connected")
        self.assertTrue(m["measurement_status"].startswith("BLOCKED"))

        # Purchases: connected only on a recorded, clear success.
        self.write_probe(http_status=200, success_field=True, records_returned=0,
                         response_received_at_utc="2026-10-15T22:32:32+00:00")
        self.assertEqual(self.run_compute()["metrics"]["purchases"]["status"], "connected")
        for bad in ({"http_status": 200, "success_field": False, "records_returned": 0},
                    {"http_status": 200, "success_field": True, "records_returned": None},
                    {"http_status": 500, "success_field": None, "records_returned": None},
                    {"http_status": None}):
            self.write_probe(**bad)
            self.assertEqual(self.run_compute()["metrics"]["purchases"]["status"], "unverified", bad)
        self.write_probe(http_status=404)
        p = self.run_compute()["metrics"]["purchases"]
        self.assertEqual(p["status"], "not connected")
        self.assertIn("endpoint not available", p["reason"])
        self.probe.write_text("{not json", encoding="utf-8")
        self.assertEqual(self.run_compute()["metrics"]["purchases"]["status"], "unverified")

        # Page views: only a recorded event from an experiment page connects it.
        self.views.write_text(json.dumps({"page_id": "c89-ua-probe"}) + "\n"
                              + json.dumps({"page_id": "Unrelated"}) + "\n", encoding="utf-8")
        self.assertEqual(self.run_compute()["metrics"]["page_views"]["status"], "not connected")
        (self.site / "guide.html").write_text(
            f'<meta name="gf-pageview-endpoint" content="https://r.example/api/page-view">'
            f'<h1>Etsy Guide</h1><a href="{TAG}">buy</a>', encoding="utf-8")
        self.assertEqual(self.run_compute()["metrics"]["page_views"]["status"], "unverified")
        with self.views.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"page_id": "Etsy Guide"}) + "\n")
        self.assertEqual(self.run_compute()["metrics"]["page_views"]["status"], "connected")

        # Listing analytics: an export file alone is never "connected".
        self.export.mkdir()
        (self.export / "gumroad_90d.csv").write_text("views\n12\n", encoding="utf-8")
        m = self.run_compute()
        self.assertEqual(m["metrics"]["listing_views_and_tagged_clicks"]["status"], "unverified")
        # Purchases + page views connected is still not enough to judge the stopping rule.
        self.write_probe(http_status=200, success_field=True, records_returned=3)
        m = self.run_compute()
        self.assertTrue(m["measurement_status"].startswith("BLOCKED"))
        self.assertIn("listing_views_and_tagged_clicks", m["measurement_status"])

        for metric in m["metrics"].values():
            self.assertIn(metric["status"], ("connected", "not connected", "unverified"))
            self.assertTrue(metric["reason"] and metric["evidence"])

    def test_legacy_hardcoded_status_is_kept_for_audit(self):
        self.assertEqual(E.LEGACY_MEASUREMENT_STATUS,
                         "BLOCKED - the tagged links exist, but no analytics endpoint can be read "
                         "without the founder, so the experiment cannot currently be judged either way")
        self.assertNotIn("measurement_status", E.EXPERIMENT)       # no stale literal left behind
        cwd = os.getcwd()
        out_dir = self.tmp / "run"
        (out_dir / "data").mkdir(parents=True)
        try:
            os.chdir(out_dir)
            sys.stdout, saved = open(os.devnull, "w", encoding="utf-8"), sys.stdout
            try:
                E.main()
            finally:
                sys.stdout.close()
                sys.stdout = saved
        finally:
            os.chdir(cwd)
        exp = json.loads((out_dir / "data" / "cycle81_product_evaluation.json").read_text(encoding="utf-8"))["experiment"]
        self.assertEqual(exp["measurement_status_legacy_hardcoded"], E.LEGACY_MEASUREMENT_STATUS)
        self.assertIn(exp["measurement_status"].split(" ")[0], ("BLOCKED", "MEASURABLE"))
        self.assertEqual(set(exp["measurement_metrics"]),
                         {"purchases", "page_views", "listing_views_and_tagged_clicks"})


if __name__ == "__main__":
    unittest.main()
