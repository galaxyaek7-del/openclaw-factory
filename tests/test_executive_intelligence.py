"""Tests for executive_intelligence/ (ADR-052).

Runs with stdlib unittest. Every function reads only from temp-file-
isolated stores passed explicitly — never the real data/*.jsonl files.

    python -m unittest tests.test_executive_intelligence -v
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from decision_engine import store
from decision_engine.types import Decision, Outcome, make_decision_id
from orchestrator import timeline as orch_timeline
from orchestrator.types import ExecutionResult

from executive_intelligence import bottlenecks, engine_health, inactivity, opportunities, report


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _decision(niche, status, score=80, decided_at=None):
    decided_at = decided_at or datetime.now(timezone.utc).isoformat()
    return Decision(
        decision_id=make_decision_id(niche, "tier4", decided_at), niche=niche, tier="tier4",
        decided_at=decided_at, status=status, ai_ceo_decision="BUILD" if status == "ACCEPTED" else "WAIT",
        opportunity_score=score, opportunity_score_accepted=(status == "ACCEPTED"),
        reasoning=["real evidence line one", "real evidence line two"], evaluation_snapshot={},
    )


class TestEngineHealth(unittest.TestCase):
    def setUp(self):
        self.timeline_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.timeline_path):
            os.remove(self.timeline_path)

    def test_engine_with_no_executions_is_discovery_not_fabricated_healthy(self):
        health = engine_health.compute_engine_health(timeline_path=self.timeline_path)
        for stage, h in health.items():
            self.assertEqual(h["maturity"], "DISCOVERY")
            self.assertEqual(h["total_executions"], 0)

    def test_engine_with_real_executions_reports_real_success_rate(self):
        orch_timeline.append_execution(
            ExecutionResult(engine="decision", status="SUCCESS", started_at="t1", finished_at="t1", attempts=1, idempotency_key="k1", output={}),
            path=self.timeline_path,
        )
        orch_timeline.append_execution(
            ExecutionResult(engine="decision", status="FAILED", started_at="t2", finished_at="t2", attempts=2, idempotency_key="k2", output={}, error="x"),
            path=self.timeline_path,
        )
        health = engine_health.compute_engine_health(timeline_path=self.timeline_path)
        self.assertEqual(health["decision"]["maturity"], "REAL")
        self.assertEqual(health["decision"]["total_executions"], 2)
        self.assertEqual(health["decision"]["success_rate"], 50.0)


class TestOpportunityTracking(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

    def test_counts_and_reasoning_are_real_and_traceable(self):
        store.append_decision(_decision("accepted niche", "ACCEPTED"), path=self.decisions_path)
        store.append_decision(_decision("rejected niche", "REJECTED"), path=self.decisions_path)
        store.append_decision(_decision("deferred niche", "DEFERRED"), path=self.decisions_path)

        result = opportunities.track_opportunities(decisions_path=self.decisions_path)
        self.assertEqual(result["counts"]["ACCEPTED"], 1)
        self.assertEqual(result["counts"]["REJECTED"], 1)
        self.assertEqual(result["counts"]["DEFERRED"], 1)
        accepted_entry = result["by_status"]["ACCEPTED"][0]
        self.assertEqual(accepted_entry["niche"], "accepted niche")
        self.assertTrue(len(accepted_entry["reasoning"]) > 0)

    def test_no_pending_opportunity_reports_honestly(self):
        result = opportunities.highest_value_pending_opportunity(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertFalse(result["available"])

    def test_highest_value_pending_opportunity_is_the_top_ranked_accepted_one(self):
        store.append_decision(_decision("low score", "ACCEPTED", score=70), path=self.decisions_path)
        store.append_decision(_decision("high score", "ACCEPTED", score=95), path=self.decisions_path)
        result = opportunities.highest_value_pending_opportunity(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertTrue(result["available"])
        self.assertEqual(result["niche"], "high score")


class TestBottleneckDetection(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

    def test_no_data_reports_no_bottleneck_honestly(self):
        result = bottlenecks.detect_bottlenecks({}, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertFalse(result["detected"])

    def test_low_engine_success_rate_is_flagged(self):
        health = {"decision": {"maturity": "REAL", "success_rate": 40.0, "failures": 3, "total_executions": 5}}
        result = bottlenecks.detect_bottlenecks(health, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertTrue(result["detected"])
        self.assertTrue(any(i["type"] == "engine_failure_rate" for i in result["items"]))

    def test_high_engine_success_rate_is_not_flagged(self):
        health = {"decision": {"maturity": "REAL", "success_rate": 95.0, "failures": 1, "total_executions": 20}}
        result = bottlenecks.detect_bottlenecks(health, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertFalse(result["detected"])

    def test_aging_accepted_opportunity_in_queue_is_flagged(self):
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        store.append_decision(_decision("aging niche", "ACCEPTED", decided_at=old), path=self.decisions_path)
        result = bottlenecks.detect_bottlenecks({}, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertTrue(result["detected"])
        self.assertTrue(any(i["type"] == "queue_aging" for i in result["items"]))

    def test_freshly_accepted_opportunity_is_not_flagged_as_aging(self):
        store.append_decision(_decision("fresh niche", "ACCEPTED"), path=self.decisions_path)
        result = bottlenecks.detect_bottlenecks({}, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertFalse(any(i["type"] == "queue_aging" for i in result.get("items", [])))


class TestInactiveComponents(unittest.TestCase):
    def setUp(self):
        self.timeline_path = _temp_path()
        self.sales_ledger_path = _temp_path()

    def tearDown(self):
        for p in (self.timeline_path, self.sales_ledger_path):
            if os.path.exists(p):
                os.remove(p)

    def test_engines_with_no_executions_are_flagged_inactive(self):
        result = inactivity.detect_inactive_components(timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path)
        self.assertTrue(result["detected"])
        component_names = [i["component"] for i in result["items"]]
        self.assertTrue(any("market_intelligence" in c for c in component_names))

    def test_engine_with_a_real_execution_is_not_flagged(self):
        orch_timeline.append_execution(
            ExecutionResult(engine="decision", status="SUCCESS", started_at="t", finished_at="t", attempts=1, idempotency_key="k", output={}),
            path=self.timeline_path,
        )
        result = inactivity.detect_inactive_components(timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path)
        component_names = [i["component"] for i in result["items"]]
        self.assertFalse(any("engine: decision" in c for c in component_names))


class TestFullReportAssembly(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.timeline_path = _temp_path()
        self.sales_ledger_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.outcomes_path, self.timeline_path, self.sales_ledger_path):
            if os.path.exists(p):
                os.remove(p)

    def test_report_has_every_required_section(self):
        r = report.generate_report(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path,
        )
        for key in (
            "generated_at", "engine_health", "opportunities", "highest_value_pending_opportunity",
            "prediction_accuracy", "bottlenecks", "revenue_distance", "inactive_components",
        ):
            self.assertIn(key, r)

    def test_markdown_renders_without_error_and_is_non_trivial(self):
        r = report.generate_report(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path,
        )
        md = report.render_markdown(r)
        self.assertIsInstance(md, str)
        self.assertGreater(len(md), 200)

    def test_zero_real_data_never_fabricates_prediction_accuracy(self):
        r = report.generate_report(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path,
        )
        self.assertIsNone(r["prediction_accuracy"]["accuracy"])

    def test_zero_real_sales_never_fabricates_a_revenue_time_estimate(self):
        r = report.generate_report(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path,
        )
        self.assertEqual(r["revenue_distance"]["maturity"], "DISCOVERY")
        self.assertNotIn("days", r["revenue_distance"])


if __name__ == "__main__":
    unittest.main()
