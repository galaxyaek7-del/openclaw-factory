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


if __name__ == "__main__":
    unittest.main()
