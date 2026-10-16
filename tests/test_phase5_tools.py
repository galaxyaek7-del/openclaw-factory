"""Phase 5: Search Console helper, page-view endpoint helper, sales-export parsing.

Temp paths for every write. The one test touching the real site is a dry run
and proves the files are byte-identical afterwards. No network.
"""
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GSC = _load("gsc_p5", "scripts/search_console_verify.py")
EP = _load("ep_p5", "scripts/set_pageview_endpoint.py")
CSV = _load("csv_p5", "src/measurement/gumroad_csv_parser.py")
EVAL = _load("eval_p5", "scripts/cycle81_product_evaluation.py")


class TestPhase5Tools(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_search_console_file_is_validated_and_never_overwritten(self):
        for bad in ("google123.html", "evil.html", "../google0123456789abcdef.html", ""):
            self.assertFalse(GSC.plan(bad, str(self.tmp))["ok"], bad)
        name = "google0123456789abcdef.html"
        self.assertEqual(GSC.plan(name, str(self.tmp))["action"], "create")
        self.assertFalse((self.tmp / name).exists())                      # plan writes nothing
        self.assertEqual(GSC.apply(name, str(self.tmp))["action"], "created")
        self.assertEqual((self.tmp / name).read_text(encoding="utf-8").strip(), f"google-site-verification: {name}")
        self.assertEqual(GSC.apply(name, str(self.tmp))["action"], "already_present")
        (self.tmp / name).write_text("something else", encoding="utf-8")
        self.assertFalse(GSC.apply(name, str(self.tmp))["ok"])

    def test_pageview_endpoint_edit_is_scoped_idempotent_and_reversible(self):
        site = self.tmp / "site"
        site.mkdir()
        tagged = '<html><head>\n<title>t</title>\n</head><body><a href="x?utm_campaign=etsy_suspension_cluster">b</a>' \
                 '<script src="assets/gf-pageview.js" defer></script></body></html>'
        other = '<html><head>\n</head><body><script src="assets/gf-pageview.js"></script></body></html>'
        (site / "exp.html").write_text(tagged, encoding="utf-8")
        (site / "other.html").write_text(other, encoding="utf-8")
        for bad in ("http://r.example/api/page-view", "https://localhost/api", "https://127.0.0.1/x",
                    'https://r.example/x" onload="y', "not a url"):
            self.assertFalse(EP.run(bad, apply=True, site=str(site))["ok"], bad)
        url = "https://r.example/api/page-view"
        r = EP.run(url, apply=True, site=str(site))
        self.assertEqual(r["pages_changed"], ["exp.html"])               # experiment scope only
        html = (site / "exp.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('name="gf-pageview-endpoint"'), 1)
        self.assertIn(f'content="{url}"', html)
        self.assertEqual((site / "other.html").read_text(encoding="utf-8"), other)
        self.assertEqual(EP.run(url, apply=True, site=str(site))["pages_changed"], [])   # idempotent
        EP.run(None, apply=True, remove=True, site=str(site))
        self.assertEqual((site / "exp.html").read_text(encoding="utf-8"), tagged)        # exact rollback

    def test_dry_run_on_the_real_site_changes_nothing(self):
        pages = EP.target_pages()
        self.assertEqual(len(pages), 8)
        digest = lambda: {p: hashlib.sha256((ROOT / "customer_site" / p).read_bytes()).hexdigest() for p in pages}
        before = digest()
        r = EP.run("https://r.example/api/page-view", apply=False)
        self.assertTrue(r["ok"])
        self.assertFalse(r["applied"])
        self.assertEqual(digest(), before)

    def test_sales_export_layout_reports_no_views_and_keeps_no_buyer_ids(self):
        f = self.tmp / "sales.csv"
        f.write_text("Purchase ID,Item Name,Buyer Name,Purchase Email,Purchase Date,Sale Price ($),Refunded?,Referrer\n"
                     "abc1,Etsy Bundle,A B,a@x.com,2026-10-01 10:00,79.00,false,"
                     "https://galaxyaek7-del.github.io/x?utm_campaign=etsy_suspension_cluster\n"
                     "abc2,Etsy Bundle,C D,c@x.com,2026-10-03 11:00,79.00,true,direct\n", encoding="utf-8")
        p = CSV.GumroadCSVParser(csv_dir=str(self.tmp / "e"), parsed_path=str(self.tmp / "parsed.json"))
        r = p.parse_export(str(f))
        self.assertEqual((r["status"], r["layout"], r["has_views"]), ("PARSED", "SALES_EXPORT", False))
        s = r["summary"]
        self.assertIsNone(s["total_views"])                               # not in file: None, never 0
        self.assertEqual((s["total_sales"], s["total_refunds"], s["total_revenue"]), (2, 1, 79.0))
        self.assertEqual(s["utm_campaigns"], {"etsy_suspension_cluster": 1})
        dumped = (self.tmp / "parsed.json").read_text(encoding="utf-8")
        for pii in ("abc1", "a@x.com", "A B"):
            self.assertNotIn(pii, dumped)
        self.assertFalse(p.to_evidence()["has_views"])

    def test_listing_analytics_connects_only_when_views_are_present(self):
        parsed = self.tmp / "parsed.json"
        parsed.write_text(json.dumps({"status": "PARSED", "layout": "SALES_EXPORT", "has_views": False}), encoding="utf-8")
        self.assertFalse(EVAL.check_gumroad_csv_parser(str(parsed))["connected"])
        parsed.write_text(json.dumps({"status": "PARSED", "layout": "DAILY_AGGREGATE", "has_views": True}), encoding="utf-8")
        self.assertTrue(EVAL.check_gumroad_csv_parser(str(parsed))["connected"])
        parsed.write_text(json.dumps({"status": "FORMAT_UNRECOGNIZED"}), encoding="utf-8")
        self.assertFalse(EVAL.check_gumroad_csv_parser(str(parsed))["connected"])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
