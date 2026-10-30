"""Phase 3 demonstrations (2026-10-29): Merchant Center feed preflight,
accessibility quick-check, EAA penalty register. Synthetic inputs and temp
files; the committed demo outputs are checked for reproducibility."""
import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "feed_preflight"))
sys.path.insert(0, str(ROOT / "services" / "accessibility_check"))
sys.path.insert(0, str(ROOT))
import preflight as pf  # noqa: E402
import check as a11y  # noqa: E402


def feed(*rows, cols=("id", "title", "description", "link", "image_link", "availability", "price", "gtin", "brand",
                      "mpn", "identifier_exists", "condition")):
    base = {"id": "A1", "title": "Mug", "description": "A mug", "link": "https://x.example/1",
            "image_link": "https://x.example/1.jpg", "availability": "in_stock", "price": "10.00 USD",
            "gtin": "", "brand": "B", "mpn": "M1", "identifier_exists": "", "condition": "new"}
    out = []
    for r in rows:
        x = dict(base)
        x.update(r)
        out.append({c: x.get(c, "") for c in cols})
    return out


def issues(report):
    return [(f["field"], f["severity"]) for f in report["findings"]]


class FeedPreflight(unittest.TestCase):
    def test_gs1_check_digit(self):
        self.assertTrue(pf.gtin_check_digit_ok("4006381333931"))   # GS1's own worked example
        self.assertFalse(pf.gtin_check_digit_ok("4006381333932"))
        self.assertIsNone(pf.check_gtin("400-638133393-1"))         # dashes ignored, as Google does
        self.assertIn("digits", pf.check_gtin("12345"))
        self.assertIn("restricted", pf.check_gtin("2000000000008"))
        # a UPC-12 starting 4 (in-store number system) reads as 04... in 13-digit form
        upc = next("40000000000" + d for d in "0123456789" if pf.gtin_check_digit_ok("40000000000" + d))
        self.assertIn("restricted", pf.check_gtin(upc))
        ordinary = next("06123450000" + d for d in "0123456789" if pf.gtin_check_digit_ok("06123450000" + d))
        self.assertIsNone(pf.check_gtin(ordinary))
        self.assertIn("coupon", pf.check_gtin(next("990000000000" + d for d in "0123456789"
                                                   if pf.gtin_check_digit_ok("990000000000" + d))))

    def test_a_clean_row_has_no_findings(self):
        r = pf.preflight(feed({}))
        self.assertEqual((r["errors"], r["warnings"], r["rows_clean"]), (0, 0, 1))

    def test_each_rule(self):
        cases = [({"price": "10,00 USD"}, ("price", "error")), ({"price": "0.00 USD"}, ("price", "error")),
                 ({"availability": "In Stock"}, ("availability", "error")), ({"link": "x.example/1"}, ("link", "error")),
                 ({"title": "x" * 151}, ("title", "error")), ({"gtin": "4006381333932"}, ("gtin", "error")),
                 ({"gtin": "4006381333931", "identifier_exists": "no"}, ("identifier_exists", "error")),
                 ({"brand": "", "mpn": ""}, ("gtin", "warning")), ({"condition": "mint"}, ("condition", "error")),
                 ({"image_link": ""}, ("image_link", "error"))]
        for row, expected in cases:
            self.assertIn(expected, issues(pf.preflight(feed(row))), row)

    def test_duplicate_ids_and_missing_columns(self):
        r = pf.preflight(feed({}, {}))
        self.assertEqual(sum(1 for f in r["findings"] if f["field"] == "id"), 2)
        r = pf.preflight([{"id": "A", "title": "t"}])
        missing = {f["field"] for f in r["findings"] if f["issue"] == "required column is missing"}
        self.assertEqual(missing, {"description", "link", "image_link", "availability", "price"})

    def test_a_feed_with_credentials_is_refused(self):
        r = pf.preflight(feed({}, cols=("id", "title", "api_key")))
        self.assertEqual(r["status"], "REFUSED")

    def test_tab_separated_feeds_are_read(self):
        rows = pf.read_feed("id\ttitle\nA1\tMug\n")
        self.assertEqual(rows, [{"id": "A1", "title": "Mug"}])

    def test_demo_package_is_reproducible(self):
        pkg = ROOT / "services" / "feed_preflight" / "demo_package"
        committed = json.loads((pkg / "report.json").read_text(encoding="utf-8"))
        fresh = pf.preflight(pf.read_feed((pkg / "input_feed.csv").read_text(encoding="utf-8")))
        self.assertEqual(committed, json.loads(json.dumps(fresh)))


