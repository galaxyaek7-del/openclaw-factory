"""Master Sprint A4: the Quality Enforcer gates real (non-dry-run) production.

book_generator.py is never spawned here: the gate must stop the run first.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from orchestrator.engines import production  # noqa: E402


class TestProductionQualityGate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _ctx(self, **brief):
        return {"niche": "a gate test niche", "dry_run": False, "quality_report_dir": str(self.tmp),
                "decision_result": {"ladder": "b2b_systems", "evaluation_snapshot": {"price": 197}},
                "product_brief": brief}

    def test_missing_facts_raise_and_never_spawn_generation(self):
        with patch.object(production.subprocess, "run") as mock_run, \
             patch("market_evidence.get_payment_evidence", return_value=[]):
            with self.assertRaises(production.QualityGateBlocked) as cm:
                production.run(self._ctx())
        self.assertFalse(mock_run.called)
        self.assertEqual(cm.exception.gate["verdict"], "BLOCKED_MISSING_DATA")
        self.assertTrue(list(self.tmp.glob("*.json")), "the blocked inspection must be saved")

    def test_blocked_stage_is_recorded_failed_not_succeeded(self):
        from orchestrator import orchestrator as orch
        from orchestrator.types import ExecutionResult  # noqa: F401  (shape check only)
        with patch.object(production.subprocess, "run") as mock_run, \
             patch("market_evidence.get_payment_evidence", return_value=[]):
            res = orch._run_stage("production", production.run, self._ctx(), "k-gate-test",
                                  str(self.tmp / "timeline.jsonl"), 1, state_path=str(self.tmp / "state.json"))
        self.assertFalse(mock_run.called)
        self.assertEqual(res.status, "FAILED")
        self.assertIn("quality_enforcer BLOCKED_MISSING_DATA", res.error)

    def test_dry_run_is_untouched_by_the_gate(self):
        with patch.object(production, "_pre_production_gate") as gate:
            out = production.run({"niche": "x", "dry_run": True})
        self.assertFalse(out["executed"])
        self.assertFalse(gate.called)


if __name__ == "__main__":
    unittest.main()
