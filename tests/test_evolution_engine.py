"""Tests for evolution_engine.py (EOS Phase 1, 2026-07-19): the Company
Evolution Engine, combining bottleneck detection, technical debt,
high-ROI ranking, capability-gap scanning, and tool proposals.

Runs with stdlib unittest.

    python -m unittest tests.test_evolution_engine -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import evolution_engine as ee


class TestHighRoiOpportunities(unittest.TestCase):
    @patch("revenue_pipeline.pipeline.run_revenue_pipeline")
    def test_no_accepted_opportunities_reports_honestly(self, mock_run):
        mock_run.return_value = {"processed": 0, "results": [], "reason": "no ACCEPTED opportunities"}
        result = ee._high_roi_opportunities()
        self.assertEqual(result["answer"], "Unknown")

    @patch("revenue_pipeline.pipeline.run_revenue_pipeline")
    def test_no_measured_roi_reports_honestly(self, mock_run):
        mock_run.return_value = {
            "processed": 1,
            "results": [{"niche": "n", "expected_roi": {"maturity": "DISCOVERY", "reason": "no cost data"}}],
        }
        result = ee._high_roi_opportunities()
        self.assertEqual(result["answer"], "Unknown")

    @patch("revenue_pipeline.pipeline.run_revenue_pipeline")
    def test_ranks_real_roi_descending(self, mock_run):
        mock_run.return_value = {
            "processed": 2,
            "results": [
                {"niche": "low", "expected_roi": {"maturity": "REAL", "roi_pct": 10, "expected_net_after_cost": 5}},
                {"niche": "high", "expected_roi": {"maturity": "REAL", "roi_pct": 90, "expected_net_after_cost": 50}},
            ],
        }
        result = ee._high_roi_opportunities()
        self.assertEqual(result["top"][0]["niche"], "high")
        self.assertEqual(result["measured_count"], 2)


class TestCustomerSuccessBottleneck(unittest.TestCase):
    """Continuous Improvement (Global Trust & Resilience Layer, Round 7,
    2026-07-29): reuses tool_intelligence.proposals' own real
    customer-funnel signal, never a second bottleneck detector."""

    def test_no_customer_proposal_is_honestly_not_detected(self):
        result = ee._customer_success_bottleneck([{"id": "fix_detected_bottlenecks", "tool": "x", "evidence": "y"}])
        self.assertFalse(result["detected"])

    def test_real_customer_proposal_is_surfaced(self):
        proposals = [{
            "id": "resolve_stuck_customer_requests", "tool": "Resolve 2 real customer request(s) stuck in the funnel",
            "evidence": "customer_pipeline.list_pipeline_overview()'s needs_attention",
        }]
        result = ee._customer_success_bottleneck(proposals)
        self.assertTrue(result["detected"])
        self.assertEqual(result["summary"], proposals[0]["tool"])
        self.assertEqual(result["evidence"], proposals[0]["evidence"])

    def test_empty_proposal_list_is_honestly_not_detected(self):
        result = ee._customer_success_bottleneck([])
        self.assertFalse(result["detected"])


class TestBuildEvolutionReport(unittest.TestCase):
    def test_real_call_against_real_data_never_throws(self):
        report = ee.build_evolution_report()
        for key in ("bottlenecks", "technical_debt", "high_roi_opportunities", "capability_gaps", "tool_proposals", "customer_success_bottleneck"):
            self.assertIn(key, report)

    def test_render_markdown_never_throws_on_real_report(self):
        report = ee.build_evolution_report()
        md = ee.render_markdown(report)
        self.assertIsInstance(md, str)
        self.assertIn("الاختناقات", md)
        self.assertIn("فجوات القدرات", md)


class TestBuildGalaxyEvolutionReport(unittest.TestCase):
    """Company Evolution Protocol V1 (ADR-173, 2026-08-05)."""

    _FAKE_BASE = {
        "generated_at": "2026-08-05T00:00:00Z",
        "bottlenecks": {"detected": False, "items": [], "reason": "x"},
        "technical_debt": {"answer": "Unknown", "reason": "x"},
        "high_roi_opportunities": {"answer": "Unknown", "reason": "x"},
        "capability_gaps": {"discovery_level": [], "estimated_level": [], "total_capabilities": 0},
        "tool_proposals": [],
        "customer_success_bottleneck": {"detected": False, "reason": "x"},
    }
    _FAKE_CAPITAL = {"top_roi_initiatives": [{"niche": "n1", "expected_roi": 12.0}], "opportunity_cost_summary": []}

    def test_never_recomputes_base_evolution_report(self):
        with patch("capital_allocation_engine.build_capital_allocation_dashboard", return_value=self._FAKE_CAPITAL):
            report = ee.build_galaxy_evolution_report(base_report=self._FAKE_BASE)
        self.assertEqual(report["generated_at"], "2026-08-05T00:00:00Z")

    def test_revenue_impact_and_effort_are_honestly_not_measurable(self):
        with patch("capital_allocation_engine.build_capital_allocation_dashboard", return_value=self._FAKE_CAPITAL):
            report = ee.build_galaxy_evolution_report(base_report=self._FAKE_BASE)
        self.assertIn("NOT_MEASURABLE", report["potential_monthly_revenue_impact"])
        self.assertIn("NOT_MEASURABLE", report["estimated_implementation_effort"])

    def test_global_benchmark_is_honestly_not_built(self):
        with patch("capital_allocation_engine.build_capital_allocation_dashboard", return_value=self._FAKE_CAPITAL):
            report = ee.build_galaxy_evolution_report(base_report=self._FAKE_BASE)
        self.assertEqual(report["global_benchmark"]["status"], "NOT_BUILT")

    def test_high_priority_actions_ranked_by_roi_cites_real_capital_data(self):
        with patch("capital_allocation_engine.build_capital_allocation_dashboard", return_value=self._FAKE_CAPITAL):
            report = ee.build_galaxy_evolution_report(base_report=self._FAKE_BASE)
        self.assertEqual(report["high_priority_actions_ranked_by_roi"][0]["initiative"], "n1")
        self.assertEqual(report["high_priority_actions_ranked_by_roi"][0]["expected_roi"], 12.0)

    def test_real_call_against_real_data_never_throws(self):
        report = ee.build_galaxy_evolution_report()
        for key in ("current_strengths", "current_weaknesses", "critical_risks", "hidden_opportunities",
                    "recommended_improvements", "high_priority_actions_ranked_by_roi",
                    "expected_long_term_impact", "potential_monthly_revenue_impact",
                    "estimated_implementation_effort", "global_benchmark"):
            self.assertIn(key, report)


class TestRenderGalaxyEvolutionReportMarkdown(unittest.TestCase):
    def test_renders_all_15_named_sections(self):
        fake_report = {
            "generated_at": "x", "current_strengths": "a", "current_weaknesses": "b",
            "critical_risks": "c", "hidden_opportunities": "d", "recommended_improvements": "e",
            "high_priority_actions_ranked_by_roi": "f", "expected_long_term_impact": "g",
            "potential_monthly_revenue_impact": "h", "estimated_implementation_effort": "i",
            "global_benchmark": "j", "commercial_debt": "k", "strategic_debt": "l",
            "competitive_threats": "m", "never_build": "n", "obsolete_components": "o",
        }
        md = ee.render_galaxy_evolution_report_markdown(fake_report)
        for label in ("Current Strengths", "Current Weaknesses", "Critical Risks", "Hidden Opportunities",
                      "Recommended Improvements", "High Priority Actions", "Expected Long-Term Impact",
                      "Potential Monthly Revenue Impact", "Estimated Implementation Effort", "Global Benchmark",
                      "Commercial Debt", "Strategic Debt", "Competitive Threats", "What Should Never Be Built",
                      "Obsolete Components"):
            self.assertIn(label, md)


class TestAutonomousEvolutionProtocolSections(unittest.TestCase):
    """ADR-187 (2026-08-07): the 4 sections added for the founder's
    Autonomous Evolution Protocol directive."""

    def test_commercial_debt_cites_real_readiness_score(self):
        result = ee._commercial_debt()
        self.assertIn("bottleneck_dimension", result)
        self.assertIn("commercial_readiness.py", result["source"])

    def test_strategic_debt_cites_real_horizons(self):
        result = ee._strategic_debt()
        self.assertIn("value", result)
        self.assertIn("strategic_intelligence_core.py", result["source"])

    def test_competitive_threats_never_triggers_a_live_network_call(self):
        # Real, mechanical proof: patch the only live-network-capable
        # function this module could reach for competitor data and
        # confirm it's never called by a report generation.
        with patch("competitor_discovery.gather_real_metrics") as mock_gather:
            ee._competitive_threats()
            mock_gather.assert_not_called()

    def test_never_build_list_is_static_and_real(self):
        result = ee._never_build_list()
        self.assertGreaterEqual(len(result["items"]), 5)
        for item in result["items"]:
            self.assertIn("decision", item)
            self.assertIn("reason", item)

    def test_full_report_includes_all_4_new_sections(self):
        report = ee.build_galaxy_evolution_report()
        for key in ("commercial_debt", "strategic_debt", "competitive_threats", "never_build"):
            self.assertIn(key, report)


class TestObsoleteComponents(unittest.TestCase):
    """ADR-193 (2026-08-07): closes MONTHLY_EVOLUTION_REPORT.md's own
    disclosed gap -- "what should be removed" now cites
    enterprise_validation.py::detect_unused_services() directly."""

    def test_cites_real_detect_unused_services(self):
        result = ee._obsolete_components()
        self.assertIn("source", result)
        self.assertIn("detect_unused_services", result["source"])

    def test_full_report_includes_obsolete_components(self):
        report = ee.build_galaxy_evolution_report()
        self.assertIn("obsolete_components", report)


if __name__ == "__main__":
    unittest.main()
