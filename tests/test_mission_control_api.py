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
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import mission_control_api


class TestEndpointDispatch(unittest.TestCase):
    def test_all_ten_endpoints_are_registered(self):
        for name in ("opportunities", "production", "revenue", "automation",
                     "decision_history", "system_configuration",
                     "rerun_market_analysis", "trigger_opportunity_evaluation",
                     "validation_report", "export_executive_report"):
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

    def test_automation_reports_all_four_real_workflows_not_just_the_two_with_fixes(self):
        """n8n Integration Gap fix: before this, Mission Control's automation
        view only knew about the 2 workflows re-exported after ADR-045's
        fixes, silently omitting Openclaw_Sensing_Engine and 02_Sales_Poll —
        which never needed a fix, so were never re-exported, but are just
        as real and just as relevant to 'is workflow execution observable'."""
        result = mission_control_api._automation()
        names = {w["name"] for w in result["workflows"]}
        self.assertEqual(names, {"00_CEO", "01_Market_Scout", "Openclaw_Sensing_Engine", "02_Sales_Poll"})

    def test_automation_labels_current_vs_backup_sourced_workflows_honestly(self):
        """The two fixed workflows come from a current re-export; the other
        two only exist in a dated backup — the response must never blur
        that distinction into looking like one uniform 'live' source."""
        result = mission_control_api._automation()
        by_name = {w["name"]: w for w in result["workflows"]}
        self.assertEqual(by_name["00_CEO"]["source_kind"], "current_export")
        self.assertEqual(by_name["01_Market_Scout"]["source_kind"], "current_export")
        self.assertEqual(by_name["Openclaw_Sensing_Engine"]["source_kind"], "backup_2026-07-15")
        self.assertEqual(by_name["02_Sales_Poll"]["source_kind"], "backup_2026-07-15")

    def test_automation_surfaces_real_trends_pipeline_evidence(self):
        """Real, verifiable proof the n8n -> /api/trends path fired for real
        at least once (a genuine OPPORTUNITIES.md entry whose exact reason
        string and timestamp format only come from that one code path) —
        must be surfaced, not silently dropped."""
        result = mission_control_api._automation()
        evidence = result["trends_pipeline_evidence"]
        self.assertIsNotNone(evidence)
        self.assertGreaterEqual(evidence["count"], 1)
        self.assertIn("نجحت كل فحوصات الجودة", evidence["most_recent"])

    def test_find_trends_pipeline_evidence_ignores_market_hunter_entries(self):
        """market_hunter.py's own OPPORTUNITIES.md entries ('market_hunter:
        <verdict> (<score>/100)') must never be mistaken for n8n-fed ones —
        they're a completely different, already-attributed source."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            opp_file = Path(tmp) / "OPPORTUNITIES.md"
            opp_file.write_text(
                "- [2026-01-01T00:00:00.000Z] some niche — market_hunter: GOOD (70/100)\n",
                encoding="utf-8",
            )
            with patch.object(mission_control_api, "_FACTORY_ROOT", Path(tmp)):
                evidence = mission_control_api._find_trends_pipeline_evidence()
            self.assertIsNone(evidence)

    def test_find_trends_pipeline_evidence_missing_file_is_honest_none(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(mission_control_api, "_FACTORY_ROOT", Path(tmp)):
                evidence = mission_control_api._find_trends_pipeline_evidence()
            self.assertIsNone(evidence)

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

    def test_validation_report_returns_the_real_daily_report_and_markdown(self):
        result = mission_control_api._validation_report()
        self.assertIn("report", result)
        self.assertIn("markdown", result)
        self.assertIn("opportunities_discovered", result["report"])
        self.assertIsInstance(result["markdown"], str)

    def test_export_executive_report_combines_both_real_reports_and_saves_a_file(self):
        """Patches _FACTORY_ROOT to a scratch directory so this test never
        writes into the real reports/ folder."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(mission_control_api, "_FACTORY_ROOT", Path(tmp)):
                result = mission_control_api._export_executive_report()
            self.assertTrue(result["path"].startswith("reports/"))
            self.assertIn("# OpenClaw Executive Report", result["markdown"])
            self.assertIn("## Validation", result["markdown"])
            self.assertIn("## Revenue", result["markdown"])
            written = Path(tmp) / result["path"]
            self.assertTrue(written.exists())

    def test_rerun_market_analysis_calls_golden_hunter_run_hunt_only(self):
        """Mocked: run_hunt() is a real, live-network pipeline (HN/GitHub/
        Stack Exchange per signal) that can take minutes — this test only
        verifies the wiring/passthrough, never runs it for real."""
        fake_queue = [{"niche": "fake", "evidence": {}}]
        with patch("golden_hunter.hunt.run_hunt", return_value=fake_queue) as mock_hunt:
            result = mission_control_api._rerun_market_analysis()
        mock_hunt.assert_called_once_with()
        self.assertEqual(result["queue"], fake_queue)
        self.assertEqual(result["count"], 1)

    def test_trigger_opportunity_evaluation_never_allows_execute_production_true(self):
        """Mocked for the same live-network reason as above, and asserts
        the one real safety guarantee this action makes: it can never
        pass execute_production=True to the real cycle, no matter what."""
        fake_result = {"processed": 0, "results": []}
        with patch("real_world_mode.operating_mode.run_real_world_cycle", return_value=fake_result) as mock_cycle:
            result = mission_control_api._trigger_opportunity_evaluation()
        mock_cycle.assert_called_once_with(execute_production=False)
        self.assertEqual(result, fake_result)


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

    def test_validation_report_endpoint_runs_end_to_end_via_real_cli(self):
        proc = self._run("validation_report")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertTrue(data["success"])
        self.assertIn("report", data)

    # rerun_market_analysis and trigger_opportunity_evaluation are
    # deliberately NOT exercised via real subprocess CLI here — both hit
    # live external services (HN/GitHub/Stack Exchange) per real signal
    # and can take minutes; that would make the whole suite unreliable
    # and slow. Their wiring is covered by the mocked tests above; their
    # real end-to-end behavior was already verified live earlier this
    # session (real_world_mode/golden_hunter test suites + manual runs).


if __name__ == "__main__":
    unittest.main()
