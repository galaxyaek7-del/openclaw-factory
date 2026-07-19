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


class TestBuildEvolutionReport(unittest.TestCase):
    def test_real_call_against_real_data_never_throws(self):
        report = ee.build_evolution_report()
        for key in ("bottlenecks", "technical_debt", "high_roi_opportunities", "capability_gaps", "tool_proposals"):
            self.assertIn(key, report)

    def test_render_markdown_never_throws_on_real_report(self):
        report = ee.build_evolution_report()
        md = ee.render_markdown(report)
        self.assertIsInstance(md, str)
        self.assertIn("الاختناقات", md)
        self.assertIn("فجوات القدرات", md)


if __name__ == "__main__":
    unittest.main()
