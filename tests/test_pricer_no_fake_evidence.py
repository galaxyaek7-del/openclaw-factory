"""Founder directive 2026-10-17 (Cleanup + Evidence Fix, Mission 1).

DynamicPricer must never claim REAL evidence or an applied price without a
source URL. Assertions are the directive's own; they sit in a TestCase so
CI's unittest runner collects them (bare pytest functions are skipped there).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pricing.dynamic_pricer import DynamicPricer  # noqa: E402


class TestPricerNoFakeEvidence(unittest.TestCase):
    def test_no_fake_real_evidence(self):
        """Pricer never claims REAL without source"""
        result = DynamicPricer().calculate_optimal_price(
            competitor_prices=[50, 60, 45], price_sources=[], product_cost=5)
        assert result["status"] == "CANNOT_PRICE"
        assert result["applied"] is False
        assert result["evidence_type"] == "NONE"

    def test_no_source_no_price(self):
        """Price without URL source is rejected"""
        result = DynamicPricer().calculate_optimal_price(
            competitor_prices=[45], price_sources=["not_a_url"], product_cost=5)
        assert result["status"] == "CANNOT_PRICE"

    def test_real_source_gives_price(self):
        """Valid URL source enables pricing"""
        result = DynamicPricer().calculate_optimal_price(
            competitor_prices=[50], price_sources=["https://gumroad.com/l/example"],
            product_cost=5, minimum_margin=0.60)
        assert result["status"] == "CALCULATED"
        assert result["suggested_price"] == 45.0
        assert result["evidence_type"] == "REAL"
        assert result["applied"] is False

    def test_applied_always_false_automatically(self):
        """Applied is never True automatically"""
        result = DynamicPricer().calculate_optimal_price(
            competitor_prices=[40], price_sources=["https://example.gumroad.com/l/x"], product_cost=3)
        assert result.get("applied") is False


if __name__ == "__main__":
    unittest.main()
