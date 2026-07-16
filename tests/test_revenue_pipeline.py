"""Tests for revenue_pipeline/ (Phase 6).

Runs with stdlib unittest. No test here ever sets execute=True against
real infrastructure without mocking the underlying subprocess/inspection
calls — nothing here spends real money or touches a real file.

    python -m unittest tests.test_revenue_pipeline -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from decision_engine import store
from decision_engine.types import Decision, make_decision_id

from revenue_pipeline import pipeline, plan


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _accepted_decision(niche="a revenue pipeline test niche", price_str="$19"):
    decided_at = "2026-07-16T10:00:00+00:00"
    return Decision(
        decision_id=make_decision_id(niche, "tier4", decided_at), niche=niche, tier="tier4",
        decided_at=decided_at, status="ACCEPTED", ai_ceo_decision="BUILD",
        opportunity_score=80.0, opportunity_score_accepted=True,
        reasoning=["real evidence"],
        evaluation_snapshot={"pricing": {"recommended_price": price_str, "note": "x"}},
    )


class TestBuildProductionPlan(unittest.TestCase):
    def test_plan_extracts_real_recommended_price(self):
        d = _accepted_decision(price_str="$24.99")
        result = plan.build_production_plan(d.to_dict())
        self.assertEqual(result["recommended_price"], 24.99)

    def test_plan_handles_missing_price_honestly(self):
        d = _accepted_decision()
        d_dict = d.to_dict()
        d_dict["evaluation_snapshot"] = {}
        result = plan.build_production_plan(d_dict)
        self.assertIsNone(result["recommended_price"])


class TestEstimateProductionCost(unittest.TestCase):
    def test_no_logged_cost_is_discovery(self):
        result = plan.estimate_production_cost(log_file="/no/such/ai_cost_log.jsonl")
        self.assertEqual(result["maturity"], "DISCOVERY")

    def test_real_logged_cost_is_used(self):
        import json
        path = _temp_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"cost_usd": 0.02}) + "\n")
                f.write(json.dumps({"cost_usd": 0.04}) + "\n")
            result = plan.estimate_production_cost(log_file=path)
            self.assertEqual(result["maturity"], "REAL")
            self.assertAlmostEqual(result["estimated_cost_usd"], 0.03, places=6)
            self.assertEqual(result["sample_size"], 2)
        finally:
            if os.path.exists(path):
                os.remove(path)


class TestEstimateRoi(unittest.TestCase):
    def test_missing_price_is_discovery(self):
        result = plan.estimate_roi(None, 0.02)
        self.assertEqual(result["maturity"], "DISCOVERY")

    def test_missing_cost_is_discovery(self):
        result = plan.estimate_roi(19.0, None)
        self.assertEqual(result["maturity"], "DISCOVERY")

    def test_real_price_and_cost_produce_a_real_roi(self):
        result = plan.estimate_roi(19.0, 0.02)
        self.assertEqual(result["maturity"], "REAL")
        self.assertIn("roi_pct", result)
        self.assertIn("net_profit_after_fees", result)
        # sanity: a $19 digital product's net profit should vastly exceed a $0.02 AI cost
        self.assertGreater(result["roi_pct"], 0)


class TestRunRevenuePipeline(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.timeline_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.analysis_db_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.timeline_path, self.outcomes_path, self.analysis_db_path):
            if os.path.exists(p):
                os.remove(p)

    def test_no_accepted_opportunities_reports_honestly(self):
        result = pipeline.run_revenue_pipeline(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertEqual(result["processed"], 0)
        self.assertIn("reason", result)

    def test_default_never_executes_real_production(self):
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        result = pipeline.run_revenue_pipeline(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path, timeline_path=self.timeline_path,
        )
        self.assertEqual(result["processed"], 1)
        self.assertFalse(result["results"][0]["executed"])
        self.assertEqual(result["results"][0]["quality_validation"]["maturity"], "DISCOVERY")

    def test_accepted_opportunity_produces_a_full_result_shape(self):
        d = _accepted_decision(price_str="$19")
        store.append_decision(d, path=self.decisions_path)
        result = pipeline.run_revenue_pipeline(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path, timeline_path=self.timeline_path,
        )
        r = result["results"][0]
        for key in ("production_plan", "quality_validation", "business_lifecycle",
                    "time_to_market", "production_cost", "expected_roi"):
            self.assertIn(key, r)

    def test_ceo_report_renders_without_error_for_empty_queue(self):
        result = pipeline.run_revenue_pipeline(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        report = pipeline.render_ceo_revenue_report(result)
        self.assertIn("لا نشاط إيراد اليوم", report)

    def test_ceo_report_renders_without_error_for_a_real_accepted_opportunity(self):
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        result = pipeline.run_revenue_pipeline(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path, timeline_path=self.timeline_path,
        )
        report = pipeline.render_ceo_revenue_report(result)
        self.assertIn(d.niche, report)

    @patch("orchestrator.orchestrator.run_cycle")
    def test_execute_true_calls_the_real_orchestrator_with_execute_production_true(self, mock_run_cycle):
        mock_run_cycle.return_value = []
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        pipeline.run_revenue_pipeline(
            execute=True, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, analysis_db_file=self.analysis_db_path,
        )
        self.assertTrue(mock_run_cycle.called)
        self.assertTrue(mock_run_cycle.call_args.kwargs["execute_production"])


if __name__ == "__main__":
    unittest.main()
