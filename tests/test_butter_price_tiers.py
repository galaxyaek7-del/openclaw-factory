"""Tests for profit_oracle.butter_price()'s four independent bands
(book/printable/premium/elite — ADR-020/ADR-024/ADR-027) and
economics.py's matching platform floors.

Runs with stdlib unittest (see tests/test_base_arm.py).

    python -m unittest tests.test_butter_price_tiers -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import economics
import profit_oracle as po


class TestButterPriceElite(unittest.TestCase):
    def test_elite_price_within_band(self):
        for niche in ["daily habit tracker", "premium subscription enterprise system", "planner"]:
            price = po.butter_price(niche, product_type="elite")
            self.assertGreaterEqual(price, po.MIN_BUTTER_PRICE_ELITE)
            self.assertLessEqual(price, po.MAX_BUTTER_PRICE_ELITE)

    def test_elite_band_is_independent_of_premium_band(self):
        niche = "premium subscription budget planner"
        elite_price = po.butter_price(niche, product_type="elite")
        premium_price = po.butter_price(niche, product_type="premium")
        self.assertGreater(elite_price, premium_price)

    def test_book_and_printable_unaffected_by_elite_addition(self):
        """Regression guard: adding the elite branch must never change
        book/printable pricing — same niches, same expected values as
        before this change (verified manually against git history when
        this test was written)."""
        cases = {
            ("daily habit tracker", "printable"): 9,
            ("planner", "printable"): 8,
            ("cookbook", "book"): 35,
        }
        for (niche, product_type), expected in cases.items():
            self.assertEqual(po.butter_price(niche, product_type=product_type), expected)


class TestEconomicsEliteFloor(unittest.TestCase):
    def setUp(self):
        self.config = economics.load_config()

    def test_elite_97_clears_floor(self):
        result = economics.evaluate(97, "gumroad_elite", self.config, page_count=50)
        self.assertTrue(result["approved"])

    def test_elite_below_floor_rejected(self):
        result = economics.evaluate(50, "gumroad_elite", self.config, page_count=50)
        self.assertFalse(result["approved"])

    def test_thin_elite_bundle_flagged_unrealistic_not_exempted(self):
        result = economics.evaluate(497, "gumroad_elite", self.config, page_count=5)
        self.assertFalse(result["market_realistic"])
        self.assertLessEqual(result["suggested_realistic_price"], 97)

    def test_kdp_ebook_and_gumroad_premium_unaffected_by_elite_addition(self):
        kdp = economics.evaluate(9.99, "kdp_ebook", self.config, page_count=60)
        self.assertTrue(kdp["approved"])
        self.assertEqual(kdp["min_required"], 6.00)
        premium = economics.evaluate(97, "gumroad_premium", self.config, page_count=50)
        self.assertTrue(premium["approved"])
        self.assertEqual(premium["min_required"], 25.00)


if __name__ == "__main__":
    unittest.main()
