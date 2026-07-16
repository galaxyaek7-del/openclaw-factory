"""Tests for validation_layer/ (ADR-053).

Runs with stdlib unittest. Every function reads only from temp-file-
isolated stores passed explicitly — never the real data/*.jsonl files.

    python -m unittest tests.test_validation_layer -v
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

from decision_engine import store as decision_store
from decision_engine.types import Decision, Outcome, make_decision_id
from orchestrator import timeline as orch_timeline
from orchestrator.orchestrator import make_idempotency_key
from orchestrator.types import ExecutionResult

from validation_layer import daily_report, durations, lifecycle, reliability, stalled


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _decision(niche, status, score=80, decided_at=None, tier="tier4"):
    decided_at = decided_at or datetime.now(timezone.utc).isoformat()
    return Decision(
        decision_id=make_decision_id(niche, tier, decided_at), niche=niche, tier=tier,
        decided_at=decided_at, status=status, ai_ceo_decision="BUILD" if status == "ACCEPTED" else "WAIT",
        opportunity_score=score, opportunity_score_accepted=(status == "ACCEPTED"),
        reasoning=["real evidence"], evaluation_snapshot={},
    )


def _exec_result(engine, niche, tier, status, started_at, finished_at, error=None):
    key = make_idempotency_key(engine, niche, tier)
    return ExecutionResult(
        engine=engine, status=status, started_at=started_at, finished_at=finished_at,
        attempts=1, idempotency_key=key, output={}, error=error,
    )


class TestLifecycleReconstruction(unittest.TestCase):
    def setUp(self):
        self.timeline_path = _temp_path()
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.timeline_path, self.decisions_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

    def test_never_seen_niche_reports_honestly_not_reached(self):
        lc = lifecycle.build_lifecycle("never seen niche", timeline_path=self.timeline_path,
                                        decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertIsNone(lc["signal"]["at"])
        self.assertEqual(lc["analysis"], [])
        self.assertEqual(lc["production"], [])

    def test_full_pipeline_reconstructs_every_real_stage_in_order(self):
        niche = "a full lifecycle test niche"
        orch_timeline.append_execution(
            _exec_result("market_intelligence", niche, "tier4", "SUCCESS", "2026-07-16T10:00:00+00:00", "2026-07-16T10:00:02+00:00"),
            path=self.timeline_path,
        )
        orch_timeline.append_execution(
            _exec_result("decision", niche, "tier4", "SUCCESS", "2026-07-16T10:00:02+00:00", "2026-07-16T10:00:03+00:00"),
            path=self.timeline_path,
        )
        orch_timeline.append_execution(
            _exec_result("production", niche, "tier4", "SUCCESS", "2026-07-16T10:05:00+00:00", "2026-07-16T10:06:00+00:00"),
            path=self.timeline_path,
        )
        decision_store.append_decision(_decision(niche, "ACCEPTED", decided_at="2026-07-16T10:00:03+00:00"), path=self.decisions_path)
        decision_id = make_decision_id(niche, "tier4", "2026-07-16T10:00:03+00:00")
        decision_store.append_outcome(
            Outcome(outcome_id="o1", decision_id=decision_id, niche=niche, recorded_at="2026-07-16T11:00:00+00:00",
                    matched=True, match_method="test", raw_sale_event={"id": "s1"}),
            path=self.outcomes_path,
        )

        lc = lifecycle.build_lifecycle(niche, timeline_path=self.timeline_path,
                                        decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertEqual(lc["signal"]["at"], "2026-07-16T10:00:00+00:00")
        self.assertEqual(len(lc["analysis"]), 1)
        self.assertEqual(lc["analysis"][0]["duration_seconds"], 2.0)
        self.assertEqual(len(lc["decision"]), 1)
        self.assertEqual(len(lc["production"]), 1)
        self.assertEqual(len(lc["queue"]), 1)
        self.assertEqual(len(lc["revenue"]), 1)
        self.assertEqual(lc["publishing"], [])  # never ran — honestly empty, not guessed


class TestStageDurations(unittest.TestCase):
    def setUp(self):
        self.timeline_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.timeline_path):
            os.remove(self.timeline_path)

    def test_no_executions_is_discovery(self):
        result = durations.compute_stage_durations(timeline_path=self.timeline_path)
        for stage, d in result.items():
            self.assertEqual(d["maturity"], "DISCOVERY")

    def test_real_durations_are_averaged_correctly(self):
        orch_timeline.append_execution(
            _exec_result("decision", "x", "tier4", "SUCCESS", "2026-07-16T10:00:00+00:00", "2026-07-16T10:00:02+00:00"),
            path=self.timeline_path,
        )
        orch_timeline.append_execution(
            _exec_result("decision", "y", "tier4", "SUCCESS", "2026-07-16T10:00:00+00:00", "2026-07-16T10:00:04+00:00"),
            path=self.timeline_path,
        )
        result = durations.compute_stage_durations(timeline_path=self.timeline_path)
        self.assertEqual(result["decision"]["maturity"], "REAL")
        self.assertEqual(result["decision"]["average_seconds"], 3.0)
        self.assertEqual(result["decision"]["sample_size"], 2)

    def test_skipped_executions_are_excluded_from_duration_average(self):
        orch_timeline.append_execution(
            _exec_result("production", "x", "tier4", "SKIPPED_NOT_APPLICABLE", "2026-07-16T10:00:00+00:00", "2026-07-16T10:00:00+00:00"),
            path=self.timeline_path,
        )
        result = durations.compute_stage_durations(timeline_path=self.timeline_path)
        self.assertEqual(result["production"]["maturity"], "DISCOVERY")


class TestStalledOpportunities(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.timeline_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.timeline_path):
            if os.path.exists(p):
                os.remove(p)

    def test_accepted_with_no_production_success_is_flagged_stalled(self):
        decision_store.append_decision(_decision("stalled niche", "ACCEPTED"), path=self.decisions_path)
        result = stalled.detect_stalled_opportunities(decisions_path=self.decisions_path, timeline_path=self.timeline_path)
        self.assertTrue(result["detected"])
        self.assertEqual(result["items"][0]["niche"], "stalled niche")

    def test_accepted_with_real_production_success_is_not_flagged(self):
        decision_store.append_decision(_decision("produced niche", "ACCEPTED"), path=self.decisions_path)
        orch_timeline.append_execution(
            _exec_result("production", "produced niche", "tier4", "SUCCESS", "t1", "t2"),
            path=self.timeline_path,
        )
        result = stalled.detect_stalled_opportunities(decisions_path=self.decisions_path, timeline_path=self.timeline_path)
        self.assertFalse(result["detected"])

    def test_rejected_decisions_are_never_flagged_as_stalled(self):
        decision_store.append_decision(_decision("rejected niche", "REJECTED"), path=self.decisions_path)
        result = stalled.detect_stalled_opportunities(decisions_path=self.decisions_path, timeline_path=self.timeline_path)
        self.assertFalse(result["detected"])


class TestReliabilityStatistics(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.timeline_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.outcomes_path, self.timeline_path):
            if os.path.exists(p):
                os.remove(p)

    def test_zero_data_never_fabricates_a_statistic(self):
        result = reliability.compute_reliability_statistics(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path, timeline_path=self.timeline_path,
        )
        self.assertEqual(result["decision_accuracy"]["accuracy"], None)
        self.assertEqual(result["bottleneck_frequency"], {})

    def test_bottleneck_frequency_tallies_by_type(self):
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        decision_store.append_decision(_decision("aging niche 1", "ACCEPTED", decided_at=old), path=self.decisions_path)
        decision_store.append_decision(_decision("aging niche 2", "ACCEPTED", decided_at=old), path=self.decisions_path)
        result = reliability.compute_reliability_statistics(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path, timeline_path=self.timeline_path,
        )
        self.assertEqual(result["bottleneck_frequency"].get("queue_aging"), 2)


class TestDailyReport(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.timeline_path = _temp_path()
        self.sales_ledger_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.outcomes_path, self.timeline_path, self.sales_ledger_path):
            if os.path.exists(p):
                os.remove(p)

    def test_report_has_every_required_field(self):
        r = daily_report.generate_daily_report(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path,
        )
        for key in (
            "opportunities_discovered", "opportunities_accepted", "opportunities_rejected",
            "production_completed", "publication_completed", "revenue_generated",
            "failures", "bottlenecks", "recommendations",
        ):
            self.assertIn(key, r)

    def test_failures_carry_exact_reason_and_source_engine(self):
        orch_timeline.append_execution(
            _exec_result("production", "x", "tier4", "FAILED", "t1", "t2", error="subprocess timed out"),
            path=self.timeline_path,
        )
        r = daily_report.generate_daily_report(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path,
        )
        self.assertEqual(len(r["failures"]), 1)
        self.assertEqual(r["failures"][0]["engine"], "production")
        self.assertEqual(r["failures"][0]["reason"], "subprocess timed out")

    def test_revenue_generated_only_counts_real_matched_outcomes(self):
        decision_store.append_outcome(
            Outcome(outcome_id="o1", decision_id="d1", niche="n1", recorded_at="t", matched=True, match_method="x", raw_sale_event={}),
            path=self.outcomes_path,
        )
        decision_store.append_outcome(
            Outcome(outcome_id="o2", decision_id=None, niche=None, recorded_at="t", matched=False, match_method="unmatched", raw_sale_event={}),
            path=self.outcomes_path,
        )
        r = daily_report.generate_daily_report(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path,
        )
        self.assertEqual(r["revenue_generated"], 1)

    def test_recommendations_are_never_generic_without_evidence(self):
        r = daily_report.generate_daily_report(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path,
        )
        for rec in r["recommendations"]:
            self.assertIn("evidence", rec)
            self.assertTrue(len(rec["evidence"]) > 0)

    def test_markdown_renders_without_error(self):
        r = daily_report.generate_daily_report(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path,
        )
        md = daily_report.render_markdown(r)
        self.assertIsInstance(md, str)
        self.assertGreater(len(md), 100)


if __name__ == "__main__":
    unittest.main()
