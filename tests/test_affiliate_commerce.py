"""Tests for affiliate_commerce/ (ADR-149, 2026-07-30): the founder's
explicit Golden Rule override, the smallest real slice -- one network
(Amazon Associates), one category (standing desk converters), real click
tracking only (never conversion -- that needs Amazon's real postback).

    python -m unittest tests.test_affiliate_commerce -v
"""

import os
import random
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate_commerce import networks, click_tracking, products, simulation


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


class TestPageViewTracking(unittest.TestCase):
    """Revenue Activation Directive (ADR-239), Section F -- the
    real 'traffic -> page' step of the conversion funnel."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pv_path = Path(self._tmp.name) / "test_page_views.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_never_touches_the_real_production_ledger(self):
        self.assertFalse(self.pv_path.exists())
        click_tracking.record_page_view("standing_desk_page", referrer="google", ledger_path=self.pv_path)
        self.assertTrue(self.pv_path.exists())
        self.assertFalse(click_tracking.DEFAULT_PAGE_VIEW_LEDGER_PATH.exists() and
                          click_tracking.DEFAULT_PAGE_VIEW_LEDGER_PATH == self.pv_path)

    def test_record_and_read_round_trip(self):
        click_tracking.record_page_view("standing_desk_page", referrer="https://google.com", ledger_path=self.pv_path)
        click_tracking.record_page_view("standing_desk_page", referrer=None, ledger_path=self.pv_path)
        entries = click_tracking.read_page_views(ledger_path=self.pv_path)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["page_id"], "standing_desk_page")
        self.assertIn("timestamp", entries[0])

    def test_read_page_views_on_missing_file_returns_empty_never_errors(self):
        missing = Path(self._tmp.name) / "does_not_exist.jsonl"
        self.assertEqual(click_tracking.read_page_views(ledger_path=missing), [])


class TestConversionFunnelSummary(unittest.TestCase):
    """Revenue Activation Directive (ADR-239), Section F."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pv_path = Path(self._tmp.name) / "pv.jsonl"
        self.click_path = Path(self._tmp.name) / "clicks.jsonl"
        self.ledger_path = Path(self._tmp.name) / "commission_ledger.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_all_stages_honestly_zero_with_no_real_activity(self):
        summary = click_tracking.conversion_funnel_summary(
            page_views_path=self.pv_path, clicks_path=self.click_path, commission_ledger_path=self.ledger_path)
        self.assertEqual(summary["TRAFFIC_PAGE_VIEWS"], 0)
        self.assertEqual(summary["OUTBOUND_CLICKS"], 0)
        self.assertEqual(summary["REAL_COMMISSIONS"], 0)
        self.assertIn("N/A", summary["page_view_to_click_rate"])

    def test_real_counts_and_rates_computed_correctly(self):
        click_tracking.record_page_view("p", ledger_path=self.pv_path)
        click_tracking.record_page_view("p", ledger_path=self.pv_path)
        click_tracking.record_click("prod1", ledger_path=self.click_path)
        summary = click_tracking.conversion_funnel_summary(
            page_views_path=self.pv_path, clicks_path=self.click_path, commission_ledger_path=self.ledger_path)
        self.assertEqual(summary["TRAFFIC_PAGE_VIEWS"], 2)
        self.assertEqual(summary["OUTBOUND_CLICKS"], 1)
        self.assertEqual(summary["page_view_to_click_rate"], 0.5)

    def test_never_fabricates_a_commission_from_clicks_alone(self):
        click_tracking.record_click("prod1", ledger_path=self.click_path)
        click_tracking.record_click("prod1", ledger_path=self.click_path)
        summary = click_tracking.conversion_funnel_summary(
            page_views_path=self.pv_path, clicks_path=self.click_path, commission_ledger_path=self.ledger_path)
        self.assertEqual(summary["REAL_COMMISSIONS"], 0)
        self.assertEqual(summary["click_to_commission_rate"], 0.0)


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


class TestSimulation(unittest.TestCase):
    """ADR-153, 2026-07-30: every simulated event must be explicitly
    labeled and written to its own separate ledger -- never the real
    click ledger, never a real financial ledger."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.click_path = Path(self._tmp.name) / "clicks.jsonl"
        self.sim_path = Path(self._tmp.name) / "sim.jsonl"
        self._old_mode = os.environ.get("AFFILIATE_MODE")

    def tearDown(self):
        self._tmp.cleanup()
        if self._old_mode is None:
            os.environ.pop("AFFILIATE_MODE", None)
        else:
            os.environ["AFFILIATE_MODE"] = self._old_mode

    def test_blocked_outside_simulation_mode(self):
        os.environ["AFFILIATE_MODE"] = "production"
        with self.assertRaises(RuntimeError):
            simulation.simulate_conversion("B07LCCJD6B", sim_ledger_path=self.sim_path)

    def test_simulate_conversion_tags_event_and_writes_to_separate_ledger(self):
        record = simulation.simulate_conversion("B07LCCJD6B", sim_ledger_path=self.sim_path)
        self.assertTrue(record["simulation"])
        self.assertEqual(record["product_id"], "B07LCCJD6B")
        self.assertTrue(self.sim_path.exists())
        self.assertFalse(self.click_path.exists())

    def test_simulate_conversion_unknown_product_returns_none(self):
        self.assertIsNone(simulation.simulate_conversion("NOT-A-REAL-ASIN", sim_ledger_path=self.sim_path))

    def test_run_simulation_cycle_draws_from_real_click_ledger(self):
        for _ in range(300):
            click_tracking.record_click("B0864RSM5S", ledger_path=self.click_path)
        generated = simulation.run_simulation_cycle(
            rng=random.Random(3), click_ledger_path=self.click_path, sim_ledger_path=self.sim_path,
        )
        self.assertGreater(len(generated), 0)
        for record in generated:
            self.assertTrue(record["simulation"])

    def test_run_simulation_cycle_with_no_real_clicks_generates_nothing(self):
        generated = simulation.run_simulation_cycle(
            rng=random.Random(1), click_ledger_path=self.click_path, sim_ledger_path=self.sim_path,
        )
        self.assertEqual(generated, [])

    def test_funnel_report_is_explicitly_labeled_simulated(self):
        report = simulation.simulation_funnel_report(click_ledger_path=self.click_path, sim_ledger_path=self.sim_path)
        self.assertIn("SIMULATED", report["label"])
        self.assertEqual(report["mode"], "simulation")

    def test_funnel_report_never_touches_real_default_ledgers(self):
        simulation.simulation_funnel_report(click_ledger_path=self.click_path, sim_ledger_path=self.sim_path)
        self.assertFalse(click_tracking.DEFAULT_LEDGER_PATH.exists() and
                          click_tracking.DEFAULT_LEDGER_PATH == self.click_path)
        self.assertFalse(simulation.DEFAULT_SIM_LEDGER_PATH.exists() and
                          simulation.DEFAULT_SIM_LEDGER_PATH == self.sim_path)


if __name__ == "__main__":
    unittest.main()