class AccessibilityCheck(unittest.TestCase):
    def found(self, html):
        return {(f["wcag"], f["severity"]) for f in a11y.check_html(html)}

    def test_a_good_page_has_no_findings(self):
        html = ('<html lang="en"><head><title>T</title><meta name="viewport" content="width=device-width, '
                'initial-scale=1"></head><body><h1>T</h1><h2>S</h2><img src="a.png" alt="A">'
                '<a href="/x">Go</a><a href="/y" aria-label="Cart"><svg></svg></a>'
                '<label for="e">Email</label><input id="e" type="email"><label>Q <input name="q"></label>'
                '<input type="hidden" name="t"><input type="text" name="website" aria-hidden="true" tabindex="-1">'
                '<button>Send</button><input type="submit" value="Go"></body></html>')
        self.assertEqual(a11y.check_html(html), [])

    def test_each_fault_is_found(self):
        f = self.found('<html><head><meta name="viewport" content="user-scalable=no"></head><body>'
                       '<h2>x</h2><h4>y</h4><img src="a.png"><a href="/c"></a><button></button>'
                       '<input name="e"><input name="q" placeholder="Search"><input name="w" tabindex="-1">'
                       '</body></html>')
        for expected in (("3.1.1", "error"), ("2.4.2", "error"), ("1.4.4", "error"), ("1.1.1", "error"),
                         ("2.4.4", "error"), ("4.1.2", "error"), ("1.3.1", "error"), ("1.3.1", "warning")):
            self.assertIn(expected, f)

    def test_decorative_images_and_anchors_without_href_are_not_flagged(self):
        html = ('<html lang="en"><head><title>T</title></head><body><h1>T</h1>'
                '<img src="d.png" role="presentation"><a name="top"></a></body></html>')
        self.assertEqual(a11y.check_html(html), [])

    def test_report_never_claims_compliance(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "p.html").write_text('<html lang="en"><title>x</title><h1>x</h1></html>', encoding="utf-8")
            r = a11y.check_path(d)
        self.assertIn("not evidence of WCAG", r["statement"])
        self.assertTrue(r["not_checked"])

    def test_synthetic_demo_is_reproducible(self):
        pkg = ROOT / "services" / "accessibility_check" / "demo_package"
        committed = json.loads((pkg / "synthetic_report.json").read_text(encoding="utf-8"))
        fresh = a11y.check_path(pkg / "synthetic_page.html")
        self.assertEqual(committed, json.loads(json.dumps(fresh)))


class EaaPenaltyRegister(unittest.TestCase):
    REL = ROOT / "data_products" / "releases" / "eaa-penalty-register" / "2026-10-29"

    def test_release_validates_and_matches_its_card(self):
        v = json.loads((self.REL / "validation.json").read_text(encoding="utf-8"))
        self.assertEqual(v["status"], "PASS")
        from data_products import datacard
        card = json.loads((self.REL / "datacard.json").read_text(encoding="utf-8"))
        self.assertEqual(card["files"][0]["sha256"], datacard.sha256_file(self.REL / "eaa_penalty_register.csv"))

    def test_every_row_states_how_it_was_verified(self):
        with open(self.REL / "eaa_penalty_register.csv", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertTrue(all(r["status"] in ("VERIFIED_OFFICIAL_TEXT", "SECONDARY_UNVERIFIED") for r in rows))
        verified = {r["country"] for r in rows if r["status"] == "VERIFIED_OFFICIAL_TEXT"}
        self.assertEqual(verified, {"DE", "IE"})
        for r in rows:
            if r["status"] == "VERIFIED_OFFICIAL_TEXT":
                self.assertTrue(r["source_url"].startswith(("https://www.gesetze-im-internet.de/",
                                                            "https://www.irishstatutebook.ie/")))
        de = [r for r in rows if r["country"] == "DE"]
        self.assertEqual(sorted(r["max_fine_eur"] for r in de), ["10000", "100000"])


if __name__ == "__main__":
    unittest.main()
