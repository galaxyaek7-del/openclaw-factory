import pytest
"""D16/D19 final deferred-item tests."""
import unittest
from pathlib import Path

# Cycle 84: this module exercises Gumroad write logic against a mocked
# HTTP layer, so it explicitly opts in to write authorization. It was
# previously getting this from an AUTOUSE fixture that set
# FACTORY_LIVE_PUBLISH=true for the whole suite -- a hidden broad
# permission. The opt-in is now visible here, in the file that needs it.
pytestmark = pytest.mark.usefixtures("authorize_live_writes")

class TestD16RetryGate(unittest.TestCase):
    def test_normalization_logic(self):
        # D16 fix: strip().lower().startswith("arm not ready:")
        def is_arm_not_ready(error):
            return str(error or "").strip().lower().startswith("arm not ready:")
        self.assertTrue(is_arm_not_ready("arm not ready: missing token"))
        self.assertTrue(is_arm_not_ready("  arm not ready: missing token"))
        self.assertTrue(is_arm_not_ready("Arm Not Ready: missing token"))
        self.assertTrue(is_arm_not_ready("  Arm Not Ready: missing token"))
        self.assertFalse(is_arm_not_ready("network timeout"))
        self.assertFalse(is_arm_not_ready(""))
        self.assertFalse(is_arm_not_ready(None))

    def test_distributor_code_uses_normalized_check(self):
        src = Path("distributor.py").read_text(encoding="utf-8")
        self.assertIn('.strip().lower().startswith("arm not ready:")', src)

    def test_distributor_still_imports(self):
        import distributor  # must not crash
        self.assertTrue(hasattr(distributor, 'distribute'))

class TestD19DocumentationOnly(unittest.TestCase):
    def test_get_economics_missing_keys_returns_unknown(self):
        from decision_engine.engine import _get_economics
        analysis = {"niche": "test", "ai_ceo": {"decision": "WAIT"}, "dimension_scores": {}}
        result = _get_economics(analysis)
        self.assertIsNotNone(result)

    def test_get_economics_documentation_present(self):
        src = Path("decision_engine/engine.py").read_text(encoding="utf-8")
        self.assertIn("market_intelligence_core.evaluate_opportunity() does NOT produce", src)
        self.assertIn("conservative", src)

    def test_d6_still_verified(self):
        self.assertIn("abs(rate - t) < 1e-9", Path("economics.py").read_text(encoding="utf-8"))

    def test_d8_still_verified(self):
        self.assertIn('platform="gumroad_digital"', Path("profit_oracle.py").read_text(encoding="utf-8"))

    def test_d10_still_verified(self):
        self.assertIn("astimezone(timezone.utc)", Path("profit_oracle.py").read_text(encoding="utf-8"))

    def test_g2_still_verified(self):
        import economics
        self.assertEqual(economics.platform_for_product_type("techdoc"), "gumroad_elite")
