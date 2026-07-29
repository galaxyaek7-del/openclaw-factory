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
                     "validation_report", "export_executive_report", "full_cycle",
                     "production_families", "commercial_execution"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_evidence_network_endpoints_are_registered(self):
        for name in ("evidence_network_status", "evidence_coverage_status"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_evidence_network_status_reports_the_real_connector_registry(self):
        """Evidence Network (ADR-128, 2026-07-25) — Mission Control's real
        view of which evidence sources are actually callable today."""
        result = mission_control_api._evidence_network_status()
        self.assertIn("real_connectors", result)
        self.assertIn("discovery_connectors", result)
        real_names = {c["name"] for c in result["real_connectors"]}
        self.assertIn("competitor_discovery", real_names)
        self.assertIn("customer_pain", real_names)

    def test_evidence_coverage_status_reports_real_aggregate_and_freshness(self):
        result = mission_control_api._evidence_coverage_status()
        self.assertIn("aggregate", result)
        self.assertIn("freshness", result)
        self.assertIn("research_queue", result["aggregate"])
        self.assertIn("competitor_discovery", result["freshness"])
        self.assertIn("customer_pain", result["freshness"])

    def test_commercial_execution_reports_real_approval_gates_and_ledger_history(self):
        """Universal Production Engine Roadmap Step 4 (2026-07-19) —
        Mission Control's real view of the Commercial Execution Layer."""
        result = mission_control_api._commercial_execution()
        self.assertIn("gated", result["approval_gates"])
        self.assertIn("autonomous", result["approval_gates"])
        self.assertIsInstance(result["recent_publish_attempts"], list)

    def test_production_families_reports_the_11_upe_canonical_names(self):
        """Universal Production Engine §7 — Mission Control's own view of
        family readiness, reported under the founder-approved canonical
        names (not product_families.mapping.ALL_PRODUCT_FAMILIES's
        pre-UPE naming for the one still-unbuilt family, notion_systems)."""
        result = mission_control_api._production_families()
        families = result["families"]
        self.assertEqual(
            set(families),
            {
                "kdp_books", "professional_templates", "digital_toolkits",
                "knowledge_bases", "ai_saas", "automation_systems",
                "notion_workspaces", "spreadsheet_systems", "prompt_libraries",
                "api_products", "micro_saas",
            },
        )
        for real_family in ("kdp_books", "professional_templates", "digital_toolkits",
                             "knowledge_bases", "automation_systems"):
            self.assertTrue(families[real_family].startswith("REAL"))
        for unbuilt_family in ("ai_saas", "notion_workspaces", "api_products", "micro_saas"):
            self.assertTrue(families[unbuilt_family].startswith("NOT YET BUILT"))

    def test_production_families_surfaces_real_manifests_for_manifest_driven_families(self):
        """Universal Production Engine Roadmap Step 3 (2026-07-18): the
        Product Definition Registry's manifests are real, structured data
        Mission Control can show directly — never fabricated for a family
        that has none yet."""
        result = mission_control_api._production_families()
        manifests = result["manifests"]
        for manifest_driven_family in ("automation_systems", "professional_templates", "digital_toolkits"):
            self.assertIn(manifest_driven_family, manifests)
            m = manifests[manifest_driven_family]
            self.assertEqual(m["content_generator"], "groq_techdoc")
            self.assertEqual(m["asset_builder"], "techdoc_package")
            self.assertEqual(m["packager"], "single_file")
            self.assertIn("paddle", m["supported_marketplaces"])
        # kdp_books/knowledge_bases have real, distinct logic — no manifest,
        # never a fabricated one just to look complete.
        for bespoke_family in ("kdp_books", "knowledge_bases"):
            self.assertNotIn(bespoke_family, manifests)

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

    def test_golden_hunter_status_returns_real_shape_never_throws(self):
        result = mission_control_api._golden_hunter_status()
        self.assertIn("top_opportunities", result)
        self.assertIn("recent_activity_count_7d", result)
        self.assertIn("total_scored", result)
        for opp in result["top_opportunities"]:
            self.assertIn("pre_acceptance_roi", opp)

    def test_pioneer_status_honestly_discloses_shared_event_log(self):
        result = mission_control_api._pioneer_status()
        self.assertIn("combined_activity_count_7d", result)
        self.assertIn("note", result)

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
        writes into the real reports/ folder. Autonomous Digital Company
        v1 (2026-07-19): now also joins executive_intelligence's and
        strategic_intelligence's real reports, previously standalone-CLI
        only (ADR-052/ADR-054). EOS Phase 1 (2026-07-19): now also joins
        ai_capability's real provider registry."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(mission_control_api, "_FACTORY_ROOT", Path(tmp)):
                result = mission_control_api._export_executive_report()
            self.assertTrue(result["path"].startswith("reports/"))
            self.assertIn("# Galaxy Forge Executive Report", result["markdown"])
            self.assertIn("## Executive Summary", result["markdown"])
            self.assertIn("## Strategic Recommendations", result["markdown"])
            self.assertIn("## Validation", result["markdown"])
            self.assertIn("## Revenue", result["markdown"])
            self.assertIn("## AI Capability", result["markdown"])
            self.assertIn("## Infrastructure", result["markdown"])
            self.assertIn("## Market Review", result["markdown"])
            written = Path(tmp) / result["path"]
            self.assertTrue(written.exists())

    def test_get_infrastructure_status_returns_none_honestly_on_subprocess_failure(self):
        """EOS Phase 1 (2026-07-19): a missing Node binary or a subprocess
        hiccup must never break the rest of the combined report -- fails
        open (returns None), same discipline as every other section here."""
        with patch("subprocess.run", side_effect=FileNotFoundError("node not found")):
            self.assertIsNone(mission_control_api._get_infrastructure_status())

    def test_get_infrastructure_status_parses_real_shaped_stdout(self):
        fake_result = subprocess.CompletedProcess(args=[], returncode=0, stdout='{"system": {"cpu": {"count": 4}}, "ai_cost_trend": {}}')
        with patch("subprocess.run", return_value=fake_result):
            status = mission_control_api._get_infrastructure_status()
        self.assertEqual(status["system"]["cpu"]["count"], 4)

    def test_get_infrastructure_status_returns_none_on_nonzero_exit(self):
        fake_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="")
        with patch("subprocess.run", return_value=fake_result):
            self.assertIsNone(mission_control_api._get_infrastructure_status())

    def test_render_infrastructure_markdown_handles_none_honestly(self):
        md = mission_control_api._render_infrastructure_markdown(None)
        self.assertIn("تعذّر", md)

    def test_render_infrastructure_markdown_renders_real_shape(self):
        status = {
            "system": {"cpu": {"count": 4, "model": "Test CPU"}, "memory": {"used_pct": 50.0}, "disk": {"used_pct": 30.0}},
            "ai_cost_trend": {"recent_7d_cost_usd": 0.01, "recent_7d_calls": 5, "outlier": False},
        }
        md = mission_control_api._render_infrastructure_markdown(status)
        self.assertIn("Test CPU", md)
        self.assertIn("50.0", md)

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


