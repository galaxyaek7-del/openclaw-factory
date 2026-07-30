"""Tests for launch_readiness.py (ADR-153, 2026-07-30): a real,
per-division 8-dimension scorecard -- every dimension is a mechanical,
disclosed-heuristic check, never a fabricated score for a division with
no real architecture.

    python -m unittest tests.test_launch_readiness -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import launch_readiness


class TestLaunchReadinessScore(unittest.TestCase):
    def test_returns_all_5_named_divisions(self):
        result = launch_readiness.launch_readiness_score()
        self.assertEqual(
            set(result["divisions"].keys()),
            {"affiliate_commerce", "digital_products", "saas", "ai_services", "licensing"},
        )

    def test_every_division_carries_all_8_named_dimensions(self):
        result = launch_readiness.launch_readiness_score()
        required = {"architecture", "automation", "testing", "compliance", "monitoring",
                    "documentation", "integration", "operational_readiness"}
        for div in result["divisions"].values():
            self.assertEqual(set(div["dimensions"].keys()), required, div["division"])

    def test_saas_ai_services_licensing_are_honestly_not_architected(self):
        result = launch_readiness.launch_readiness_score()
        for key in ("saas", "ai_services", "licensing"):
            div = result["divisions"][key]
            for dim_name, dim in div["dimensions"].items():
                self.assertEqual(dim["value"], launch_readiness.NOT_ARCHITECTED,
                                  f"{key}.{dim_name} should be honestly not_architected")

    def test_affiliate_commerce_architecture_reflects_real_files(self):
        result = launch_readiness.launch_readiness_score()
        arch = result["divisions"]["affiliate_commerce"]["dimensions"]["architecture"]
        self.assertNotEqual(arch["value"], launch_readiness.NOT_ARCHITECTED)
        self.assertIn("affiliate_commerce/networks.py", arch["files"])

    def test_digital_products_testing_counts_real_test_functions(self):
        result = launch_readiness.launch_readiness_score()
        testing = result["divisions"]["digital_products"]["dimensions"]["testing"]
        self.assertIsInstance(testing["value"], int)
        self.assertGreater(testing["value"], 0)

    def test_operational_readiness_only_real_when_all_7_dimensions_real(self):
        result = launch_readiness.launch_readiness_score()
        for div in result["divisions"].values():
            dims = div["dimensions"]
            real_count = sum(1 for k, v in dims.items()
                              if k != "operational_readiness" and v["value"] != launch_readiness.NOT_ARCHITECTED)
            op = dims["operational_readiness"]
            if real_count == 7:
                self.assertNotEqual(op["value"], launch_readiness.NOT_ARCHITECTED, div["division"])
            else:
                self.assertEqual(op["value"], launch_readiness.NOT_ARCHITECTED, div["division"])


if __name__ == "__main__":
    unittest.main()
