"""Tests for executive_intelligence/production_gate.py (Autonomous
Digital Company v1 follow-up, 2026-07-19): the real production-engine
health gate for factory_loop.js's Golden Hunter Bridge.

Runs with stdlib unittest. Every function reads only from a temp-file-
isolated timeline — never the real data/orchestrator_timeline.jsonl.

    python -m unittest tests.test_production_gate -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from orchestrator import timeline as orch_timeline
from orchestrator.types import ExecutionResult

from executive_intelligence import production_gate


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestProductionEngineHealthGate(unittest.TestCase):
    def setUp(self):
        self.timeline_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.timeline_path):
            os.remove(self.timeline_path)

    def test_no_real_execution_history_never_blocks(self):
        result = production_gate.check_production_engine_health(timeline_path=self.timeline_path)
        self.assertTrue(result["ok"])
        self.assertEqual(result["engine_health"].get("maturity"), "DISCOVERY")

    def test_healthy_production_engine_never_blocks(self):
        for i in range(4):
            orch_timeline.append_execution(
                ExecutionResult(engine="production", status="SUCCESS", started_at=f"t{i}", finished_at=f"t{i}", attempts=1, idempotency_key=f"k{i}", output={}),
                path=self.timeline_path,
            )
        result = production_gate.check_production_engine_health(timeline_path=self.timeline_path)
        self.assertTrue(result["ok"])
        self.assertEqual(result["engine_health"]["success_rate"], 100.0)

    def test_real_low_success_rate_blocks_with_an_honest_reason(self):
        # 1 success, 4 failures -> 20% real success rate, below the 80% alert threshold.
        orch_timeline.append_execution(
            ExecutionResult(engine="production", status="SUCCESS", started_at="t0", finished_at="t0", attempts=1, idempotency_key="k0", output={}),
            path=self.timeline_path,
        )
        for i in range(1, 5):
            orch_timeline.append_execution(
                ExecutionResult(engine="production", status="FAILED", started_at=f"t{i}", finished_at=f"t{i}", attempts=1, idempotency_key=f"k{i}", output={}, error="x"),
                path=self.timeline_path,
            )
        result = production_gate.check_production_engine_health(timeline_path=self.timeline_path)
        self.assertFalse(result["ok"])
        self.assertIn("20", result["reason"])
        self.assertEqual(result["engine_health"]["success_rate"], 20.0)

    def test_only_the_production_stage_is_gated_not_other_engines(self):
        # A real low success rate on a DIFFERENT engine must never block production.
        for i in range(4):
            orch_timeline.append_execution(
                ExecutionResult(engine="market_intelligence", status="FAILED", started_at=f"t{i}", finished_at=f"t{i}", attempts=1, idempotency_key=f"k{i}", output={}, error="x"),
                path=self.timeline_path,
            )
        result = production_gate.check_production_engine_health(timeline_path=self.timeline_path)
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
