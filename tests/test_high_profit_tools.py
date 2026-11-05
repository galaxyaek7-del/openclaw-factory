"""High-profit investment tools — connections and behavior."""
import unittest
from pathlib import Path

class TestHighProfitScreener(unittest.TestCase):
    def test_module_imports(self):
        import tools.high_profit_screener as s
        self.assertTrue(hasattr(s, 'is_high_profit'))
        self.assertTrue(hasattr(s, 'screen_high_profit'))
        self.assertTrue(hasattr(s, 'screener_report'))

    def test_is_high_profit_known_cases(self):
        from tools.high_profit_screener import is_high_profit
        # Low score
        ok, reason = is_high_profit({"commercial_score": 60, "ranking_dimensions": {"willingness_to_pay": {"value": "high"}}})
        self.assertFalse(ok)
        # High score but UNKNOWN wtp
        ok, _ = is_high_profit({"commercial_score": 80, "ranking_dimensions": {"willingness_to_pay": {"value": "UNKNOWN"}}})
        self.assertFalse(ok)
        # High score with real wtp and not dead zone
        ok, reason = is_high_profit({"commercial_score": 80, "ranking_dimensions": {"willingness_to_pay": {"value": "high"}, "recurring_revenue_potential": {"value": 70}}, "estimated_profit": {"in_dead_zone": False}})
        self.assertTrue(ok)

    def test_screen_uses_investment_pipeline(self):
        import inspect
        src = Path("tools/high_profit_screener.py").read_text(encoding="utf-8")
        self.assertIn("from investment_pipeline import build_investment_pipeline", src)
        self.assertIn("is_high_profit", src)

    def test_screener_report_structure(self):
        from tools.high_profit_screener import screener_report
        r = screener_report(limit=5)
        self.assertIn("total_screened", r)
        self.assertIn("high_profit_count", r)
        self.assertIn("criteria", r)

class TestPremiumPricingValidator(unittest.TestCase):
    def test_module_imports(self):
        import tools.premium_pricing_validator as v
        self.assertTrue(hasattr(v, 'validate_premium_price'))

    def test_uses_g2_central(self):
        src = Path("tools/premium_pricing_validator.py").read_text(encoding="utf-8")
        self.assertIn("economics.platform_for_product_type", src)

    def test_premium_17_pages_unrealistic(self):
        from tools.premium_pricing_validator import validate_premium_price
        r = validate_premium_price(327, "premium", page_count=17)
        # 17 pages at $327 for premium (gumroad_premium) → market unrealistic per economics
        self.assertFalse(r["valid"])
        self.assertIn("market", r["reason"].lower() if "reason" in r else "")

    def test_g2_still_verified(self):
        self.assertIn("def platform_for_product_type", Path("economics.py").read_text(encoding="utf-8"))  # ADR-065: central entry point, canonical table in book_generator

    def test_d6_d8_d10_still_verified(self):
        self.assertIn("abs(rate - t) < 1e-9", Path("economics.py").read_text(encoding="utf-8"))
        self.assertIn('platform="gumroad_digital"', Path("profit_oracle.py").read_text(encoding="utf-8"))
        self.assertIn("astimezone(timezone.utc)", Path("profit_oracle.py").read_text(encoding="utf-8"))

    def test_no_external_calls(self):
        src = Path("tools/high_profit_screener.py").read_text(encoding="utf-8") + Path("tools/premium_pricing_validator.py").read_text(encoding="utf-8")
        self.assertNotIn("http", src.lower())
        self.assertNotIn("fetch", src.lower())
