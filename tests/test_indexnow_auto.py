"""scripts/indexnow_auto.py: only changed, published, live pages are sent;
once per day; the write gate is honoured; keyLocation is always sent.
No network: pages, liveness and the POST are injected."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import indexnow_auto as ia  # noqa: E402
from channels import write_gate as wg  # noqa: E402


class TestIndexNowAuto(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        self.state, self.ledger = d / "state.json", d / "ledger.jsonl"
        self.sent = []

    def run_ia(self, pages, live=lambda u: True, status=202, today="2026-10-24", **kw):
        def post(urls):
            self.sent.append(list(urls))
            return status
        return ia.run(pages=pages, live=live, post=post, today=today, state_path=self.state, ledger_path=self.ledger, **kw)

    def test_first_run_sends_every_live_page_and_records_receipt(self):
        r = self.run_ia({"customer_site/a.html": "b1", "customer_site/b.html": "b2"})
        self.assertEqual(r["action"], "submitted")
        self.assertEqual(sorted(self.sent[0]), [ia.BASE + "customer_site/a.html", ia.BASE + "customer_site/b.html"])
        rec = json.loads(self.ledger.read_text().splitlines()[-1])
        self.assertEqual(rec["http_status"], 202)
        self.assertEqual(rec["key_location"], ia.KEY_LOCATION)

    def test_only_changed_pages_are_sent_and_once_per_day(self):
        self.run_ia({"customer_site/a.html": "b1", "customer_site/b.html": "b2"})
        self.assertEqual(self.run_ia({"customer_site/a.html": "b1x", "customer_site/b.html": "b2"})["action"], "none")
        r = self.run_ia({"customer_site/a.html": "b1x", "customer_site/b.html": "b2"}, today="2026-10-25")
        self.assertEqual(self.sent[-1], [ia.BASE + "customer_site/a.html"])
        self.assertEqual(r["action"], "submitted")

    def test_pages_not_live_yet_are_retried_later_the_same_day(self):
        r = self.run_ia({"customer_site/a.html": "b1", "customer_site/b.html": "b2"}, live=lambda u: u.endswith("a.html"))
        self.assertIn("1 not live yet", r["detail"])
        self.run_ia({"customer_site/a.html": "b1", "customer_site/b.html": "b2"})
        self.assertEqual(self.sent[-1], [ia.BASE + "customer_site/b.html"])

    def test_rejected_submission_is_a_failure_and_not_marked_sent(self):
        r = self.run_ia({"customer_site/a.html": "b1"}, status=403)
        self.assertEqual(r["action"], "failed")
        self.run_ia({"customer_site/a.html": "b1"})
        self.assertEqual(len(self.sent), 2, "resent after the failure")

    def test_dry_run_sends_nothing(self):
        r = self.run_ia({"customer_site/a.html": "b1"}, dry_run=True)
        self.assertEqual(r["action"], "dry_run")
        self.assertEqual(self.sent, [])
        self.assertFalse(self.state.exists())

    def test_sitemap_paths_keeps_only_this_site_pages(self):
        text = ("<urlset>"
                "<url><loc>%scustomer_site/a.html</loc></url>"
                "<url><loc>%spublic_site/b.html</loc></url>"
                "<url><loc>https://example.test/other.html</loc></url>"
                "<url><loc>%scustomer_site/c.png</loc></url>"
                "</urlset>" % (ia.BASE, ia.BASE, ia.BASE))
        self.assertEqual(ia.sitemap_paths(text),
                         {"customer_site/a.html", "public_site/b.html"})

    def test_every_advertised_page_is_announced(self):
        # public_site/market-validation.html sat in the sitemap for weeks while
        # published_pages() only walked customer_site/, so it was never sent.
        advertised = ia.sitemap_paths(
            (ROOT / "sitemap.xml").read_text(encoding="utf-8"))
        announced = ia.published_pages("HEAD")
        self.assertEqual(sorted(advertised - set(announced)), [])

    def test_real_submit_is_refused_without_authorization(self):
        env = {"FACTORY_LIVE_PUBLISH": "", wg.SEARCH_PING_ENV: ""}
        with patch.dict(os.environ, env), patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            with self.assertRaises(wg.WriteNotAuthorized):
                ia.submit([ia.BASE + "customer_site/a.html"])


if __name__ == "__main__":
    unittest.main()
