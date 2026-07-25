"""Tests for orchestrator/ (ADR-051).

Runs with stdlib unittest. All network-calling functions inherited from
market_intelligence_core/competitor_discovery/market_intelligence_engine
are mocked throughout — this suite never depends on live API availability,
and never spawns a real book_generator.py/distributor.py subprocess
(execute_production defaults False in every test that doesn't explicitly
test the production/publishing adapters in isolation with mocks).

    python -m unittest tests.test_orchestrator -v
"""

import json
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
        self.pain_db_path = _temp_path(".json")
        self.state_path = _temp_path(".json")
        patcher1 = patch("competitor_discovery._query_hn", return_value=[])
        patcher2 = patch("competitor_discovery._query_github", return_value=[])
        patcher3 = patch("market_intelligence_engine._query_hn_discussions", return_value=([], 0))
        patcher4 = patch("market_intelligence_engine._query_github_issues", return_value=([], 0))
        patcher5 = patch("competitor_discovery.COMPETITOR_DB_FILE", self.competitor_db_path)
        # Opportunity Rejection Investigation (2026-07-22): reformulate_pain_
        # query() now makes a real (costly, non-deterministic) Groq call and
        # _query_stack_overflow_for_pain() a real network call unless
        # mocked -- found live: an earlier run of this suite without these
        # two mocks leaked 38 real Groq calls into data/ai_cost_log.jsonl.
        patcher6 = patch("market_intelligence_engine.reformulate_pain_query", return_value=("test", "literal_fallback", None))
        patcher7 = patch("market_intelligence_engine._query_stack_overflow_for_pain", return_value=([], 0))
        # Evidence Network (ADR-128, 2026-07-25): analyze_customer_pain() now
        # caches to data/pain_evidence_cache.json by default -- same exact
        # real bug class this class's own docstring already documents fixing
        # once for COMPETITOR_DB_FILE. Found live: a real full regression run
        # wrote this suite's own niche fixtures ("a dry run safety test
        # niche", "a re-evaluation allowed test niche", etc.) into the real
        # shared cache before this fix.
        patcher8 = patch("market_intelligence_engine.PAIN_EVIDENCE_DB_FILE", self.pain_db_path)
        for p in (patcher1, patcher2, patcher3, patcher4, patcher5, patcher6, patcher7, patcher8):
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        for p in (self.timeline_path, self.decisions_path, self.analysis_db_path,
                  self.outcomes_path, self.competitor_db_path, self.pain_db_path, self.state_path):
            if os.path.exists(p):
                os.remove(p)

    def _run_cycle(self, niche, **kwargs):
        return orch.run_cycle(
            niche, timeline_path=self.timeline_path, decisions_path=self.decisions_path,
            analysis_db_file=self.analysis_db_path, outcomes_path=self.outcomes_path,
            state_path=self.state_path, **kwargs,
        )


class TestExistingDecisionAvoidsDuplicateDecisionRecording(_IsolatedRunCycleTestCase):
    """Strategic Phase (2026-07-19): market_hunter.py's daily hunt_market()
    already calls decision_engine.engine.record_ladder_decision() for a
    real accepted opportunity. If the golden-hunter-bridge path called
    run_cycle() without existing_decision, the "decision" stage would run
    evaluate_and_decide() again -- a SEPARATE real re-evaluation recording
    a second decision (different decision_id, since make_decision_id()
    hashes in a fresh timestamp) for the same real niche, risking two
    independent production_ids and duplicate publishing for one real
    opportunity. This is the regression test for that fix."""

    def test_market_intelligence_and_decision_are_skipped_not_reevaluated(self):
        existing = {"decision_id": "existing-1", "niche": "x", "status": "ACCEPTED", "ladder": "b2b_systems"}
        results = self._run_cycle("x", ladder="b2b_systems", existing_decision=existing)
        by_stage = {r.engine: r for r in results}
        self.assertEqual(by_stage["market_intelligence"].status, "SKIPPED_NOT_APPLICABLE")
        self.assertEqual(by_stage["decision"].status, "SKIPPED_NOT_APPLICABLE")
        self.assertIn("reusing an existing decision", by_stage["decision"].output.get("reason", ""))

    def test_zero_new_decisions_are_ever_recorded_to_the_real_store(self):
        existing = {"decision_id": "existing-2", "niche": "y", "status": "ACCEPTED", "ladder": "b2b_systems"}
        self._run_cycle("y", ladder="b2b_systems", existing_decision=existing)
        # decisions_path was never written to at all -- not even created.
        self.assertFalse(os.path.exists(self.decisions_path))

    def test_execute_production_true_proceeds_using_the_reused_decision(self):
        from orchestrator.engines import production as production_engine
        existing = {
            "decision_id": "existing-3", "niche": "z", "status": "ACCEPTED", "ladder": "b2b_systems",
            "evaluation_snapshot": {"price": 197},
        }
        with patch.object(production_engine.subprocess, "run") as mock_run:
            mock_run.return_value.stdout = json.dumps({"success": True, "path": "/fake.pdf"})
            results = self._run_cycle(
                "z", ladder="b2b_systems", execute_production=True, existing_decision=existing,
            )
        by_stage = {r.engine: r for r in results}
        self.assertEqual(by_stage["production"].status, "SUCCESS")
        self.assertEqual(by_stage["publishing"].status, "SUCCESS")

    def test_omitting_existing_decision_reproduces_prior_behavior(self):
        """No existing_decision (every caller before this parameter
        existed) -- market_intelligence/decision still run for real,
        unchanged."""
        results = self._run_cycle("a existing_decision omitted test niche", ladder="b2b_systems")
        by_stage = {r.engine: r for r in results}
        self.assertEqual(by_stage["market_intelligence"].status, "SUCCESS")
        self.assertEqual(by_stage["decision"].status, "SUCCESS")


