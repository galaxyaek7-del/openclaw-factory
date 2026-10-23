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
