"""scripts/auto_publish_site.py review rules: only site pages are ever pushed
automatically; product files, ignored paths and code changes are refused."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import auto_publish_site as aps  # noqa: E402

never_ignored = lambda p: False  # noqa: E731


class TestReviewRange(unittest.TestCase):
    def test_site_only_range_is_allowed(self):
        ok, _ = aps.review_range([("a" * 40, [("M", "customer_site/index.html"), ("A", "customer_site/guide-x.html")]),
                                  ("b" * 40, [("M", "sitemap.xml"), ("D", "customer_site/old.html")])], never_ignored)
        self.assertTrue(ok)

    def test_any_code_change_holds_the_whole_range(self):
        ok, why = aps.review_range([("a" * 40, [("M", "customer_site/index.html")]),
                                    ("b" * 40, [("M", "server.js")])], never_ignored)
        self.assertFalse(ok)
        self.assertIn("server.js", why)

    def test_product_file_is_refused_even_inside_the_site(self):
        ok, why = aps.review_range([("a" * 40, [("A", "customer_site/downloads/kit.pdf")])], never_ignored)
        self.assertFalse(ok)
        self.assertIn("product-like", why)

    def test_ignored_path_is_refused(self):
        ok, why = aps.review_range([("a" * 40, [("A", "customer_site/private.html")])], lambda p: p.endswith("private.html"))
        self.assertFalse(ok)
        self.assertIn(".gitignore", why)

    def test_env_and_data_paths_are_not_site_pages(self):
        for path in (".env", "data/founder_approvals.jsonl", "customer_siteX/a.html"):
            self.assertFalse(aps.review_range([("a" * 40, [("A", path)])], never_ignored)[0], path)


if __name__ == "__main__":
    unittest.main()


class TestNetworkOutages(unittest.TestCase):
    """2026-10-29: network failures are 'deferred', recorded once per outage window."""

    def setUp(self):
        import tempfile
        self.d = Path(tempfile.mkdtemp())
        self.outages = self.d / "outages.jsonl"
        self.state = {}

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d, ignore_errors=True)

    def call(self, run_fn, now):
        return aps.classify_and_record(run_fn, outages=self.outages, now=now,
                                       state_reader=lambda: dict(self.state),
                                       state_writer=lambda s: self.state.update(s) or self.state.clear() or self.state.update(s))

    def events(self):
        import json
        return [json.loads(l) for l in self.outages.read_text(encoding="utf-8").splitlines()] if self.outages.exists() else []

    def test_network_error_is_deferred_and_window_recorded_once(self):
        def down(dry_run=False):
            raise RuntimeError("git fetch -q failed: fatal: unable to access 'https://github.com/x': Could not resolve host: github.com")
        r1 = self.call(down, "2026-10-29T05:00:00+00:00")
        r2 = self.call(down, "2026-10-29T05:10:00+00:00")
        self.assertEqual(("deferred", "network", "opened"), (r1["action"], r1["reason"], r1["outage"]))
        self.assertEqual("deferred", r2["action"])
        self.assertNotIn("outage", r2)
        r3 = self.call(lambda dry_run=False: {"action": "none", "detail": "nothing to publish"}, "2026-10-29T06:30:00+00:00")
        self.assertEqual(90.0, r3["outage_closed_minutes"])
        ev = self.events()
        self.assertEqual(["github_unreachable", "github_reachable_again"], [e["event"] for e in ev])
        self.assertNotIn("outage_open_since", self.state)

    def test_other_errors_are_still_failures(self):
        def broken(dry_run=False):
            raise RuntimeError("git rev-parse failed: fatal: bad revision")
        r = self.call(broken, "2026-10-29T05:00:00+00:00")
        self.assertEqual("failed", r["action"])
        self.assertEqual([], self.events())

    def test_detection(self):
        self.assertTrue(aps.is_network_error("Failed to connect to github.com port 443 after 21149 ms"))
        self.assertFalse(aps.is_network_error("CI failed for the last automatic push"))