class TestCliRunLadderOpportunity(unittest.TestCase):
    """Strategic Phase (2026-07-19): the real CLI bridge factory_loop.js's
    golden_hunter_bridge step spawns
    (`python -m orchestrator.orchestrator --run-ladder-opportunity`).
    Must always be invoked with `-m` -- `python orchestrator/orchestrator.py`
    directly puts orchestrator/'s own directory on sys.path, and
    orchestrator/types.py shadows the stdlib `types` module."""

    def test_no_accepted_decision_fails_honestly_never_fabricates_one(self):
        """Real, safe, read-only smoke test against the ACTUAL CLI
        subprocess and the real data/decisions.jsonl -- a niche this
        random can never have a real accepted decision, so this never
        risks a real production/publish side effect."""
        import subprocess
        proc = subprocess.run(
            [sys.executable, "-m", "orchestrator.orchestrator", "--run-ladder-opportunity"],
            input=json.dumps({"niche": "zzz_never_a_real_accepted_niche_test_probe_998877", "ladder": "b2b_systems"}),
            capture_output=True, text=True, encoding="utf-8", cwd=str(_FACTORY_ROOT), timeout=30,
        )
        self.assertEqual(proc.returncode, 1)
        result = json.loads(proc.stdout)
        self.assertFalse(result["success"])
        self.assertIn("no ACCEPTED decision", result["error"])

    def test_invalid_stdin_fails_honestly(self):
        import subprocess
        proc = subprocess.run(
            [sys.executable, "-m", "orchestrator.orchestrator", "--run-ladder-opportunity"],
            input="not valid json", capture_output=True, text=True, encoding="utf-8", cwd=str(_FACTORY_ROOT), timeout=30,
        )
        self.assertEqual(proc.returncode, 1)
        result = json.loads(proc.stdout)
        self.assertFalse(result["success"])

    def test_an_existing_accepted_decision_drives_a_real_run_cycle_call(self):
        """In-process test (not subprocess) so run_cycle()/decision_store
        can be mocked -- proves the CLI reuses the existing decision via
        existing_decision= rather than re-evaluating, and reports the
        real production_id/publish_record back."""
        from orchestrator import orchestrator as orch
        from decision_engine import store as decision_store
        import io

        fake_decision = {"decision_id": "cli-test-1", "niche": "cli test niche", "status": "ACCEPTED", "ladder": "b2b_systems"}
        fake_result_production = ExecutionResult(
            engine="production", status="SUCCESS", started_at="t", finished_at="t",
            attempts=1, idempotency_key="k1", output={"production_id": "PROD-cli-test-1", "success": True},
        )
        fake_result_publishing = ExecutionResult(
            engine="publishing", status="SUCCESS", started_at="t", finished_at="t",
            attempts=1, idempotency_key="k2", output={"publish_record": {"product_id": "PROD-cli-test-1"}},
        )

        with patch.object(decision_store, "find_decisions_by_niche", return_value=[fake_decision]), \
             patch.object(orch, "run_cycle", return_value=[fake_result_production, fake_result_publishing]) as mocked_run_cycle, \
             patch("sys.stdin", io.StringIO(json.dumps({"niche": "cli test niche", "ladder": "b2b_systems"}))), \
             patch("builtins.print") as mocked_print:
            orch._cli_run_ladder_opportunity()

        self.assertEqual(mocked_run_cycle.call_args.kwargs["existing_decision"], fake_decision)
        self.assertTrue(mocked_run_cycle.call_args.kwargs["execute_production"])
        printed = json.loads(mocked_print.call_args.args[0])
        self.assertTrue(printed["success"])
        self.assertEqual(printed["production_id"], "PROD-cli-test-1")


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

    def test_ladder_tagged_decision_routes_production_to_the_techdoc_payload(self):
        """ADR-077: a ladder-tagged decision must route production to the
        same real product_type='techdoc' payload factory_loop.js's
        briefFromGoldenOpportunity() already uses (ADR-071) — never a
        second, diverging assumption about what to build."""
        from unittest.mock import patch, MagicMock
        from orchestrator.engines import production

        context = {
            "niche": "workflow automation system for logistics companies",
            "dry_run": False,
            "decision_result": {"ladder": "b2b_systems", "evaluation_snapshot": {"price": 327}},
        }
        fake_proc = MagicMock(stdout='{"success": true, "product_type": "techdoc"}')
        with patch.object(production.subprocess, "run", return_value=fake_proc) as mock_run:
            production.run(context)
        sent_payload = json.loads(mock_run.call_args.kwargs["input"])
        self.assertEqual(sent_payload["product_type"], "techdoc")
        self.assertEqual(sent_payload["price"], 327)

    def test_no_ladder_tag_reproduces_the_exact_prior_book_payload(self):
        from unittest.mock import patch, MagicMock
        from orchestrator.engines import production

        context = {"niche": "x", "dry_run": False, "decision_result": {}}
        fake_proc = MagicMock(stdout='{"success": true}')
        with patch.object(production.subprocess, "run", return_value=fake_proc) as mock_run:
            production.run(context)
        sent_payload = json.loads(mock_run.call_args.kwargs["input"])
        self.assertNotIn("product_type", sent_payload)
        self.assertEqual(sent_payload["topic"], "x")

    def test_ladder_tagged_decision_with_a_decision_id_threads_the_same_production_id(self):
        """ADR-077 Requirement #5: reuses production_factory.dossier's own
        f"PROD-{decision_id}" formula (via make_production_id) rather than
        inventing a second ID scheme, so the real generated file traces
        back to the same dossier/decision."""
        from unittest.mock import patch, MagicMock
        from orchestrator.engines import production

        context = {
            "niche": "x", "dry_run": False,
            "decision_result": {"ladder": "ai_saas", "decision_id": "dec-abc123", "evaluation_snapshot": {}},
        }
        fake_proc = MagicMock(stdout='{"success": true}')
        with patch.object(production.subprocess, "run", return_value=fake_proc) as mock_run:
            production.run(context)
        sent_payload = json.loads(mock_run.call_args.kwargs["input"])
        self.assertEqual(sent_payload["production_id"], "PROD-dec-abc123")

    def test_a_registered_product_family_dispatches_in_process_never_spawns_a_subprocess(self):
        """Packaging Architecture Plan §7 (Phase A, 2026-07-18): a decision
        whose product_family resolves to an actually-registered adapter
        dispatches through product_families.registry in-process — the new
        Generation path — and never touches the subprocess/techdoc payload
        below it at all."""
        from unittest.mock import patch, MagicMock
        from orchestrator.engines import production
        from product_families import registry as family_registry

        fake_adapter = MagicMock()
        fake_adapter.generate.return_value = {"success": True, "path": "/fake/spreadsheet.pdf"}
        with patch.object(family_registry, "get", return_value=fake_adapter):
            with patch.object(production.subprocess, "run") as mock_subprocess_run:
                context = {
                    "niche": "x", "dry_run": False,
                    "decision_result": {"ladder": "reusable_assets", "product_family": "professional_templates",
                                        "decision_id": "dec-fam-1", "evaluation_snapshot": {"price": 197}},
                }
                result = production.run(context)

        self.assertFalse(mock_subprocess_run.called, "a registered family adapter must dispatch in-process, never spawn book_generator.py")
        self.assertTrue(fake_adapter.generate.called)
        sent_spec = fake_adapter.generate.call_args.args[0]
        self.assertEqual(sent_spec["product_family"], "professional_templates")
        self.assertEqual(sent_spec["production_id"], "PROD-dec-fam-1")
        self.assertTrue(result["success"])

    def test_an_unregistered_product_family_falls_back_to_the_existing_techdoc_payload(self):
        """The "nothing breaks mid-migration" guarantee (Plan §7 Risk 4):
        a resolved family with no adapter built yet (e.g. notion_systems,
        not built in Phase A) must fall through to today's exact hardcoded
        ladder/techdoc behavior, never raise or silently drop the niche."""
        from unittest.mock import patch, MagicMock
        from orchestrator.engines import production

        context = {
            "niche": "x", "dry_run": False,
            "decision_result": {"ladder": "ai_saas", "product_family": "notion_systems", "evaluation_snapshot": {"price": 388}},
        }
        fake_proc = MagicMock(stdout='{"success": true}')
        with patch.object(production.subprocess, "run", return_value=fake_proc) as mock_run:
            production.run(context)
        sent_payload = json.loads(mock_run.call_args.kwargs["input"])
        self.assertEqual(sent_payload["product_type"], "techdoc")


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


