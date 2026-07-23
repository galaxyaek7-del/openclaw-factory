"""Tests for market_memory.py (Global Market Learning Engine, 2026-07-23):
the real, honest 17-dimension commercial event schema, aggregation,
monthly evolution report, and evidence-gated recommendations.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_market_memory -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import market_evidence
import market_memory


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestSeasonAndCustomerIdExtraction(unittest.TestCase):
    def test_derives_correct_season_from_month(self):
        self.assertEqual(market_memory._derive_season("2026-01-15T00:00:00+00:00"), "winter")
        self.assertEqual(market_memory._derive_season("2026-07-15T00:00:00+00:00"), "summer")
        self.assertEqual(market_memory._derive_season("2026-04-15T00:00:00+00:00"), "spring")
        self.assertEqual(market_memory._derive_season("2026-10-15T00:00:00+00:00"), "autumn")

    def test_missing_or_malformed_timestamp_is_honest_none_never_a_guess(self):
        self.assertIsNone(market_memory._derive_season(None))
        self.assertIsNone(market_memory._derive_season("not-a-real-timestamp"))

    def test_gumroad_customer_id_is_real_email_field(self):
        self.assertEqual(market_memory._extract_customer_identifier({"email": "a@b.com"}, "gumroad"), "a@b.com")

    def test_paddle_customer_id_is_real_customer_id_field(self):
        self.assertEqual(market_memory._extract_customer_identifier({"customer_id": "ctm_123"}, "paddle"), "ctm_123")

    def test_unknown_platform_or_missing_field_is_honest_none(self):
        self.assertIsNone(market_memory._extract_customer_identifier({"email": "a@b.com"}, "etsy"))
        self.assertIsNone(market_memory._extract_customer_identifier({}, "gumroad"))


class TestComputeProfit(unittest.TestCase):
    def test_gumroad_profit_uses_real_fee_math(self):
        profit, reason = market_memory._compute_profit(29.0, "gumroad")
        self.assertIsNone(reason)
        self.assertIsInstance(profit, float)

    def test_paddle_profit_is_honest_none_no_real_fee_model_configured(self):
        """The real gap this session found: economics.py has no 'paddle'
        entry, so profit must be honestly None + a stated reason, never a
        fabricated fee percentage."""
        profit, reason = market_memory._compute_profit(388.0, "paddle")
        self.assertIsNone(profit)
        self.assertIn("paddle", reason)

    def test_no_price_is_honest_none(self):
        profit, reason = market_memory._compute_profit(None, "gumroad")
        self.assertIsNone(profit)
        self.assertIn("لا سعر", reason)


class TestBuildCommercialEvent(unittest.TestCase):
    def setUp(self):
        self.sales_ledger_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.sales_ledger_path):
            os.remove(self.sales_ledger_path)

    def test_real_fields_are_populated_honest_gaps_marked(self):
        # In the real flow (decision_engine/feedback.py::sync_outcomes()),
        # the sale is already appended to the ledger by
        # channels/ledger.py::record_sale() before build_commercial_event()
        # is ever called -- so the ledger must already contain this sale.
        from channels import ledger as sales_ledger
        sales_ledger.append_event(
            {"event_type": "sale", "platform": "gumroad", "raw": {"price": "29.00", "email": "a@b.com"}},
            ledger_path=self.sales_ledger_path,
        )
        event = market_memory.build_commercial_event(
            "gratitude journal", "book", "gumroad", {"price": "29.00", "email": "a@b.com"},
            "2026-07-23T00:00:00+00:00", sales_ledger_path=self.sales_ledger_path,
        )
        self.assertEqual(event["product"], "gratitude journal")
        self.assertEqual(event["product_family"], "book")
        self.assertEqual(event["platform"], "gumroad")
        self.assertEqual(event["selling_price"], 29.0)
        self.assertEqual(event["season"], "summer")
        self.assertIsInstance(event["profit"], float)
        self.assertEqual(event["purchase_frequency"], 1)  # this sale itself, first time seen

        # Fields with no real source in this factory must be an honest
        # {value: None, reason: ...} dict, never a bare guessed value.
        for field in ("bundle", "customer_country", "customer_language", "traffic_source",
                      "acquisition_channel", "device", "conversion", "refund", "customer_feedback"):
            self.assertIsNone(event[field]["value"])
            self.assertTrue(event[field]["reason"])

    def test_purchase_frequency_counts_real_repeat_customer(self):
        from channels import ledger as sales_ledger
        # First real purchase, already in the ledger from a prior tick.
        sales_ledger.append_event(
            {"event_type": "sale", "platform": "gumroad", "raw": {"price": "10.00", "email": "repeat@b.com"}},
            ledger_path=self.sales_ledger_path,
        )
        # Second real purchase by the same customer -- also already in
        # the ledger by the time build_commercial_event() runs.
        sales_ledger.append_event(
            {"event_type": "sale", "platform": "gumroad", "raw": {"price": "10.00", "email": "repeat@b.com"}},
            ledger_path=self.sales_ledger_path,
        )
        event = market_memory.build_commercial_event(
            "niche", None, "gumroad", {"price": "10.00", "email": "repeat@b.com"},
            "2026-07-23T00:00:00+00:00", sales_ledger_path=self.sales_ledger_path,
        )
        self.assertEqual(event["purchase_frequency"], 2)

    def test_no_customer_id_leaves_purchase_frequency_honestly_none(self):
        event = market_memory.build_commercial_event(
            "niche", None, "paddle", {}, "2026-07-23T00:00:00+00:00", sales_ledger_path=self.sales_ledger_path,
        )
        self.assertIsNone(event["purchase_frequency"])


class TestNicheCommercialProfile(unittest.TestCase):
    def setUp(self):
        self.evidence_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.evidence_path):
            os.remove(self.evidence_path)

    def test_no_real_events_is_honestly_empty(self):
        profile = market_memory.niche_commercial_profile("nothing sold", evidence_path=self.evidence_path)
        self.assertEqual(profile["sample_size"], 0)
        self.assertIn("reason", profile)

    def test_real_events_are_aggregated(self):
        market_evidence.record_evidence("test niche", "closed_sale", {
            "commercial_event": {"platform": "gumroad", "selling_price": 20.0, "season": "summer"},
        }, evidence_path=self.evidence_path)
        market_evidence.record_evidence("test niche", "closed_sale", {
            "commercial_event": {"platform": "paddle", "selling_price": 100.0, "season": "winter"},
        }, evidence_path=self.evidence_path)

        profile = market_memory.niche_commercial_profile("test niche", evidence_path=self.evidence_path)
        self.assertEqual(profile["sample_size"], 2)
        self.assertEqual(profile["total_revenue"], 120.0)
        self.assertEqual(profile["average_price"], 60.0)
        self.assertEqual(profile["platforms"], ["gumroad", "paddle"])

    def test_bare_closed_sale_events_with_no_commercial_event_are_ignored(self):
        market_evidence.record_evidence("test niche", "closed_sale", {"platform": "gumroad"}, evidence_path=self.evidence_path)
        profile = market_memory.niche_commercial_profile("test niche", evidence_path=self.evidence_path)
        self.assertEqual(profile["sample_size"], 0)


class TestMonthlyEvolutionReportAndRecommendations(unittest.TestCase):
    def setUp(self):
        self.evidence_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.evidence_path):
            os.remove(self.evidence_path)

    def _record(self, niche, platform, price, profit=None):
        market_evidence.record_evidence(niche, "closed_sale", {
            "commercial_event": {"platform": platform, "selling_price": price, "profit": profit, "season": "summer"},
        }, evidence_path=self.evidence_path)

    def test_below_min_samples_reports_discovery_never_a_fabricated_trend(self):
        self._record("n1", "gumroad", 10.0, 5.0)
        report = market_memory.monthly_evolution_report(evidence_path=self.evidence_path)
        self.assertEqual(report["maturity"], "DISCOVERY")
        self.assertEqual(report["sample_size"], 1)

    def test_enough_real_samples_computes_real_ranking(self):
        for i in range(market_memory.MIN_SAMPLES):
            self._record("winning niche", "gumroad", 10.0, 5.0)
        report = market_memory.monthly_evolution_report(evidence_path=self.evidence_path)
        self.assertEqual(report["maturity"], "REAL")
        self.assertEqual(report["top_growing_niches"][0]["niche"], "winning niche")
        self.assertEqual(report["top_growing_niches"][0]["revenue"], 30.0)
        # Sections with no real data source in this factory stay honest.
        self.assertIsNone(report["highest_ltv_customers"]["value"])
        self.assertIsNone(report["highest_roi_countries"]["value"])

    def test_recommendations_empty_below_min_samples(self):
        self._record("n1", "gumroad", 10.0, 5.0)
        result = market_memory.recommend_actions(evidence_path=self.evidence_path)
        self.assertEqual(result["maturity"], "DISCOVERY")
        self.assertEqual(result["recommendations"], [])

    def test_recommends_increasing_investment_only_with_real_positive_profit_evidence(self):
        for i in range(market_memory.MIN_SAMPLES):
            self._record("profitable niche", "gumroad", 10.0, 5.0)
        result = market_memory.recommend_actions(evidence_path=self.evidence_path)
        self.assertEqual(result["maturity"], "REAL")
        types = [r["type"] for r in result["recommendations"]]
        self.assertIn("increase_investment", types)

    def test_no_fee_model_niche_gets_review_pricing_not_a_guessed_profit_verdict(self):
        for i in range(market_memory.MIN_SAMPLES):
            self._record("paddle-only niche", "paddle", 100.0, None)
        result = market_memory.recommend_actions(evidence_path=self.evidence_path)
        types = [r["type"] for r in result["recommendations"]]
        self.assertIn("review_pricing_model", types)
        self.assertNotIn("increase_investment", types)


if __name__ == "__main__":
    unittest.main()
