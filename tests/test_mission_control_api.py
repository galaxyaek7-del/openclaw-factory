"""Tests for mission_control_api.py (Phase 8).

Runs with stdlib unittest. Tests the dispatch functions directly
(importing the module), not via subprocess, to keep this fast and
avoid depending on the real filesystem's exact current state where
avoidable.

    python -m unittest tests.test_mission_control_api -v
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import mission_control_api


class TestEndpointDispatch(unittest.TestCase):
    def test_all_four_endpoints_are_registered(self):
        for name in ("opportunities", "production", "revenue", "automation"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_opportunities_returns_real_ranking_shape(self):
        result = mission_control_api._opportunities()
        self.assertIn("all", result)
        self.assertIn("queue", result)

    def test_production_returns_real_factory_shape(self):
        result = mission_control_api._production()
        self.assertIn("processed", result)
        self.assertIn("dossiers", result)

    def test_revenue_returns_real_pipeline_shape_plus_ceo_report(self):
        result = mission_control_api._revenue()
        self.assertIn("processed", result)
        self.assertIn("ceo_report_markdown", result)
        self.assertIsInstance(result["ceo_report_markdown"], str)

    def test_automation_never_claims_live_status(self):
        """Zero fabrication: this must never claim n8n live status is
        available when it structurally cannot check it."""
        result = mission_control_api._automation()
        self.assertFalse(result["live_status_available"])
        self.assertIn("reason", result)


class TestCliDispatch(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(_FACTORY_ROOT / "mission_control_api.py"), *args],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )

    def test_unknown_endpoint_fails_honestly_not_silently(self):
        proc = self._run("not-a-real-endpoint")
        self.assertNotEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertFalse(data["success"])
        self.assertIn("unknown endpoint", data["error"])

    def test_no_endpoint_argument_fails_honestly(self):
        proc = self._run()
        self.assertNotEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertFalse(data["success"])

    def test_automation_endpoint_runs_end_to_end_via_real_cli(self):
        proc = self._run("automation")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertTrue(data["success"])
        self.assertIn("workflows", data)


if __name__ == "__main__":
    unittest.main()
