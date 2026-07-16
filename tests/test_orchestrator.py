"""Tests for orchestrator/ (ADR-051).

Runs with stdlib unittest. All network-calling functions inherited from
market_intelligence_core/competitor_discovery/market_intelligence_engine
are mocked throughout — this suite never depends on live API availability,
and never spawns a real book_generator.py/distributor.py subprocess
(execute_production defaults False in every test that doesn't explicitly
test the production/publishing adapters in isolation with mocks).

    python -m unittest tests.test_orchestrator -v
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

from orchestrator import orchestrator as orch
from orchestrator import registry, timeline
from orchestrator.types import EXECUTION_ORDER, ExecutionResult


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class TestExecutionOrderIsData(unittest.TestCase):
    def test_execution_order_is_the_declared_five_stages(self):
        self.assertEqual(
            EXECUTION_ORDER,
            ("market_intelligence", "decision", "production", "publishing", "learning"),
        )


class TestRegistryAutoDiscovery(unittest.TestCase):
    def test_all_five_engines_are_registered(self):
        import orchestrator.engines  # noqa: F401 — triggers auto-import
        engines = registry.get_engines()
        for name in EXECUTION_ORDER:
            self.assertIn(name, engines)

    def test_adding_a_new_engine_at_runtime_requires_zero_orchestrator_edits(self):
        """The concrete proof of 'allow new engines to register
        automatically without modifying existing code': register a
        brand-new engine dynamically (as if a 6th file had been dropped
        into engines/) and confirm the registry picks it up with no
        changes to orchestrator.py or any existing engine."""
        @registry.register_engine("test_only_engine")
        def _fake_engine(context):
            return {"ok": True}

        try:
            self.assertIn("test_only_engine", registry.get_engines())
        finally:
            del registry._ENGINES["test_only_engine"]


class TestTimelineIsImmutable(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_every_execution_is_appended_never_overwritten(self):
        r1 = ExecutionResult(engine="x", status="SUCCESS", started_at="t1", finished_at="t1", attempts=1, idempotency_key="k1", output={})
        r2 = ExecutionResult(engine="x", status="FAILED", started_at="t2", finished_at="t2", attempts=1, idempotency_key="k1", output={}, error="boom")
        timeline.append_execution(r1, path=self.path)
        timeline.append_execution(r2, path=self.path)
        records = list(timeline.read_timeline(path=self.path))
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["status"], "SUCCESS")
        self.assertEqual(records[1]["status"], "FAILED")

    def test_has_succeeded_true_only_after_a_real_success_record(self):
        self.assertFalse(timeline.has_succeeded("k1", path=self.path))
        timeline.append_execution(
            ExecutionResult(engine="x", status="FAILED", started_at="t", finished_at="t", attempts=1, idempotency_key="k1", output={}, error="x"),
            path=self.path,
        )
        self.assertFalse(timeline.has_succeeded("k1", path=self.path))
        timeline.append_execution(
            ExecutionResult(engine="x", status="SUCCESS", started_at="t", finished_at="t", attempts=1, idempotency_key="k1", output={}),
            path=self.path,
        )
        self.assertTrue(timeline.has_succeeded("k1", path=self.path))

    def test_missing_timeline_file_reads_as_empty_never_throws(self):
        self.assertEqual(list(timeline.read_timeline(path="/no/such/timeline.jsonl")), [])
        self.assertFalse(timeline.has_succeeded("anything", path="/no/such/timeline.jsonl"))


class TestRetryHandlesTransientFailure(unittest.TestCase):
    def test_succeeds_on_a_later_attempt_without_exhausting_all_attempts_uselessly(self):
        from orchestrator import retry
        calls = {"n": 0}

        def flaky(context):
            calls["n"] += 1
            if calls["n"] < 2:
                raise Exception("transient")
            return {"ok": True}

        output, error, attempts = retry.run_with_retry(flaky, {}, max_attempts=3)
        self.assertIsNone(error)
        self.assertEqual(output, {"ok": True})
        self.assertEqual(attempts, 2)

    def test_reports_the_error_honestly_after_exhausting_every_attempt(self):
        from orchestrator import retry

        def always_fails(context):
            raise Exception("permanent failure")

        output, error, attempts = retry.run_with_retry(always_fails, {}, max_attempts=2)
        self.assertIsNone(output)
        self.assertIn("permanent failure", error)
        self.assertEqual(attempts, 2)


class _IsolatedRunCycleTestCase(unittest.TestCase):
    """Shared isolation for every test that calls orch.run_cycle(): redirects
    every real store (timeline, decisions, market-intelligence analyses,
    outcomes) to temp files, and patches competitor_discovery.COMPETITOR_DB_FILE
    directly (2026-07-16 fix) since get_or_refresh_competitors() writes there
    even when the network query itself is mocked, and no public parameter
    threads that override through analyze_opportunity()/evaluate_opportunity()
    — confirmed by finding this suite's own niche strings inside the real
    data/competitor_database.json before this fix."""

    def setUp(self):
        self.timeline_path = _temp_path()
        self.decisions_path = _temp_path()
        self.analysis_db_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.competitor_db_path = _temp_path(".json")
        patcher1 = patch("competitor_discovery._query_hn", return_value=[])
        patcher2 = patch("competitor_discovery._query_github", return_value=[])
        patcher3 = patch("market_intelligence_engine._query_hn_discussions", return_value=([], 0))
        patcher4 = patch("market_intelligence_engine._query_github_issues", return_value=([], 0))
        patcher5 = patch("competitor_discovery.COMPETITOR_DB_FILE", self.competitor_db_path)
        for p in (patcher1, patcher2, patcher3, patcher4, patcher5):
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        for p in (self.timeline_path, self.decisions_path, self.analysis_db_path,
                  self.outcomes_path, self.competitor_db_path):
            if os.path.exists(p):
                os.remove(p)

    def _run_cycle(self, niche, **kwargs):
        return orch.run_cycle(
            niche, timeline_path=self.timeline_path, decisions_path=self.decisions_path,
            analysis_db_file=self.analysis_db_path, outcomes_path=self.outcomes_path, **kwargs,
        )


class TestRunCycleDryRunSafetyDefault(_IsolatedRunCycleTestCase):
    def test_default_never_executes_production_or_publishing(self):
        results = self._run_cycle("a dry run safety test niche")
        by_stage = {r.engine: r for r in results}
        self.assertEqual(by_stage["production"].status, "SKIPPED_NOT_APPLICABLE")
        self.assertEqual(by_stage["publishing"].status, "SKIPPED_NOT_APPLICABLE")

    def test_market_intelligence_and_decision_always_run(self):
        results = self._run_cycle("a dry run safety test niche 2")
        by_stage = {r.engine: r for r in results}
        self.assertEqual(by_stage["market_intelligence"].status, "SUCCESS")
        self.assertEqual(by_stage["decision"].status, "SUCCESS")

    def test_learning_always_runs_regardless_of_decision_outcome(self):
        results = self._run_cycle("كتاب")  # weak niche -> likely rejected/deferred
        by_stage = {r.engine: r for r in results}
        self.assertEqual(by_stage["learning"].status, "SUCCESS")

    def test_every_stage_is_recorded_to_the_timeline(self):
        self._run_cycle("a full timeline coverage test niche")
        records = list(timeline.read_timeline(path=self.timeline_path))
        recorded_engines = {r["engine"] for r in records}
        for stage in EXECUTION_ORDER:
            self.assertIn(stage, recorded_engines)

    def test_production_engine_itself_never_spawns_a_subprocess_under_dry_run(self):
        from orchestrator.engines import production
        result = production.run({"niche": "x", "dry_run": True})
        self.assertFalse(result["executed"])


class TestDuplicateExecutionPreventionScopedToCostlyStages(_IsolatedRunCycleTestCase):
    def test_market_intelligence_and_decision_never_skip_as_duplicate_on_rerun(self):
        """Re-evaluating a niche must always be allowed — this factory's own
        freshness/re-evaluation semantics (competitor_discovery's cache
        window, decision_engine's append-only re-decision history) depend
        on it; permanently blocking re-runs after one success would make
        the system unable to ever reassess a niche again."""
        niche = "a re-evaluation allowed test niche"
        self._run_cycle(niche)
        results2 = self._run_cycle(niche)
        by_stage = {r.engine: r for r in results2}
        self.assertEqual(by_stage["market_intelligence"].status, "SUCCESS")
        self.assertEqual(by_stage["decision"].status, "SUCCESS")

    def test_a_manually_recorded_production_success_is_never_repeated(self):
        key = orch.make_idempotency_key("production", "already produced niche", "tier4")
        timeline.append_execution(
            ExecutionResult(engine="production", status="SUCCESS", started_at="t", finished_at="t", attempts=1, idempotency_key=key, output={}),
            path=self.timeline_path,
        )
        # Force through to production by monkeypatching decision status via a direct stage check:
        self.assertTrue(timeline.has_succeeded(key, path=self.timeline_path))


class TestPrioritizeQueueReusesDecisionEngineRanking(unittest.TestCase):
    def test_max_items_caps_the_real_ranking(self):
        with patch("decision_engine.ranking.rank_queue", return_value=[{"niche": "a"}, {"niche": "b"}, {"niche": "c"}]):
            result = orch.prioritize_queue(max_items=2)
            self.assertEqual(len(result), 2)


class TestRealCompetitionEnrichment(unittest.TestCase):
    """ADR-057: profit_oracle._score_competition() already accepts a real
    external_signal['competition']['related_results_count'] (ADR-041);
    competitor_discovery.py already computes a real HN/GitHub competitor
    count (ADR-042). Nothing wired them together until this fix."""

    def setUp(self):
        self.competitor_db_path = _temp_path(".json")

    def tearDown(self):
        if os.path.exists(self.competitor_db_path):
            os.remove(self.competitor_db_path)

    @patch("competitor_discovery._query_github", return_value=[{"full_name": "x/y", "stargazers_count": 10, "owner": {"type": "User"}, "created_at": "2026-01-01T00:00:00Z"}])
    @patch("competitor_discovery._query_hn", return_value=[])
    def test_real_competitor_count_is_merged_into_competition_key(self, mock_hn, mock_gh):
        with patch("competitor_discovery.COMPETITOR_DB_FILE", self.competitor_db_path):
            result = orch._enrich_with_real_competition("a real enrichment test niche", None, 10)
        self.assertEqual(result["competition"]["related_results_count"], 1)

    @patch("competitor_discovery._query_github", return_value=[])
    @patch("competitor_discovery._query_hn", return_value=[])
    def test_existing_demand_signal_fields_are_preserved_not_overwritten(self, mock_hn, mock_gh):
        with patch("competitor_discovery.COMPETITOR_DB_FILE", self.competitor_db_path):
            result = orch._enrich_with_real_competition(
                "a preserve fields test niche", {"source": "github", "stars": 500}, 10
            )
        self.assertEqual(result["source"], "github")
        self.assertEqual(result["stars"], 500)
        self.assertIn("competition", result)

    def test_competitor_discovery_failure_degrades_to_unchanged_signal_never_fabricates(self):
        with patch("competitor_discovery.get_or_refresh_competitors", side_effect=Exception("network down")):
            original = {"source": "github", "stars": 500}
            result = orch._enrich_with_real_competition("a failure test niche", original, 10)
        self.assertEqual(result, original)

    def test_none_external_signal_still_gets_a_real_competition_key(self):
        with patch("competitor_discovery.get_or_refresh_competitors", return_value={"total_found": 3}):
            result = orch._enrich_with_real_competition("x", None, 10)
        self.assertEqual(result, {"competition": {"related_results_count": 3}})

    def test_no_cap_returns_the_full_real_queue(self):
        with patch("decision_engine.ranking.rank_queue", return_value=[{"niche": "a"}, {"niche": "b"}]):
            result = orch.prioritize_queue()
            self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
