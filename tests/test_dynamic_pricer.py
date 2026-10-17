"""src/pricing/dynamic_pricer.py: recommendation only, never invents a price.

recommend() and the DynamicPricer class share one rule: a competitor price
counts only with an http(s) source. No network, no live price change.
(Rewritten 2026-10-17: the earlier version of this file asserted that
apply_to_product() returned applied=True for unsourced prices; that method
was removed by founder directive as fabricated evidence.)
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.pricing import dynamic_pricer as P  # noqa: E402

COMPS = [{"name": "A", "url": "https://example.com/a", "price_usd": 40},
         {"name": "B", "url": "https://example.com/b", "price_usd": 60}]


class TestRecommend(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.log = self.tmp / "rec.jsonl"
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_ten_percent_under_cheapest_sourced_competitor(self):
        r = P.recommend({"id": "X", "price": 29, "competitors": COMPS}, unit_cost=1, log_path=self.log)
        self.assertEqual(r["status"], P.PRICED)
        self.assertEqual(r["recommended_price_usd"], 35.99)          # 40 * 0.9 = 36 -> 35.99
        self.assertEqual(r["change_usd"], 6.99)
        self.assertFalse(r["live_change"])

    def test_no_sourced_competitor_means_research_needed(self):
        r = P.recommend({"id": "X", "price": 29, "competitors": [{"name": "no url", "price_usd": 9}]},
                        log_path=self.log)
        self.assertEqual(r["status"], P.RESEARCH_NEEDED)
        self.assertIsNone(r["recommended_price_usd"])

    def test_margin_floor_wins_over_undercut(self):
        self.assertEqual(P.margin_floor(20), 50.0)                   # 20 / (1 - 0.60)
        r = P.recommend({"id": "X", "competitors": COMPS}, unit_cost=20, log_path=self.log)
        self.assertEqual((r["status"], r["recommended_price_usd"]), (P.FLOOR_BOUND, 50.0))

    def test_every_recommendation_is_logged(self):
        P.recommend({"id": "X", "competitors": COMPS}, log_path=self.log)
        P.recommend({"id": "Y"}, log_path=self.log)
        rows = [json.loads(l) for l in self.log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["product_id"] for r in rows], ["X", "Y"])


class TestDynamicPricerClass(unittest.TestCase):
    SRC = ["https://a.example/1", "https://b.example/2", "https://c.example/3", "https://d.example/4"]

    def test_ten_percent_under_cheapest_and_cites_its_source(self):
        r = P.DynamicPricer().calculate_optimal_price([50, 60, 45, 70], self.SRC, product_cost=5)
        self.assertEqual((r["status"], r["suggested_price"]), ("CALCULATED", 40.5))
        self.assertEqual(r["cheapest_source"], "https://c.example/3")   # the source of 45, not of 50

    def test_margin_floor(self):
        r = P.DynamicPricer().calculate_optimal_price([8, 9, 10], self.SRC, product_cost=6)
        self.assertEqual((r["suggested_price"], r["basis"]), (15.0, "MARGIN_FLOOR"))

    def test_unsourced_and_invalid_prices_are_dropped(self):
        r = P.DynamicPricer().calculate_optimal_price([0, -3, "x", 30], self.SRC[:3] + ["ftp://x"], product_cost=5)
        self.assertEqual(r["status"], "CANNOT_PRICE")
        self.assertFalse(hasattr(P.DynamicPricer, "apply_to_product"))


if __name__ == "__main__":
    unittest.main()