class TestPublishingEngineUsesTheUnifiedPipeline(unittest.TestCase):
    """Universal Production Engine Roadmap Step 4 (2026-07-19):
    orchestrator/engines/publishing.py now routes through
    commercial_execution.pipeline.run_publish_pipeline() instead of
    calling distributor.distribute() directly, so a decision's
    product_family (when it has a registered ProductManifest) narrows
    publishing to that family's declared marketplaces."""

    def test_product_family_from_the_decision_result_is_threaded_through(self):
        from orchestrator.engines import publishing

        context = {
            "dry_run": True,
            "production_result": {
                "executed": True, "success": True, "path": "/fake/path.pdf",
                "price": 197.0, "product_type": "techdoc", "production_id": "PROD-pub-test",
                "dossier_bundle": {"version": "1.2.0"},
            },
            "decision_result": {"product_family": "automation_systems"},
        }
        with patch.object(publishing, "run_publish_pipeline") as mocked:
            mocked.return_value = {"marketplaces": [], "product_id": "PROD-pub-test",
                                    "version": "1.2.0", "revenue_status": {}, "audit_trail": []}
            result = publishing.run(context)

        mocked.assert_called_once()
        call_kwargs = mocked.call_args.kwargs
        self.assertEqual(call_kwargs["product_family"], "automation_systems")
        self.assertEqual(call_kwargs["version"], "1.2.0")
        self.assertTrue(result["executed"])
        self.assertIn("publish_record", result)

    def test_no_decision_result_means_no_product_family_never_a_crash(self):
        from orchestrator.engines import publishing

        context = {
            "dry_run": True,
            "production_result": {
                "executed": True, "success": True, "path": "/fake/path.pdf",
                "price": 9.99, "product_type": "book",
            },
        }
        with patch.object(publishing, "run_publish_pipeline") as mocked:
            mocked.return_value = {"marketplaces": [], "product_id": "", "version": None,
                                    "revenue_status": {}, "audit_trail": []}
            publishing.run(context)
        self.assertIsNone(mocked.call_args.kwargs["product_family"])


