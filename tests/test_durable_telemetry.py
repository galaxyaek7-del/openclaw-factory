"""Tests for Phase 2C durable append-only runtime telemetry (ADR-245).

Proves the full Phase 2C contract:
  1. telemetry is persisted to data/runtime_telemetry.jsonl (durable);
  2. it is APPEND-ONLY — prior records are never lost or rewritten;
  3. existing records are preserved across new appends;
  4. run_id (the Phase 2B carrier) is carried into applicable records;
  5. multiple runs are distinguishable by distinct run_id;
  6. malformed/failed telemetry fails SAFELY (returns False, never raises,
     never weakens a barrier);
  7. telemetry can NEVER authorize publishing — it returns only a bool and
     exposes no allow/proceed concept, and nothing reads it to gate;
  8. the in-memory JSON telemetry (lib/metrics.js summarizeRoutes) remains
     functional (unchanged contract) — verified in tests/test_metrics.js,
     untouched by this phase;
  9. the Prometheus surface (renderPrometheusText) remains intact — also
     verified in tests/test_metrics.js;
  10-14. Gate-1/Gate-2, distributor, publish-protection and circuit-breaker
     suites all still pass — this file proves the causal mechanism (a
     telemetry write failure cannot change a run_cycle() gate decision),
     and the full regression run confirms those suites separately;
  15. no financial mutation happens via telemetry;
  16. the pre-existing orchestrator failure (decision+resolve_product_family)
     is NOT repaired by this phase — no telemetry code touches that path.

Runs with stdlib unittest.
"""

import json
import os
import shutil
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

import durable_telemetry
from orchestrator.types import ExecutionResult


def _temp_dir():
    return tempfile.mkdtemp(prefix="gf-2c-")


