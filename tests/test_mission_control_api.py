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
    def test_all_twelve_endpoints_are_registered(self):
        for name in ("opportunities", "production", "revenue", "automation",
                     "decision_history", "system_configuration", "recovery",
                     "rerun_market_analysis", "trigger_opportunity_evaluation",
                     "validation_report", "export_executive_report", "full_cycle"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_recovery_returns_the_real_factory_state_shape(self):
        """Unified Recovery System §6 — this must reflect exactly what
        factory_state.py's own load_state() returns, plus the last real
        recovery action, never a second, competing computation."""
        import factory_state
        result = mission_control_api._recovery()
        for key in ("current_task", "active_workflow", "recovery_info",
                    "pending_retries", "last_successful_checkpoint",
                    "last_successful_recovery", "updated_at"):
            self.assertIn(key, result)
        real_state = factory_state.load_state()
        self.assertEqual(result["recovery_info"], real_state["recovery_info"])

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


class TestFullCycle(unittest.TestCase):
    """_full_cycle() (Phase 11 — Autonomous Production Launch). Every real
    module it calls is mocked here so these tests stay fast (the real
    market_intelligence_and_evaluation stage alone takes minutes of live
    network calls) — the modules themselves are already tested elsewhere
    (test_real_world_mode.py, test_production_factory.py, etc.); these
    tests are about _full_cycle()'s own orchestration and graceful
    degradation, not re-verifying each reused module's internals."""

    def _patched(self, tmp_path, **overrides):
        """Context manager stack patching every stage to a fast, successful
        default, with per-test overrides for the ones under test."""
        from contextlib import ExitStack
        defaults = {
            "real_world_mode.operating_mode.run_real_world_cycle": lambda **k: {"processed": 0, "results": []},
            "production_factory.factory.run_production_factory": lambda: {"processed": 0, "dossiers": []},
            "validation_layer.daily_report.generate_daily_report": lambda **k: {
                "opportunities_discovered": 0, "opportunities_accepted": 0,
                "failures": [], "bottlenecks": [], "stalled_opportunities": [],
            },
            "validation_layer.daily_report.render_markdown": lambda report: "md",
            "revenue_pipeline.pipeline.run_revenue_pipeline": lambda **k: {"processed": 0},
            "revenue_pipeline.pipeline.render_ceo_revenue_report": lambda result: "md",
            "decision_engine.feedback.sync_outcomes": lambda **k: {"synced": 0},
            "decision_engine.learning.recalibration_report": lambda **k: {"recalibrated": False},
        }
        defaults.update(overrides)
        stack = ExitStack()
        stack.enter_context(patch.object(mission_control_api, "_FACTORY_ROOT", tmp_path))
        for target, side_effect in defaults.items():
            stack.enter_context(patch(target, side_effect=side_effect))
        return stack

    def test_all_stages_present_and_completed_on_the_happy_path(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self._patched(Path(tmp)):
                result = mission_control_api._full_cycle()
            expected_stages = {
                "market_intelligence_and_evaluation", "production", "quality_validation",
                "executive_reports", "automation_snapshot", "security_snapshot",
                "learning", "knowledge_base_update",
            }
            self.assertEqual(set(result["stages"].keys()), expected_stages)
            self.assertEqual(result["stages_completed"], result["stages_total"])
            self.assertTrue(result["cycle_id"].startswith("cycle_"))

    def test_one_stage_failing_never_blocks_the_others(self):
        """Graceful degradation, objective 10: a real exception in one
        stage must not prevent the rest from completing."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self._patched(
                Path(tmp),
                **{"production_factory.factory.run_production_factory": lambda: (_ for _ in ()).throw(RuntimeError("synthetic failure"))},
            ):
                result = mission_control_api._full_cycle()
            self.assertFalse(result["stages"]["production"]["ok"])
            self.assertIn("synthetic failure", result["stages"]["production"]["error"])
            other_stages = {k: v for k, v in result["stages"].items() if k != "production"}
            self.assertTrue(all(s["ok"] for s in other_stages.values()), other_stages)
            self.assertEqual(result["stages_completed"], result["stages_total"] - 1)

    def test_knowledge_base_update_appends_a_real_record_to_the_patched_path(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with self._patched(tmp_path):
                result = mission_control_api._full_cycle()
            log_file = tmp_path / "data" / "full_cycle_runs.jsonl"
            self.assertTrue(log_file.exists())
            record = json.loads(log_file.read_text(encoding="utf-8").strip())
            self.assertEqual(record["cycle_id"], result["cycle_id"])
            self.assertIn("stages_summary", record)

    def test_security_snapshot_counts_real_rejected_niches_entries(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "REJECTED_NICHES.md").write_text(
                "# header\n\n## \U0001f6ab 2026-01-01T00:00:00\n**niche:** a\n\n"
                "## \U0001f6ab 2026-01-02T00:00:00\n**niche:** b\n",
                encoding="utf-8",
            )
            with self._patched(tmp_path):
                result = mission_control_api._full_cycle()
            self.assertEqual(result["stages"]["security_snapshot"]["result"]["rejected_niches_recorded"], 2)

    def test_executive_reports_saves_a_file_named_after_the_cycle(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with self._patched(tmp_path):
                result = mission_control_api._full_cycle()
            report_path = tmp_path / result["stages"]["executive_reports"]["result"]["path"]
            self.assertTrue(report_path.exists())
            self.assertIn(result["cycle_id"], report_path.name)


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
