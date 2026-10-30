"""A listing a buyer can pay for and receive nothing from is a defect, not a stat.

2026-10-30: two published, priced Gumroad listings had an empty `file_info` and
no `custom_delivery_url` (/l/svlky $8.00, /l/ieashv $11.99). The first audit
pass reported all 109 listings as fileless, which was the audit's bug: Gumroad
returns `file_info` with capitalised keys, so a `name`/`size` lookup matched
nothing. That false positive is pinned here too, because an audit that cannot
read the real field would either hide the two genuine defects among 109 false
ones or, worse, be "fixed" by loosening the rule until it never fires.

The rule this file locks: published + priced + no file + no delivery URL means
the storefront must not advertise it.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

import deliverability


class TestDelivers(unittest.TestCase):
    def test_capitalised_file_info_is_a_real_file(self):
        # The exact shape Gumroad returns: {"Size": "17.6 KB"}.
        self.assertTrue(deliverability.delivers({"file_info": {"Size": "17.6 KB"}}))

    def test_lowercase_file_info_is_a_real_file(self):
        self.assertTrue(deliverability.delivers({"file_info": {"size": 1024}}))

    def test_empty_file_info_delivers_nothing(self):
        self.assertFalse(deliverability.delivers({"file_info": {}}))

    def test_missing_file_info_delivers_nothing(self):
        self.assertFalse(deliverability.delivers({"file_info": None}))
        self.assertFalse(deliverability.delivers({}))

    def test_a_delivery_url_is_a_deliverable(self):
        self.assertTrue(deliverability.delivers(
            {"file_info": {}, "custom_delivery_url": "https://example.test/x.zip"}))

    def test_a_non_dict_file_info_is_not_trusted(self):
        self.assertFalse(deliverability.delivers({"file_info": "17.6 KB"}))


class TestAudit(unittest.TestCase):
    def test_reports_only_published_undeliverable_listings(self):
        products = [
            {"name": "Has File", "published": True, "price": 900,
             "short_url": "https://aekraft.gumroad.com/l/hasfile",
             "file_info": {"Size": "1 KB"}},
            {"name": "Empty", "published": True, "price": 1199,
             "short_url": "https://aekraft.gumroad.com/l/empty", "file_info": {}},
            {"name": "Unpublished", "published": False, "price": 500,
             "short_url": "https://aekraft.gumroad.com/l/draft", "file_info": {}},
            {"name": "Deleted", "published": True, "deleted": True, "price": 500,
             "short_url": "https://aekraft.gumroad.com/l/gone", "file_info": {}},
        ]
        found = deliverability.audit_products(products)
        self.assertEqual([e["slug"] for e in found], ["empty"])
        self.assertEqual(found[0]["price_cents"], 1199)

    def test_export_round_trips_through_the_generated_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "undeliverable.json")
            deliverability.export_undeliverable([
                {"name": "Empty", "published": True, "price": 800,
                 "short_url": "https://aekraft.gumroad.com/l/svlky", "file_info": {}},
            ], path)
            self.assertEqual(deliverability.undeliverable_slugs(path), ("svlky",))
            doc = json.load(open(path, encoding="utf-8"))
            self.assertIn("generated_by", doc)
            self.assertNotIn("slug", doc["products"]["svlky"])

    def test_absent_file_means_nothing_is_excluded(self):
        self.assertEqual(deliverability.undeliverable_slugs("/nonexistent/x.json"), ())

    def test_committed_copy_lists_the_two_priced_defects(self):
        # iaiyt and owtmpe are in the copy too, but they are already excluded
        # for their own reasons (hold policy, seller-labelled unsellable); these
        # two are the ones nothing else was catching.
        doc = json.load(open(deliverability.EXPORT_PATH, encoding="utf-8"))
        products = doc["products"]
        self.assertIn("svlky", products)
        self.assertIn("ieashv", products)
        self.assertEqual(products["svlky"]["price_cents"], 800)
        self.assertEqual(products["ieashv"]["price_cents"], 1199)
        for slug, entry in products.items():
            self.assertRegex(slug, r"^[a-z0-9]+$")
            self.assertIn("title", entry)
            self.assertIn("price_cents", entry)


if __name__ == "__main__":
    unittest.main()