class TestDurableTelemetryWriter(unittest.TestCase):
    def setUp(self):
        self.tmp = _temp_dir()
        self.telemetry_path = os.path.join(self.tmp, "runtime_telemetry.jsonl")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── (1) persisted to the durable ledger ──────────────────────────────
    def test_append_persists_a_record_to_disk(self):
        self.assertTrue(durable_telemetry.append_telemetry(
            {"event": "observational_note", "run_id": "run_1"}, path=self.telemetry_path))
        self.assertTrue(os.path.exists(self.telemetry_path))
        records = durable_telemetry.read_telemetry(path=self.telemetry_path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event"], "observational_note")

    # ── (2) append-only: never truncates, never rewrites prior lines ────
    def test_append_only_never_truncates(self):
        durable_telemetry.append_telemetry({"event": "observational_note", "note": "first"}, path=self.telemetry_path)
        durable_telemetry.append_telemetry({"event": "observational_note", "note": "second"}, path=self.telemetry_path)
        durable_telemetry.append_telemetry({"event": "observational_note", "note": "third"}, path=self.telemetry_path)
        lines = []
        with open(self.telemetry_path, encoding="utf-8") as f:
            lines = f.read().split("\n")
        nonempty = [l for l in lines if l.strip()]
        self.assertEqual(len(nonempty), 3)
        # original first line is still the first line, unmodified
        self.assertEqual(json.loads(nonempty[0])["note"], "first")

    # ── (3) existing records preserved across new appends ───────────────
    def test_existing_records_preserved(self):
        durable_telemetry.append_telemetry({"event": "observational_note", "note": "old"}, path=self.telemetry_path)
        before = durable_telemetry.read_telemetry(path=self.telemetry_path)
        durable_telemetry.append_telemetry({"event": "observational_note", "note": "new"}, path=self.telemetry_path)
        after = durable_telemetry.read_telemetry(path=self.telemetry_path)
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(after[0], before[0])

    # ── (4) run_id carried into applicable records ──────────────────────
    def test_run_id_is_carried_into_record(self):
        durable_telemetry.append_telemetry({"event": "run_dispatched", "run_id": "run_abc_123", "niche": "x"},
                                           path=self.telemetry_path)
        rec = durable_telemetry.read_telemetry(path=self.telemetry_path)[0]
        self.assertEqual(rec["run_id"], "run_abc_123")

    def test_non_string_run_id_is_never_stored(self):
        # a dict/list/bool is not a run identity — must become None, never a junk value
        durable_telemetry.append_telemetry({"event": "run_dispatched", "run_id": {"bad": 1}}, path=self.telemetry_path)
        rec = durable_telemetry.read_telemetry(path=self.telemetry_path)[0]
        self.assertIsNone(rec["run_id"])

    def test_stage_outcome_carries_the_execution_result_run_id(self):
        result = ExecutionResult("production", "SUCCESS", "s", "f", 1, "k", {"success": True}, run_id="run_STAGE")
        self.assertTrue(durable_telemetry.append_stage_outcome(result, path=self.telemetry_path))
        rec = durable_telemetry.read_telemetry(path=self.telemetry_path)[0]
        self.assertEqual(rec["run_id"], "run_STAGE")
        self.assertEqual(rec["event"], "stage_outcome")
        self.assertEqual(rec["status"], "SUCCESS")
        self.assertEqual(rec["engine"], "production")

    # ── (5) multiple runs distinguishable ────────────────────────────────
    def test_multiple_runs_distinguishable_by_run_id(self):
        durable_telemetry.append_run_dispatched("run_A", {"niche": "n1"}, path=self.telemetry_path)
        durable_telemetry.append_run_dispatched("run_B", {"niche": "n2"}, path=self.telemetry_path)
        ids = {r["run_id"] for r in durable_telemetry.read_telemetry(path=self.telemetry_path)}
        self.assertEqual(ids, {"run_A", "run_B"})

    # ── (6) malformed/failed telemetry fails safely ──────────────────────
    def test_unknown_event_type_is_refused_not_appended(self):
        # never fabricate: an event type we didn't register must be refused
        self.assertFalse(durable_telemetry.append_telemetry({"event": "invented_event"}, path=self.telemetry_path))
        self.assertEqual(durable_telemetry.read_telemetry(path=self.telemetry_path), [])

    def test_non_dict_record_is_refused(self):
        self.assertFalse(durable_telemetry.append_telemetry("not a dict", path=self.telemetry_path))
        self.assertFalse(durable_telemetry.append_telemetry(["list"], path=self.telemetry_path))
        self.assertEqual(durable_telemetry.read_telemetry(path=self.telemetry_path), [])

    def test_failed_write_returns_false_never_raises(self):
        # a path whose parent cannot be created (nested under an existing FILE)
        blocking_path = os.path.join(self.tmp, "afile", "sub", "ledger.jsonl")
        with open(os.path.join(self.tmp, "afile"), "w") as f:
            f.write("x")
        self.assertFalse(durable_telemetry.append_telemetry({"event": "observational_note"}, path=blocking_path))

    def test_corrupt_partial_line_is_skipped_on_read(self):
        # a crash mid-write leaves a partial line; it must be skipped, not fatal
        with open(self.telemetry_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"event": "observational_note", "run_id": "run_ok"}) + "\n")
            f.write('{"event": "observational_note", "run_id": "run_par' + "\n")  # truncated
        records = durable_telemetry.read_telemetry(path=self.telemetry_path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["run_id"], "run_ok")

    # ── (7) telemetry can NEVER authorize publishing ─────────────────────
    def test_append_returns_only_a_bool_never_a_proceed_signal(self):
        # the module's only "result" is whether the append landed — a bool, not a
        # do/allow token. Nothing can treat it as authorization.
        ret = durable_telemetry.append_telemetry({"event": "observational_note"}, path=self.telemetry_path)
        self.assertIs(type(ret), bool)
        # the module has no gate-decision vocabulary and no way for its return
        # value to be read as authorization to publish. (Note: 'allow' itself
        # is legitimately inside "swallow", so we scan for gate SPECIFIC tokens.)
        module_src = None
        with open(os.path.join(_FACTORY_ROOT, "durable_telemetry.py"), encoding="utf-8") as f:
            module_src = f.read()
        for forbidden in ("authorize_gate", "proceed_signal", "approved", "def allow", "allow_publish"):
            self.assertNotIn(forbidden, module_src)

    def test_append_stage_outcome_records_only_the_real_execution_status(self):
        # SUCCESS is only recorded when the real result says SUCCESS — never
        # synthesized. A FAILED result must be recorded as FAILED.
        failed = ExecutionResult("production", "FAILED", "s", "f", 2, "k", {}, error="boom")
        self.assertTrue(durable_telemetry.append_stage_outcome(failed, path=self.telemetry_path))
        rec = durable_telemetry.read_telemetry(path=self.telemetry_path)[0]
        self.assertEqual(rec["status"], "FAILED")
        self.assertEqual(rec["error"], "boom")
        self.assertEqual(rec["attempts"], 2)

    # ── (15) no financial mutation ───────────────────────────────────────
    def test_append_never_touches_finance_data(self):
        # durable telemetry writes only to its ledger path; it must neither
        # create nor alter finance_data.json.
        finance = _FACTORY_ROOT / "finance_data.json"
        before = finance.read_bytes() if finance.exists() else None
        created = not finance.exists()
        self.assertTrue(durable_telemetry.append_run_dispatched("run_F", {"niche": "n"}, path=self.telemetry_path))
        if created:
            self.assertFalse(finance.exists(), "telemetry must not create finance_data.json")
        else:
            self.assertEqual(finance.read_bytes(), before, "telemetry must not alter finance_data.json")


