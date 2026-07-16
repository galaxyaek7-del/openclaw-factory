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
    def test_all_six_endpoints_are_registered(self):
        for name in ("opportunities", "production", "revenue", "automation",
                     "decision_history", "system_configuration"):
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

    def test_decision_history_returns_summary_records_newest_first(self):
        result = mission_control_api._decision_history()
        self.assertIn("history", result)
        self.assertIn("count", result)
        self.assertEqual(result["count"], len(result["history"]))
        for record in result["history"]:
            self.assertEqual(set(record.keys()), set(mission_control_api._DECISION_SUMMARY_FIELDS))
        dates = [r["decided_at"] for r in result["history"] if r["decided_at"]]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_decision_history_never_includes_the_heavy_evaluation_snapshot(self):
        """The full per-decision evaluation_snapshot is already reachable
        via the opportunity-queue/market-intelligence services; a summary
        listing must not re-embed it (it made a 555-record response ~4.5MB
        before this projection was added)."""
        result = mission_control_api._decision_history()
        for record in result["history"]:
            self.assertNotIn("evaluation_snapshot", record)
            self.assertNotIn("external_signal", record)

    def test_system_configuration_exposes_real_tier_weights_and_floor(self):
        from profit_oracle import TIER_WEIGHTS, MIN_OPPORTUNITY_SCORE
        result = mission_control_api._system_configuration()
        self.assertEqual(result["tier_weights"], TIER_WEIGHTS)
        self.assertEqual(result["min_opportunity_score"], MIN_OPPORTUNITY_SCORE)

    def test_system_configuration_reads_real_economics_and_capability_registry(self):
        result = mission_control_api._system_configuration()
        self.assertIsNotNone(result["economics"])
        self.assertIsNotNone(result["capability_registry"])
        self.assertIn("platforms", result["economics"])


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

    def test_decision_history_endpoint_runs_end_to_end_via_real_cli(self):
        proc = self._run("decision_history")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertTrue(data["success"])
        self.assertIn("history", data)

    def test_system_configuration_endpoint_runs_end_to_end_via_real_cli(self):
        proc = self._run("system_configuration")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertTrue(data["success"])
        self.assertIn("tier_weights", data)


if __name__ == "__main__":
    unittest.main()
