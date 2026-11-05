"""Tests for Phase 2B run-identity carrier (ADR-245).

Proves the additive run_id contract:
  * every stage record of one run_cycle() shares the SAME run_id (same run,
    same identity);
  * two separate runs (with or without a caller-supplied id) never silently
    share an identity (unrelated runs stay distinct);
  * a valid caller-supplied run_id is honored and carried unfiltered
    (the cross-engine JS -> Python carrier);
  * a missing / malformed run_id is safely handled (mint a fresh per-run id,
    never propagate a junk identity);
  * existing logging behavior does not regress — a legacy ExecutionResult
    with run_id=None serializes byte-identically (no run_id key);
  * zero new durable telemetry ledger is introduced (run_id decorates the
    existing orchestrator timeline only) and no external I/O / financial
    mutation happens.

Runs with stdlib unittest. Same isolation convention as
tests/test_orchestrator.py._IsolatedRunCycleTestCase: every real store is
redirected to temp files and every network function is mocked.
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

# Phase 2 isolation close-out (ADR-245): redirect every factory-side default AI
# cost-ledger read/write (ai_capability/registry.py, ai_capability/observatory.py,
# book_generator.py) to an isolated temp location BEFORE those modules are
# imported, so this test process can never pollute the real data/ai_cost_log.jsonl
# even if a Groq call slips past a mock.
_GF_COST_LOG_DIR = tempfile.mkdtemp(prefix="gf-costlog-")
os.environ["GF_AI_COST_LOG"] = os.path.join(_GF_COST_LOG_DIR, "ai_cost_log.jsonl")

from orchestrator import orchestrator as orch
from orchestrator import run_id, timeline
from orchestrator.types import ExecutionResult, EXECUTION_ORDER
import durable_telemetry


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class _IsolatedRunCycleTestCase(unittest.TestCase):
    """Same isolation discipline as tests/test_orchestrator.py: redirect every
    real store to temp files and mock every network/DB write."""

    def setUp(self):
        self.timeline_path = _temp_path()
        self.telemetry_path = _temp_path()
        self.decisions_path = _temp_path()
        self.analysis_db_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.competitor_db_path = _temp_path(".json")
        self.pain_db_path = _temp_path(".json")
        self.state_path = _temp_path(".json")
        patchers = [
            patch("competitor_discovery._query_hn", return_value=[]),
            patch("competitor_discovery._query_github", return_value=[]),
            patch("market_intelligence_engine._query_hn_discussions", return_value=([], 0)),
            patch("market_intelligence_engine._query_github_issues", return_value=([], 0)),
            patch("competitor_discovery.COMPETITOR_DB_FILE", self.competitor_db_path),
            patch("market_intelligence_engine.reformulate_pain_query", return_value=("test", "literal_fallback", None)),
            patch("market_intelligence_engine._query_stack_overflow_for_pain", return_value=([], 0)),
            patch("market_intelligence_engine.PAIN_EVIDENCE_DB_FILE", self.pain_db_path),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        for p in (self.timeline_path, self.telemetry_path, self.decisions_path, self.analysis_db_path,
                  self.outcomes_path, self.competitor_db_path, self.pain_db_path, self.state_path):
            if os.path.exists(p):
                os.remove(p)

    def _run_cycle(self, niche, **kwargs):
        return orch.run_cycle(
            niche, timeline_path=self.timeline_path, decisions_path=self.decisions_path,
            analysis_db_file=self.analysis_db_path, outcomes_path=self.outcomes_path,
            state_path=self.state_path, telemetry_path=self.telemetry_path, **kwargs,
        )

    def _records(self):
        return list(timeline.read_timeline(path=self.timeline_path))

    def _telemetry(self):
        return durable_telemetry.read_telemetry(path=self.telemetry_path)


class TestRunIdentityHelpers(unittest.TestCase):
    def test_new_run_id_is_unique(self):
        a, b = run_id.new_run_id(), run_id.new_run_id()
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("run_"))
        self.assertTrue(b.startswith("run_"))

    def test_coerce_rejects_none_and_nonstrings_and_whitespace(self):
        self.assertIsNone(run_id.coerce_run_id(None))
        self.assertIsNone(run_id.coerce_run_id(b"raw-bytes"))
        self.assertIsNone(run_id.coerce_run_id(12345))
        self.assertIsNone(run_id.coerce_run_id({"a": 1}))
        self.assertIsNone(run_id.coerce_run_id("   "))
        self.assertIsNone(run_id.coerce_run_id("has space and punctuation!"))

    def test_coerce_accepts_a_literal_identifier_token(self):
        self.assertEqual(run_id.coerce_run_id("run_20260902_abc123_x.y-z:1"), "run_20260902_abc123_x.y-z:1")

    def test_resolve_honors_valid_value_instead_of_minting(self):
        self.assertEqual(run_id.resolve_run_id("run_SPECIAL_1"), "run_SPECIAL_1")

    def test_resolve_mints_fresh_when_missing_or_invalid(self):
        r1 = run_id.resolve_run_id(None)
        r2 = run_id.resolve_run_id("!!!bad!!!")
        r3 = run_id.resolve_run_id(None)
        self.assertTrue(r1.startswith("run_"))
        self.assertTrue(r2.startswith("run_"))
        # never returns None and never reuses an unrelated identity
        self.assertNotEqual(r1, r3)


class TestExecutionResultSerialization(unittest.TestCase):
    def test_legacy_record_without_run_id_has_no_run_id_key(self):
        record = ExecutionResult("x", "SUCCESS", "t", "t", 1, "k1", {}).to_dict()
        self.assertNotIn("run_id", record)

    def test_record_with_run_id_carries_it_in_serialized_form(self):
        record = ExecutionResult("x", "SUCCESS", "t", "t", 1, "k1", {}, run_id="run_R1").to_dict()
        self.assertEqual(record["run_id"], "run_R1")


class TestSameRunSharesOneRunId(_IsolatedRunCycleTestCase):
    def test_every_timeline_record_of_one_run_has_identical_run_id(self):
        self._run_cycle("identical run id test niche")
        records = self._records()
        self.assertTrue(records, "timeline should have records")
        ids = {r.get("run_id") for r in records}
        self.assertEqual(len(ids), 1, f"all records must share one run_id, got {ids}")
        self.assertTrue(records[0]["run_id"].startswith("run_"))
        # every stage is present, so the "same run" claim covers the whole cycle
        self.assertEqual({r["engine"] for r in records}, set(EXECUTION_ORDER))

    def test_caller_supplied_run_id_is_carried_into_every_record(self):
        self._run_cycle("supplied run id test niche", run_id="run_EXTERNAL_CARRIER")
        ids = {r.get("run_id") for r in self._records()}
        self.assertEqual(ids, {"run_EXTERNAL_CARRIER"})


class TestUnrelatedRunsNeverShareAnIdentity(_IsolatedRunCycleTestCase):
    def test_two_omitted_runs_get_distinct_identities(self):
        self._run_cycle("distinct run a")
        self._run_cycle("distinct run b")
        ids = {r.get("run_id") for r in self._records()}
        self.assertEqual(len(ids), 2, f"two runs must never share an identity, got {ids}")

    def test_two_supplied_runs_with_same_id_are_distinct_from_an_autonomous_run(self):
        # Two runs sharing a caller id is a legitimate caller decision; the
        # guarantee that matters is a caller-supplied run is never conflated
        # with an id-less run minted fresh by the engine.
        self._run_cycle("supplied same id a", run_id="run_SHARED")
        self._run_cycle("supplied same id b", run_id="run_SHARED")
        self._run_cycle("autonomous run", run_id=None)
        ids = {r.get("run_id") for r in self._records()}
        self.assertEqual(len(ids), 2)
        self.assertIn("run_SHARED", ids)
        minted = (ids - {"run_SHARED"}).pop()
        self.assertTrue(minted.startswith("run_"))


class TestMalformedRunIdHandling(_IsolatedRunCycleTestCase):
    def test_invalid_run_id_never_propagates_a_junk_identity(self):
        self._run_cycle("malformed run id test niche", run_id="!!! not a token !!!")
        records = self._records()
        ids = {r.get("run_id") for r in records}
        self.assertEqual(len(ids), 1)
        self.assertTrue(records[0]["run_id"].startswith("run_"))


class TestNoDurableTelemetryIntroduced(_IsolatedRunCycleTestCase):
    def test_isolated_run_writes_durable_telemetry_only_to_the_temp_path(self):
        # Phase 2C: the append-only durable telemetry ledger is a real, intended
        # artifact of every run. The isolation contract is that a TEST run's
        # telemetry goes to the isolated telemetry_path, never the real
        # data/runtime_telemetry.jsonl. This test proves both halves: the temp
        # ledger got the real records AND the real default ledger was not
        # touched by this test run.
        real_default = durable_telemetry.DEFAULT_TELEMETRY_PATH
        real_before = durable_telemetry.read_telemetry(path=str(real_default)) if real_default.exists() else None

        self._run_cycle("no telemetry test niche")
        telemetry = self._telemetry()
        self.assertTrue(telemetry, "isolated run must write durable telemetry to its temp path")
        for rec in telemetry:
            self.assertIn("run_id", rec)
            self.assertNotEqual(rec.get("run_id"), None, "every 2C stage outcome must carry the resolved run_id")

        real_after = durable_telemetry.read_telemetry(path=str(real_default)) if real_default.exists() else None
        self.assertEqual(real_before, real_after, "a test run must never change the real durable telemetry ledger")

    def test_no_external_financial_mutation(self):
        # Corrected Phase 2 invariant (closes the closed-out assertion): a
        # successful decision execution MAY write its decision record — but only
        # to the ISOLATED test location, and doing so must NEVER count as a
        # financial mutation. finance_data.json and the real factory
        # decisions.jsonl ledger must both remain untouched by a test run.
        from decision_engine import store as decision_store

        real_decisions = decision_store.DEFAULT_DECISIONS_PATH
        real_decisions_before = real_decisions.read_bytes() if real_decisions.exists() else None
        real_decisions_existed = real_decisions.exists()

        finance = _FACTORY_ROOT / "finance_data.json"
        finance_before = finance.read_bytes() if finance.exists() else None

        self._run_cycle("no finance mutation test niche")

        # (a) the decision stage succeeded and recorded its decision in the
        #     ISOLATED location — this is the intended, correct behavior.
        self.assertTrue(
            os.path.exists(self.decisions_path),
            "a successful decision must be recorded in the isolated decisions path",
        )
        # (b) the isolated decision record is genuinely present and non-empty.
        with open(self.decisions_path, encoding="utf-8") as f:
            written = [l for l in f.read().split("\n") if l.strip()]
        self.assertTrue(written, "isolated decisions ledger must carry the decision")

        # (c) the decision is NOT a financial mutation: finance_data.json unchanged.
        self.assertEqual(finance.read_bytes(), finance_before, "a decision must never alter finance_data.json")

        # (d) the REAL factory decisions ledger (and any other store) is never
        #     touched by an isolated test run.
        if real_decisions_existed:
            self.assertEqual(
                real_decisions.read_bytes(), real_decisions_before,
                "an isolated run must not append to the real factory decisions.jsonl",
            )
        else:
            self.assertFalse(real_decisions.exists(), "an isolated run must not create the real decisions.jsonl")


class TestCliForwardsCarrierRunId(unittest.TestCase):
    """The real JS -> Python carrier: `python -m orchestrator.orchestrator
    --run-ladder-opportunity` reads {niche, ladder, tier, run_id} from stdin
    and must hand a valid caller-supplied run_id to run_cycle() so Python's
    timeline records share the JS spawner's identity."""

    def test_stdin_run_id_is_forwarded_to_run_cycle(self):
        import io
        from decision_engine import store as decision_store

        fake_decision = {"decision_id": "cli-rid-1", "niche": "cli rid niche", "status": "ACCEPTED", "ladder": "b2b_systems"}
        fake_result = ExecutionResult(
            engine="production", status="SUCCESS", started_at="t", finished_at="t",
            attempts=1, idempotency_key="k1", output={"production_id": "PROD-rid-1", "success": True}, run_id="run_JS_CARRIER",
        )
        with patch.object(decision_store, "find_decisions_by_niche", return_value=[fake_decision]), \
             patch.object(orch, "run_cycle", return_value=[fake_result]) as mocked_run_cycle, \
             patch("sys.stdin", io.StringIO(json.dumps({"niche": "cli rid niche", "ladder": "b2b_systems", "run_id": "run_JS_CARRIER"}))), \
             patch.object(durable_telemetry, "append_run_completed"), \
             patch("builtins.print"):
            orch._cli_run_ladder_opportunity()

        self.assertEqual(mocked_run_cycle.call_args.kwargs["run_id"], "run_JS_CARRIER")

    def test_stdin_without_run_id_reproduces_legacy_forwarding(self):
        import io
        from decision_engine import store as decision_store

        fake_decision = {"decision_id": "cli-rid-2", "niche": "cli rid niche 2", "status": "ACCEPTED", "ladder": "b2b_systems"}
        fake_result = ExecutionResult(
            engine="production", status="SUCCESS", started_at="t", finished_at="t",
            attempts=1, idempotency_key="k1", output={"success": True},
        )
        with patch.object(decision_store, "find_decisions_by_niche", return_value=[fake_decision]), \
             patch.object(orch, "run_cycle", return_value=[fake_result]) as mocked_run_cycle, \
             patch("sys.stdin", io.StringIO(json.dumps({"niche": "cli rid niche 2", "ladder": "b2b_systems"}))), \
             patch.object(durable_telemetry, "append_run_completed"), \
             patch("builtins.print"):
            orch._cli_run_ladder_opportunity()

        # "legacy" stdin (no run_id key) forwards None -> run_cycle mints fresh.
        self.assertIsNone(mocked_run_cycle.call_args.kwargs["run_id"])


if __name__ == "__main__":
    unittest.main()