class TestGlobalMarketLearningEngineActions(unittest.TestCase):
    """_get_niche_commercial_profile / _get_monthly_market_evolution_report
    / _get_commercial_recommendations (2026-07-23) -- real, non-stub
    delegation to market_memory.py, reading data/market_evidence.jsonl
    for real (no test-isolation override exists for these CLI actions,
    same as the pre-existing get_value_profile/get_value_engine_report
    actions), so these tests only assert the real shape/dispatch, never
    a specific real value that would drift as real evidence accumulates."""

    def test_all_three_actions_are_registered(self):
        for name in ("get_niche_commercial_profile", "get_monthly_market_evolution_report", "get_commercial_recommendations"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_global_execution_view_is_registered(self):
        self.assertIn("get_global_execution_view", mission_control_api._ENDPOINTS)

    def test_growth_report_and_channel_expansion_actions_are_registered(self):
        for name in ("get_growth_report", "get_channel_expansion_status"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_commercial_intelligence_and_premium_catalog_actions_are_registered(self):
        for name in ("get_commercial_intelligence_report", "get_premium_product_catalog_status"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_investment_pipeline_actions_are_registered(self):
        for name in ("get_investment_pipeline_entry", "get_investment_pipeline"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_investment_pipeline_entry_requires_a_niche(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_investment_pipeline_entry", json.dumps({})]):
            with self.assertRaises(ValueError):
                mission_control_api._get_investment_pipeline_entry()

    def test_investment_pipeline_entry_delegates_to_the_real_module(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_investment_pipeline_entry", json.dumps({"niche": "test niche"})]):
            with patch("investment_pipeline.build_investment_pipeline_entry", return_value={"niche": "test niche"}) as mock_entry:
                result = mission_control_api._get_investment_pipeline_entry()
        mock_entry.assert_called_once_with("test niche")
        self.assertEqual(result["investment_pipeline_entry"]["niche"], "test niche")

    def test_investment_pipeline_forwards_optional_limit(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_investment_pipeline", json.dumps({"limit": 5})]):
            with patch("investment_pipeline.build_investment_pipeline", return_value={"count": 0}) as mock_pipeline:
                mission_control_api._get_investment_pipeline()
        mock_pipeline.assert_called_once_with(limit=5)

    def test_portfolio_actions_are_registered(self):
        for name in ("get_portfolio_entry", "get_portfolio_report"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_portfolio_entry_requires_a_niche(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_portfolio_entry", json.dumps({})]):
            with self.assertRaises(ValueError):
                mission_control_api._get_portfolio_entry()

    def test_portfolio_entry_delegates_to_the_real_module(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_portfolio_entry", json.dumps({"niche": "test niche"})]):
            with patch("portfolio_engine.build_portfolio_entry", return_value={"niche": "test niche"}) as mock_entry:
                result = mission_control_api._get_portfolio_entry()
        mock_entry.assert_called_once_with("test niche")
        self.assertEqual(result["portfolio_entry"]["niche"], "test niche")

    def test_portfolio_report_delegates_to_the_real_module(self):
        with patch("portfolio_engine.build_portfolio_report", return_value={"total_real_opportunities": 0}) as mock_report:
            result = mission_control_api._get_portfolio_report()
        mock_report.assert_called_once_with()
        self.assertEqual(result["total_real_opportunities"], 0)

    def test_production_factory_actions_are_registered(self):
        for name in ("get_production_blueprint", "get_production_missions_board"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_production_blueprint_requires_a_niche(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_production_blueprint", json.dumps({})]):
            with self.assertRaises(ValueError):
                mission_control_api._get_production_blueprint()

    def test_production_blueprint_delegates_to_the_real_module(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_production_blueprint", json.dumps({"niche": "test niche"})]):
            with patch("production_blueprint.build_production_blueprint", return_value={"niche": "test niche"}) as mock_bp:
                result = mission_control_api._get_production_blueprint()
        mock_bp.assert_called_once_with("test niche")
        self.assertEqual(result["production_blueprint"]["niche"], "test niche")

    def test_production_missions_board_delegates_to_the_real_module(self):
        with patch("production_blueprint.build_production_missions_board", return_value={"counts": {}}) as mock_board:
            result = mission_control_api._get_production_missions_board()
        mock_board.assert_called_once_with()
        self.assertEqual(result["counts"], {})

    def test_master_loop_actions_are_registered(self):
        for name in ("get_lifecycle_trace", "get_mission_control_heartbeat"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_lifecycle_trace_requires_a_niche(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_lifecycle_trace", json.dumps({})]):
            with self.assertRaises(ValueError):
                mission_control_api._get_lifecycle_trace()

    def test_lifecycle_trace_delegates_to_the_real_module(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_lifecycle_trace", json.dumps({"niche": "test niche"})]):
            with patch("master_loop.trace_lifecycle", return_value={"niche": "test niche"}) as mock_trace:
                result = mission_control_api._get_lifecycle_trace()
        mock_trace.assert_called_once_with("test niche")
        self.assertEqual(result["lifecycle_trace"]["niche"], "test niche")

    def test_mission_control_heartbeat_delegates_to_the_real_module(self):
        with patch("master_loop.mission_control_heartbeat", return_value={"current_opportunity": None}) as mock_hb:
            result = mission_control_api._get_mission_control_heartbeat()
        mock_hb.assert_called_once_with()
        self.assertIsNone(result["current_opportunity"])

    def test_company_reality_score_action_is_registered(self):
        self.assertIn("get_company_reality_score", mission_control_api._ENDPOINTS)

    def test_company_reality_score_delegates_to_the_real_module(self):
        with patch("reality_mode.compute_company_reality_score", return_value={"score_pct": None}) as mock_score:
            result = mission_control_api._get_company_reality_score()
        mock_score.assert_called_once_with()
        self.assertIsNone(result["score_pct"])

    def test_ceo_decision_center_actions_are_registered(self):
        for name in ("get_ceo_questions", "get_capital_allocation_snapshot", "get_ceo_dashboard"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_ceo_questions_delegates_to_the_real_module(self):
        with patch("ceo_decision_center.answer_ceo_questions", return_value={"1_most_profitable_opportunity_now": None}) as mock_q:
            result = mission_control_api._get_ceo_questions()
        mock_q.assert_called_once_with()
        self.assertIsNone(result["1_most_profitable_opportunity_now"])

    def test_capital_allocation_snapshot_delegates_to_the_real_module(self):
        with patch("ceo_decision_center.capital_allocation_snapshot", return_value={"Research": {}}) as mock_alloc:
            result = mission_control_api._get_capital_allocation_snapshot()
        mock_alloc.assert_called_once_with()
        self.assertEqual(result["Research"], {})

    def test_ceo_dashboard_delegates_to_the_real_module(self):
        with patch("ceo_decision_center.ceo_dashboard", return_value={"current_strategic_priority": None}) as mock_dash:
            result = mission_control_api._get_ceo_dashboard()
        mock_dash.assert_called_once_with()
        self.assertIsNone(result["current_strategic_priority"])

    def test_build_in_public_actions_are_registered(self):
        for name in ("get_weekly_progress_report", "draft_adr_post", "queue_draft_for_approval"):
            self.assertIn(name, mission_control_api._ENDPOINTS)

    def test_weekly_progress_report_delegates_to_the_real_module(self):
        with patch("build_in_public.build_weekly_progress_report", return_value={"scored": 0}) as mock_report:
            result = mission_control_api._get_weekly_progress_report()
        mock_report.assert_called_once_with()
        self.assertEqual(result["scored"], 0)

    def test_draft_adr_post_requires_an_adr_path(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "draft_adr_post", json.dumps({})]):
            with self.assertRaises(ValueError):
                mission_control_api._draft_adr_post()

    def test_draft_adr_post_delegates_to_the_real_module(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "draft_adr_post", json.dumps({"adr_path": "x.md"})]):
            with patch("build_in_public.draft_adr_post", return_value={"draft_text": "d"}) as mock_draft:
                result = mission_control_api._draft_adr_post()
        mock_draft.assert_called_once_with("x.md")
        self.assertEqual(result["draft_text"], "d")

    def test_queue_draft_for_approval_requires_all_fields(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "queue_draft_for_approval", json.dumps({"draft_type": "x"})]):
            with self.assertRaises(ValueError):
                mission_control_api._queue_draft_for_approval()

    def test_queue_draft_for_approval_delegates_to_the_real_module(self):
        payload = {"draft_type": "weekly_report", "title": "t", "content_markdown": "c", "telegram_summary_arabic": "s"}
        with patch.object(sys, "argv", ["mission_control_api.py", "queue_draft_for_approval", json.dumps(payload)]):
            with patch("build_in_public.queue_draft_for_approval", return_value={"draft_path": "p"}) as mock_queue:
                result = mission_control_api._queue_draft_for_approval()
        mock_queue.assert_called_once_with("weekly_report", "t", "c", "s")
        self.assertEqual(result["draft_path"], "p")

    def test_commercial_intelligence_report_requires_a_niche(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_commercial_intelligence_report", json.dumps({})]):
            with self.assertRaises(ValueError):
                mission_control_api._get_commercial_intelligence_report()

    def test_commercial_intelligence_report_delegates_to_the_real_module(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_commercial_intelligence_report", json.dumps({"niche": "test niche"})]):
            with patch("commercial_intelligence.build_commercial_intelligence_report", return_value={"niche": "test niche"}) as mock_report:
                result = mission_control_api._get_commercial_intelligence_report()
        mock_report.assert_called_once_with("test niche")
        self.assertEqual(result["commercial_intelligence"]["niche"], "test niche")

    def test_premium_product_catalog_status_delegates_to_growth_engine(self):
        with patch("growth_engine.premium_product_catalog_status", return_value={"categories": {}}) as mock_status:
            result = mission_control_api._get_premium_product_catalog_status()
        mock_status.assert_called_once_with()
        self.assertEqual(result["categories"], {})

    def test_growth_report_requires_a_niche(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_growth_report", json.dumps({})]):
            with self.assertRaises(ValueError):
                mission_control_api._get_growth_report()

    def test_growth_report_delegates_to_growth_engine(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_growth_report", json.dumps({"niche": "test niche"})]):
            with patch("growth_engine.build_growth_report", return_value={"niche": "test niche"}) as mock_report:
                result = mission_control_api._get_growth_report()
        mock_report.assert_called_once_with("test niche")
        self.assertEqual(result["growth_report"]["niche"], "test niche")

    def test_channel_expansion_status_delegates_to_growth_engine(self):
        with patch("growth_engine.evaluate_channel_expansion", return_value={"live_arms": [], "catalog_entries": []}) as mock_eval:
            result = mission_control_api._get_channel_expansion_status()
        mock_eval.assert_called_once_with()
        self.assertEqual(result["live_arms"], [])

    def test_niche_commercial_profile_requires_a_niche(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_niche_commercial_profile", json.dumps({})]):
            with self.assertRaises(ValueError):
                mission_control_api._get_niche_commercial_profile()

    def test_niche_commercial_profile_delegates_to_market_memory(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "get_niche_commercial_profile", json.dumps({"niche": "test niche"})]):
            with patch("market_memory.niche_commercial_profile", return_value={"niche": "test niche", "sample_size": 0}) as mock_profile:
                result = mission_control_api._get_niche_commercial_profile()
        mock_profile.assert_called_once_with("test niche")
        self.assertEqual(result["commercial_profile"]["sample_size"], 0)

    def test_monthly_market_evolution_report_delegates_to_market_memory(self):
        with patch("market_memory.monthly_evolution_report", return_value={"maturity": "DISCOVERY"}) as mock_report:
            result = mission_control_api._get_monthly_market_evolution_report()
        mock_report.assert_called_once_with()
        self.assertEqual(result["maturity"], "DISCOVERY")

    def test_commercial_recommendations_delegates_to_market_memory(self):
        with patch("market_memory.recommend_actions", return_value={"maturity": "DISCOVERY", "recommendations": []}) as mock_recs:
            result = mission_control_api._get_commercial_recommendations()
        mock_recs.assert_called_once_with()
        self.assertEqual(result["recommendations"], [])

    def test_global_execution_view_assembles_every_real_source_never_recomputes(self):
        """Autonomous Global Execution Engine (2026-07-23): confirms
        every field comes from an already-real function call, not a
        second competing computation -- each source mocked distinctly
        so a wrong wiring would fail this test."""
        with patch.object(sys, "argv", ["mission_control_api.py", "get_global_execution_view"]), \
             patch("execution_status.build_execution_status_report", return_value={"count": 0, "opportunities": []}) as m_exec, \
             patch("scheduler.decide_next_actions", return_value={"counts": {}}) as m_sched, \
             patch("market_memory.monthly_evolution_report", return_value={"maturity": "DISCOVERY"}) as m_monthly, \
             patch("market_memory.recommend_actions", return_value={"recommendations": []}) as m_recs, \
             patch("growth_engine.portfolio_growth_summary", return_value={"total_accepted_opportunities": 0}) as m_growth, \
             patch("growth_engine.production_capacity_summary", return_value={"real_productions_in_window": 0}) as m_capacity, \
             patch("growth_engine.growth_forecast", return_value={"maturity": "DISCOVERY", "forecast": None}) as m_forecast, \
             patch("ai_capability.registry.list_providers", return_value=[]) as m_providers, \
             patch("ai_capability.orchestrator.resource_allocation_status", return_value={}) as m_alloc, \
             patch.object(mission_control_api, "_revenue", return_value={"real": "revenue"}) as m_rev, \
             patch.object(mission_control_api, "_production", return_value={"real": "production"}) as m_prod:
            result = mission_control_api._get_global_execution_view()

        m_exec.assert_called_once_with(limit=None)
        m_sched.assert_called_once_with()
        m_monthly.assert_called_once_with()
        m_recs.assert_called_once_with()
        m_growth.assert_called_once_with()
        m_capacity.assert_called_once_with()
        m_forecast.assert_called_once_with()
        m_providers.assert_called_once_with()
        m_alloc.assert_called_once_with()
        m_rev.assert_called_once_with()
        m_prod.assert_called_once_with()
        self.assertEqual(result["revenue"], {"real": "revenue"})
        self.assertEqual(result["production"], {"real": "production"})
        self.assertEqual(result["portfolio_growth"]["total_accepted_opportunities"], 0)
        self.assertEqual(result["growth_forecast"]["maturity"], "DISCOVERY")
        self.assertIn("note", result)

    def test_global_execution_view_forwards_an_optional_limit_to_execution_status(self):
        """Autonomous Global Commercial Company Layer (2026-07-24): the
        real scale valve, forwarded through -- scheduling stays
        unlimited regardless."""
        with patch.object(sys, "argv", ["mission_control_api.py", "get_global_execution_view", json.dumps({"limit": 5})]), \
             patch("execution_status.build_execution_status_report", return_value={"count": 0, "opportunities": []}) as m_exec, \
             patch("scheduler.decide_next_actions", return_value={"counts": {}}), \
             patch("market_memory.monthly_evolution_report", return_value={"maturity": "DISCOVERY"}), \
             patch("market_memory.recommend_actions", return_value={"recommendations": []}), \
             patch("growth_engine.portfolio_growth_summary", return_value={}), \
             patch("growth_engine.production_capacity_summary", return_value={}), \
             patch("growth_engine.growth_forecast", return_value={}), \
             patch("ai_capability.registry.list_providers", return_value=[]), \
             patch("ai_capability.orchestrator.resource_allocation_status", return_value={}), \
             patch.object(mission_control_api, "_revenue", return_value={}), \
             patch.object(mission_control_api, "_production", return_value={}):
            mission_control_api._get_global_execution_view()
        m_exec.assert_called_once_with(limit=5)


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


class TestEvolutionQueueEndpoints(unittest.TestCase):
    """Autonomous Company Evolution Engine, Round 6 (2026-07-29): the
    dispatch layer for the Evolution Queue -- daily intake/simulate/decide,
    read-only queue view, and the three founder-only approve/reject/
    mark-implemented actions. Every real state mutation is mocked here;
    evolution_queue.py's own logic has its own isolated unit tests in
    tests/test_evolution_queue.py."""

    def test_evolution_queue_daily_cycle_delegates_to_real_proposals_and_queue(self):
        with patch("tool_intelligence.proposals.list_proposals", return_value=[{"id": "p1"}]) as mock_props:
            with patch("evolution_queue.run_daily_cycle", return_value={"added_count": 1, "processed": ["p1"]}) as mock_cycle:
                result = mission_control_api._evolution_queue_daily_cycle()
        mock_props.assert_called_once_with()
        mock_cycle.assert_called_once_with(proposals=[{"id": "p1"}])
        self.assertEqual(result["added_count"], 1)

    def test_evolution_queue_is_a_passthrough(self):
        fake_queue = {"stage_distribution": {}, "awaiting_approval": [], "entries": []}
        with patch("evolution_queue.list_evolution_queue", return_value=fake_queue) as mock_list:
            result = mission_control_api._evolution_queue()
        mock_list.assert_called_once_with()
        self.assertEqual(result, fake_queue)

    def test_approve_evolution_proposal_requires_a_proposal_id(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "approve_evolution_proposal", json.dumps({})]):
            with self.assertRaises(ValueError):
                mission_control_api._approve_evolution_proposal()

    def test_approve_evolution_proposal_delegates_with_founder_as_decided_by(self):
        payload = {"proposal_id": "p1", "note": "looks good"}
        with patch.object(sys, "argv", ["mission_control_api.py", "approve_evolution_proposal", json.dumps(payload)]):
            with patch("evolution_queue.approve_proposal", return_value={"success": True, "stage": "APPROVED"}) as mock_approve:
                result = mission_control_api._approve_evolution_proposal()
        mock_approve.assert_called_once_with("p1", decided_by="founder", note="looks good")
        self.assertEqual(result["stage"], "APPROVED")

    def test_reject_evolution_proposal_requires_a_proposal_id(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "reject_evolution_proposal", json.dumps({})]):
            with self.assertRaises(ValueError):
                mission_control_api._reject_evolution_proposal()

    def test_reject_evolution_proposal_delegates_with_founder_as_decided_by(self):
        payload = {"proposal_id": "p1", "reason": "not worth it"}
        with patch.object(sys, "argv", ["mission_control_api.py", "reject_evolution_proposal", json.dumps(payload)]):
            with patch("evolution_queue.reject_proposal", return_value={"success": True, "stage": "REJECTED"}) as mock_reject:
                result = mission_control_api._reject_evolution_proposal()
        mock_reject.assert_called_once_with("p1", decided_by="founder", reason="not worth it")
        self.assertEqual(result["stage"], "REJECTED")

    def test_mark_evolution_proposal_implemented_requires_a_proposal_id(self):
        with patch.object(sys, "argv", ["mission_control_api.py", "mark_evolution_proposal_implemented", json.dumps({})]):
            with self.assertRaises(ValueError):
                mission_control_api._mark_evolution_proposal_implemented()

    def test_mark_evolution_proposal_implemented_delegates(self):
        payload = {"proposal_id": "p1", "note": "shipped in commit abc123"}
        with patch.object(sys, "argv", ["mission_control_api.py", "mark_evolution_proposal_implemented", json.dumps(payload)]):
            with patch("evolution_queue.mark_implemented", return_value={"success": True, "stage": "IMPLEMENTED"}) as mock_mark:
                result = mission_control_api._mark_evolution_proposal_implemented()
        mock_mark.assert_called_once_with("p1", note="shipped in commit abc123")
        self.assertEqual(result["stage"], "IMPLEMENTED")


if __name__ == "__main__":
    unittest.main()
