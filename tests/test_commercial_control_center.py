"""Tests for commercial_control_center.py (ADR-202, 2026-08-07).

    python -m unittest tests.test_commercial_control_center -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import commercial_control_center as ccc


def _write_finance(tmp, sales, extra=None):
    path = os.path.join(tmp, "finance_data.json")
    data = {
        "sales": sales, "totalKDP": 0, "totalEtsy": 0, "totalGumroad": 0, "totalPaddle": 0,
        "totalSales": 0, "byLadder": {}, "lastUpdated": None,
    }
    if extra:
        data.update(extra)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


class TestRevenueSnapshotFiltering(unittest.TestCase):
    def test_test_smoke_record_never_counts_as_real_revenue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [
                {"id": 1, "platform": "Paddle", "amount": 150, "product": "contract-test-ladder-DELETE-ME", "date": "2026-07-24", "ladder": "ai_saas"},
            ])
            snap = ccc.revenue_snapshot(finance_path=path)
            self.assertEqual(snap["ACTUAL"]["total_revenue_usd"], 0)

    def test_by_platform_never_leaks_the_filtered_test_record(self):
        """Regression test for a real bug caught while building this
        module: revenue_by_platform used to read finance_data.json's own
        pre-aggregated totalPaddle field directly, which still included
        the filtered DELETE-ME test record even though total_revenue_usd
        correctly excluded it."""
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [
                {"id": 1, "platform": "Paddle", "amount": 150, "product": "contract-test-ladder-DELETE-ME", "date": "2026-07-24", "ladder": "ai_saas"},
            ], extra={"totalPaddle": 150, "byLadder": {"ai_saas": 150}})
            snap = ccc.revenue_snapshot(finance_path=path)
            self.assertEqual(snap["ACTUAL"]["revenue_by_platform"]["Paddle"], 0)
            self.assertEqual(snap["ACTUAL"]["subscription_revenue_usd"], 0)
            self.assertEqual(snap["ACTUAL"]["enterprise_revenue_usd"], 0)

    def test_real_sale_counts_correctly_by_platform_and_product(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [
                {"id": 1, "platform": "Paddle", "amount": 155, "product": "EU AI Act Toolkit", "date": "2026-08-07", "ladder": "b2b_systems"},
                {"id": 2, "platform": "Gumroad", "amount": 20, "product": "Journal", "date": "2026-08-06"},
            ])
            snap = ccc.revenue_snapshot(finance_path=path)
            a = snap["ACTUAL"]
            self.assertEqual(a["total_revenue_usd"], 175)
            self.assertEqual(a["revenue_by_platform"]["Paddle"], 155)
            self.assertEqual(a["revenue_by_platform"]["Gumroad"], 20)
            self.assertEqual(a["revenue_by_product"]["EU AI Act Toolkit"], 155)
            self.assertEqual(a["enterprise_revenue_usd"], 155)

    def test_revenue_today_only_counts_todays_date(self):
        import datetime
        now = datetime.datetime(2026, 8, 7, tzinfo=datetime.timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [
                {"id": 1, "platform": "Paddle", "amount": 100, "product": "X", "date": "2026-08-07"},
                {"id": 2, "platform": "Paddle", "amount": 50, "product": "Y", "date": "2026-08-01"},
            ])
            snap = ccc.revenue_snapshot(now=now, finance_path=path)
            self.assertEqual(snap["ACTUAL"]["revenue_today_usd"], 100)
            self.assertEqual(snap["ACTUAL"]["total_revenue_usd"], 150)


class TestHonestTiers(unittest.TestCase):
    def test_mrr_arr_are_honestly_zero_not_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [])
            snap = ccc.revenue_snapshot(finance_path=path)
            self.assertEqual(snap["ACTUAL"]["mrr_usd"], 0)
            self.assertEqual(snap["ACTUAL"]["arr_usd"], 0)

    def test_revenue_by_country_is_honestly_unknown_never_fabricated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [])
            snap = ccc.revenue_snapshot(finance_path=path)
            self.assertEqual(snap["ACTUAL"]["revenue_by_country"]["status"], "UNKNOWN")

    def test_projected_tier_is_honestly_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [])
            snap = ccc.revenue_snapshot(finance_path=path)
            self.assertEqual(snap["PROJECTED"]["status"], "NOT_AVAILABLE")

    def test_estimated_tier_is_a_real_simulation_never_actual_revenue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [])
            snap = ccc.revenue_snapshot(finance_path=path)
            self.assertIn("SIMULATION MODE", snap["ESTIMATED"].get("note", ""))


class TestGlobalCommercialScore(unittest.TestCase):
    def test_overall_excludes_uncomputed_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [])
            result = ccc.global_commercial_score(finance_path=path)
            scored = [d["score"] for d in result["dimensions"].values() if isinstance(d.get("score"), (int, float))]
            if scored:
                self.assertAlmostEqual(result["overall"], round(sum(scored) / len(scored), 1))
            else:
                self.assertIsNone(result["overall"])

    def test_every_dimension_has_a_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [])
            result = ccc.global_commercial_score(finance_path=path)
            for name, d in result["dimensions"].items():
                self.assertIn("source", d, name)

    def test_no_score_is_fabricated_above_100_or_below_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [])
            result = ccc.global_commercial_score(finance_path=path)
            for name, d in result["dimensions"].items():
                if isinstance(d.get("score"), (int, float)):
                    self.assertGreaterEqual(d["score"], 0.0, name)
                    self.assertLessEqual(d["score"], 100.0, name)


class TestCommercialCommands(unittest.TestCase):
    def test_all_10_named_commands_are_recognized(self):
        for phrasing in ccc.COMMERCIAL_COMMANDS:
            result = ccc.answer_commercial_command(phrasing)
            self.assertNotEqual(
                result["answer"].get("status") if isinstance(result["answer"], dict) else None,
                "UNRECOGNIZED_COMMAND", phrasing,
            )

    def test_every_answer_has_evidence_and_timestamp(self):
        result = ccc.answer_commercial_command("Show me today's revenue.")
        self.assertIn("evidence", result)
        self.assertIn("timestamp", result)

    def test_unrecognized_command_is_honestly_flagged_not_guessed(self):
        result = ccc.answer_commercial_command("Do something completely unrelated")
        self.assertEqual(result["answer"]["status"], "UNRECOGNIZED_COMMAND")

    def test_case_and_punctuation_insensitive_matching(self):
        r1 = ccc.answer_commercial_command("show me today's revenue")
        r2 = ccc.answer_commercial_command("Show me today's revenue.")
        self.assertEqual(r1["answer"], r2["answer"])

    def test_todays_revenue_command_matches_snapshot_directly(self):
        import datetime
        now = datetime.datetime(2026, 8, 7, tzinfo=datetime.timezone.utc)
        r = ccc.answer_commercial_command("Show me today's revenue.", now=now)
        snap = ccc.revenue_snapshot(now=now)
        self.assertEqual(r["answer"], snap["ACTUAL"]["revenue_today_usd"])


class TestCommercialDailyBrief(unittest.TestCase):
    def test_all_12_named_fields_present(self):
        r = ccc.commercial_daily_brief()
        expected = {
            "revenue_usd", "net_revenue_usd", "best_product", "best_platform", "best_market",
            "best_acquisition_channel", "top_opportunity", "top_partnership", "top_affiliate_opportunity",
            "biggest_commercial_risk", "biggest_revenue_leak", "recommended_action",
        }
        self.assertTrue(expected.issubset(r.keys()))

    def test_best_product_honestly_no_revenue_yet(self):
        r = ccc.commercial_daily_brief()
        self.assertEqual(r["best_product"]["status"], "NO_REAL_REVENUE_YET")

    def test_recommended_action_is_a_nonempty_string(self):
        r = ccc.commercial_daily_brief()
        self.assertIsInstance(r["recommended_action"], str)
        self.assertGreater(len(r["recommended_action"]), 10)

    def test_never_raises_even_if_a_sub_call_fails(self):
        with patch("business_development.top_partnership_opportunities", side_effect=RuntimeError("boom")):
            r = ccc.commercial_daily_brief()
        self.assertIsNotNone(r)


if __name__ == "__main__":
    unittest.main()
