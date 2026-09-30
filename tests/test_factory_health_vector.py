"""Tier-1 tests: health vector honesty (no fabricated scores)."""
import unittest

import factory_health_vector as hv

ALLOWED = {"HEALTHY", "DEGRADED", "CRITICAL", "UNKNOWN"}


class TestHealthVector(unittest.TestCase):
    def test_all_dimensions_present(self):
        vec = hv.health_vector()
        for dim in hv.DIMENSIONS:
            self.assertIn(dim, vec)
            self.assertIn(vec[dim]["status"], ALLOWED)
            self.assertTrue(vec[dim]["evidence"])

    def test_no_aggregate_score(self):
        vec = hv.health_vector()
        flat = str(vec).lower()
        self.assertNotIn("overall_score", flat)
        self.assertNotIn("health_score", flat)

    def test_commercial_reports_revenue_as_fact(self):
        vec = hv.health_vector()
        self.assertIn("revenue_usd", vec["COMMERCIAL_HEALTH"]["evidence"])


if __name__ == "__main__":
    unittest.main()