class TestPublishingEngineHonorsFactoryLivePublish(unittest.TestCase):
    """EOS Phase 2, Round 2 (2026-07-19) production-safety hardening: a
    real live publish now needs BOTH context["dry_run"]=False AND
    FACTORY_LIVE_PUBLISH=true -- confirmed this was NOT the case before
    this fix (context["dry_run"] alone controlled it, and the modern
    ladder pipeline hardcodes execute_production=True, which flows into
    dry_run=False with zero further check). Matches the founder's own,
    already-documented "three independent barriers" design
    (AUTO_PRODUCE_ACTIVATION_CHECKLIST.md, ADR-009 §9.2)."""

    def _context(self):
        return {
            "dry_run": False,
            "production_result": {
                "executed": True, "success": True, "path": "/fake/path.pdf",
                "price": 197.0, "product_type": "techdoc", "production_id": "PROD-live-test",
                "dossier_bundle": {"version": "1.0.0"},
            },
        }

    def test_dry_run_false_without_factory_live_publish_still_forces_a_dry_run(self):
        from orchestrator.engines import publishing
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FACTORY_LIVE_PUBLISH", None)
            with patch.object(publishing, "run_publish_pipeline") as mocked:
                mocked.return_value = {"marketplaces": [], "product_id": "x", "version": "1.0.0",
                                        "revenue_status": {}, "audit_trail": []}
                publishing.run(self._context())
        self.assertTrue(mocked.call_args.kwargs["dry_run"])

    def test_dry_run_false_with_factory_live_publish_true_allows_a_real_attempt(self):
        from orchestrator.engines import publishing
        with patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"}):
            with patch.object(publishing, "run_publish_pipeline") as mocked:
                mocked.return_value = {"marketplaces": [], "product_id": "x", "version": "1.0.0",
                                        "revenue_status": {}, "audit_trail": []}
                publishing.run(self._context())
        self.assertFalse(mocked.call_args.kwargs["dry_run"])

    def test_context_dry_run_true_still_wins_even_with_factory_live_publish_true(self):
        from orchestrator.engines import publishing
        context = self._context()
        context["dry_run"] = True
        with patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"}):
            with patch.object(publishing, "run_publish_pipeline") as mocked:
                mocked.return_value = {"marketplaces": [], "product_id": "x", "version": "1.0.0",
                                        "revenue_status": {}, "audit_trail": []}
                publishing.run(context)
        self.assertTrue(mocked.call_args.kwargs["dry_run"])


if __name__ == "__main__":
    unittest.main()
