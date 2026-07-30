"""Tests for affiliate_commerce/ (ADR-149, 2026-07-30): the founder's
explicit Golden Rule override, the smallest real slice -- one network
(Amazon Associates), one category (standing desk converters), real click
tracking only (never conversion -- that needs Amazon's real postback).

    python -m unittest tests.test_affiliate_commerce -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate_commerce import networks, click_tracking, products


class TestNetworks(unittest.TestCase):
    def test_no_tag_configured_by_default_honest_not_fabricated(self):
        # Real check against whatever the actual environment has -- never
        # assumes a tag exists. Isolate from a real AMAZON_ASSOCIATE_TAG
        # if this environment happens to have one set.
        old = os.environ.pop(networks.AMAZON_ASSOCIATE_TAG_ENV, None)
        try:
            self.assertFalse(networks.amazon_associate_tag_configured())
            status = networks.network_status()
            self.assertEqual(status["network"], "amazon_associates")
            self.assertFalse(status["tag_configured"])
            self.assertIsNotNone(status["reason"])
        finally:
            if old is not None:
                os.environ[networks.AMAZON_ASSOCIATE_TAG_ENV] = old

    def test_build_amazon_url_omits_tag_when_not_configured(self):
        url = networks.build_amazon_url("B07LCCJD6B", tag=None)
        self.assertEqual(url, "https://www.amazon.com/dp/B07LCCJD6B")

    def test_build_amazon_url_appends_real_tag_when_given(self):
        url = networks.build_amazon_url("B07LCCJD6B", tag="galaxyforge-20")
        self.assertEqual(url, "https://www.amazon.com/dp/B07LCCJD6B?tag=galaxyforge-20")

    def test_build_amazon_url_reads_env_tag_when_none_passed(self):
        old = os.environ.get(networks.AMAZON_ASSOCIATE_TAG_ENV)
        os.environ[networks.AMAZON_ASSOCIATE_TAG_ENV] = "envtag-20"
        try:
            url = networks.build_amazon_url("B07LCCJD6B")
            self.assertEqual(url, "https://www.amazon.com/dp/B07LCCJD6B?tag=envtag-20")
            self.assertTrue(networks.amazon_associate_tag_configured())
        finally:
            if old is None:
                del os.environ[networks.AMAZON_ASSOCIATE_TAG_ENV]
            else:
                os.environ[networks.AMAZON_ASSOCIATE_TAG_ENV] = old


class TestClickTracking(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ledger_path = Path(self._tmp.name) / "test_affiliate_clicks.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_never_touches_the_real_production_ledger(self):
        # Every call in this test class passes an explicit ledger_path --
        # confirms the real data/affiliate_clicks.jsonl stays untouched
        # by test runs (the exact discipline this session already
        # enforces everywhere else with a real ledger).
        self.assertFalse(self.ledger_path.exists())
        click_tracking.record_click("B07LCCJD6B", referrer="test", ledger_path=self.ledger_path)
        self.assertTrue(self.ledger_path.exists())
        self.assertFalse(click_tracking.DEFAULT_LEDGER_PATH.exists() and
                          click_tracking.DEFAULT_LEDGER_PATH == self.ledger_path)

    def test_record_and_read_round_trip(self):
        click_tracking.record_click("B07LCCJD6B", referrer="https://example.com", ledger_path=self.ledger_path)
        click_tracking.record_click("B0864RSM5S", referrer=None, ledger_path=self.ledger_path)
        entries = click_tracking.read_clicks(ledger_path=self.ledger_path)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["product_id"], "B07LCCJD6B")
        self.assertIn("timestamp", entries[0])

    def test_read_clicks_on_missing_file_returns_empty_never_errors(self):
        missing = Path(self._tmp.name) / "does_not_exist.jsonl"
        self.assertEqual(click_tracking.read_clicks(ledger_path=missing), [])

    def test_click_summary_counts_are_real_never_a_fabricated_conversion_rate(self):
        click_tracking.record_click("B07LCCJD6B", ledger_path=self.ledger_path)
        click_tracking.record_click("B07LCCJD6B", ledger_path=self.ledger_path)
        click_tracking.record_click("B0864RSM5S", ledger_path=self.ledger_path)
        summary = click_tracking.click_summary(ledger_path=self.ledger_path)
        self.assertEqual(summary["total_real_clicks"], 3)
        self.assertEqual(summary["clicks_by_product"]["B07LCCJD6B"], 2)
        self.assertEqual(summary["clicks_by_product"]["B0864RSM5S"], 1)
        self.assertNotIn("conversion_rate", summary)
        self.assertNotIn("revenue", summary)


class TestProducts(unittest.TestCase):
    def test_lists_only_the_one_real_directive_named_category(self):
        result = products.list_products()
        self.assertEqual(result["category"], "standing_desk_converters")
        self.assertEqual(result["count"], 4)
        self.assertTrue(result["source"])
        self.assertEqual(result["verified_at"], "2026-07-30")

    def test_every_product_has_a_real_asin_price_and_rating(self):
        result = products.list_products()
        for p in result["products"]:
            self.assertTrue(p["asin"])
            self.assertGreater(p["price_usd"], 0)
            self.assertGreater(p["rating"], 0)
            self.assertGreater(p["rating_count"], 0)

    def test_ranking_is_by_weighted_rating_not_input_order(self):
        result = products.list_products()
        ids_in_rank_order = [p["id"] for p in result["products"]]
        # FITUEYES 36" (2547 ratings @ 4.6) should outrank the Aconcept
        # budget pick (62 ratings @ 4.1) under the disclosed weighted
        # formula, even though Aconcept is listed last in PRODUCTS.
        self.assertLess(ids_in_rank_order.index("B07LCCT6VS"), ids_in_rank_order.index("B0D1C9LBN5"))

    def test_unknown_category_returns_empty_not_an_error(self):
        result = products.list_products(category="nonexistent_category")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["products"], [])

    def test_get_product_returns_none_for_unknown_id_never_fabricates(self):
        self.assertIsNone(products.get_product("NOT-A-REAL-ASIN"))

    def test_get_product_returns_the_real_matching_product(self):
        p = products.get_product("B07LCCJD6B")
        self.assertIsNotNone(p)
        self.assertEqual(p["asin"], "B07LCCJD6B")


if __name__ == "__main__":
    unittest.main()
