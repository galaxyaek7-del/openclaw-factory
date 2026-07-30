"""Tests for simulation_mode.py (ADR-153, 2026-07-30): generalizes this
factory's own real dry_run discipline (channels/base_arm.py,
distributor.py, reality.py) to "don't really transact."

    python -m unittest tests.test_simulation_mode -v
"""

import os
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import simulation_mode


class TestSimulationMode(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get("AFFILIATE_MODE")

    def tearDown(self):
        if self._old is None:
            os.environ.pop("AFFILIATE_MODE", None)
        else:
            os.environ["AFFILIATE_MODE"] = self._old

    def test_defaults_to_simulation_when_unset(self):
        os.environ.pop("AFFILIATE_MODE", None)
        self.assertTrue(simulation_mode.is_simulation_mode("affiliate_commerce"))

    def test_explicit_production_flips_it(self):
        os.environ["AFFILIATE_MODE"] = "production"
        self.assertFalse(simulation_mode.is_simulation_mode("affiliate_commerce"))

    def test_explicit_simulation_value_stays_true(self):
        os.environ["AFFILIATE_MODE"] = "simulation"
        self.assertTrue(simulation_mode.is_simulation_mode("affiliate_commerce"))

    def test_unknown_division_defaults_to_simulation(self):
        self.assertTrue(simulation_mode.is_simulation_mode("some_division_with_no_real_code_yet"))

    def test_tag_simulated_never_mutates_input(self):
        original = {"product_id": "X"}
        tagged = simulation_mode.tag_simulated(original)
        self.assertNotIn("simulation", original)
        self.assertTrue(tagged["simulation"])
        self.assertEqual(tagged["product_id"], "X")


if __name__ == "__main__":
    unittest.main()