class TestOrchestratorIsolationFromTelemetry(unittest.TestCase):
    """The real gate-coupling proof: a durable-telemetry WRITE FAILURE must
    not change what a run_cycle() decides to do (Gate-1/Gate-2 semantics).
    We run an isolated run once with telemetry working and once with the
    writer forced to fail, and assert the resulting stage statuses are
    IDENTICAL — i.e. telemetry cannot gate or influence the pipeline."""

    def setUp(self):
        self.tmp = _temp_dir()
        self.timeline_path = os.path.join(self.tmp, "timeline.jsonl")
        self.telemetry_ok = os.path.join(self.tmp, "tel_ok.jsonl")
        self.telemetry_bad = os.path.join(self.tmp, "blocked", "child", "tel_bad.jsonl")
        # Phase 2 isolation close-out: every store this run touches must go to an
        # isolated temp path so validation can never write into real factory
        # ledgers (data/decisions.jsonl, data/market_intelligence_analyses.jsonl,
        # data/factory_state.json, data/... decision outcomes).
        self.decisions_path = os.path.join(self.tmp, "decisions.jsonl")
        self.analysis_db_path = os.path.join(self.tmp, "analysis.jsonl")
        self.outcomes_path = os.path.join(self.tmp, "outcomes.jsonl")
        self.state_path = os.path.join(self.tmp, "state.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_isolated(self, niche, telemetry_path):
        from orchestrator import orchestrator as orch
        return orch.run_cycle(
            niche,
            timeline_path=self.timeline_path,
            telemetry_path=telemetry_path,
            decisions_path=self.decisions_path,
            analysis_db_file=self.analysis_db_path,
            outcomes_path=self.outcomes_path,
            state_path=self.state_path,
            execute_production=False,
        )

    def test_telemetry_write_failure_does_not_change_stage_gates(self):
        # Run WITHOUT real network: mock the two live query functions this
        # pipeline touches so we only measure gate behavior, not I/O.
        with patch("competitor_discovery._query_hn", return_value=[]), \
             patch("competitor_discovery._query_github", return_value=[]), \
             patch("market_intelligence_engine.reformulate_pain_query", return_value=("x", "literal", None)), \
             patch("market_intelligence_engine._query_hn_discussions", return_value=([], 0)), \
             patch("market_intelligence_engine._query_github_issues", return_value=([], 0)), \
             patch("market_intelligence_engine._query_stack_overflow_for_pain", return_value=([], 0)):
            # Baseline: telemetry writer working, isolated path.
            good = self._run_isolated("telemetry-gate-probe", self.telemetry_ok)
            # Telemetry forced to fail the way it REALLY fails: append_stage_outcome
            # swallows errors and returns False (it never raises). Simulating that
            # honest failure path proves a swallowed telemetry write cannot change
            # any gate outcome.
            with patch("durable_telemetry.append_stage_outcome", return_value=False):
                forced = self._run_isolated("telemetry-gate-probe", self.telemetry_bad)
            # gate semantics (per-stage status) are identical with and without telemetry
            self.assertEqual({r.engine: r.status for r in good},
                             {r.engine: r.status for r in forced},
                             "telemetry write failure must not change any stage's gate outcome")


class TestTelemetryBoundary(unittest.TestCase):
    def test_default_ledger_path_is_the_documented_durable_location(self):
        self.assertEqual(str(durable_telemetry.DEFAULT_TELEMETRY_PATH),
                         str(_FACTORY_ROOT / "data" / "runtime_telemetry.jsonl"))

    def test_event_types_are_the_registered_fixed_set(self):
        self.assertEqual(set(durable_telemetry.EVENT_TYPES),
                         {"stage_outcome", "run_dispatched", "run_completed", "observational_note"})


if __name__ == "__main__":
    unittest.main()