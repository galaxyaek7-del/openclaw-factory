"""GF-ROS Milestone 9: the read model as a Mission Control surface.

Acceptance: renders with an empty dataset, reports UNKNOWN where no signal
exists (never 0 presented as truth), and is read-only.
"""
import io
import os
import tempfile
import unittest

import revenue_os


class TestReadModelSurface(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.paths = {
            "orders_path": os.path.join(self.tmp.name, "orders.jsonl"),
            "payouts_path": os.path.join(self.tmp.name, "payouts.jsonl"),
            "costs_path": os.path.join(self.tmp.name, "costs.jsonl"),
            "reconciliation_path": os.path.join(self.tmp.name, "recon.jsonl"),
            "commission_ledger_path": os.path.join(self.tmp.name, "comm.jsonl"),
        }

    def test_empty_dataset_reports_unknown_not_fabricated_zero(self):
        model = revenue_os.revenue_read_model(**self.paths)
        self.assertEqual(model["verified_revenue_usd"], 0.0)
        for key in ("refund_rate", "conversion_rate", "cac_usd"):
            self.assertEqual(model["unknowns"][key], "UNKNOWN")

    def test_counts_are_real_zeros_with_a_named_source(self):
        model = revenue_os.revenue_read_model(**self.paths)
        self.assertEqual(model["counts"]["orders"], 0)
        self.assertIn("orders", model["sources"])
        self.assertTrue(model["sources"]["orders"].endswith("orders.jsonl"))

    def test_observed_revenue_is_never_promoted(self):
        model = revenue_os.revenue_read_model(**self.paths)
        self.assertIn("reconciled_observed_usd", model)
        self.assertEqual(model["reconciled_observed_usd"], 0)
        self.assertEqual(model["verified_revenue_usd"], 0.0)

    def test_call_writes_nothing(self):
        before = set(os.listdir(self.tmp.name))
        revenue_os.revenue_read_model(**self.paths)
        self.assertEqual(set(os.listdir(self.tmp.name)), before)


class TestWiring(unittest.TestCase):
    def test_endpoint_registered(self):
        import mission_control_api as mca
        self.assertIn("revenue_os_read_model", mca._ENDPOINTS)
        payload = mca._ENDPOINTS["revenue_os_read_model"]()
        self.assertIn("verified_revenue_usd", payload)

    def test_service_and_panel_exist(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with io.open(os.path.join(root, "server.js"), encoding="utf-8") as f:
            self.assertIn("revenue-os-read-model", f.read())
        with io.open(os.path.join(root, "mission_control_executive_v1.html"),
                     encoding="utf-8") as f:
            html = f.read()
        self.assertIn("revenue-os-read-model", html)
        self.assertIn("group:'revenue'", html)


if __name__ == "__main__":
    unittest.main()
