"""Tests for recovery/startup_check.py (Unified Recovery System §2,
2026-07-18): safe startup classification. Never touches the real
data/factory_state.json or orchestrator_timeline.jsonl — every test
passes explicit temp paths.

    python -m unittest tests.test_startup_check -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import factory_state
from orchestrator import timeline
from orchestrator.types import ExecutionResult
from recovery import startup_check


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    return path


class TestCheckStartupSafety(unittest.TestCase):
    def setUp(self):
        self.state_path = _temp_path()
        self.timeline_path = _temp_path()

    def tearDown(self):
        for p in (self.state_path, self.timeline_path):
            if os.path.exists(p):
                os.remove(p)

    def test_clean_start_is_always_healthy_regardless_of_state(self):
        factory_state.set_current_task("production", idempotency_key="key1", path=self.state_path)
        result = startup_check.check_startup_safety(False, state_path=self.state_path, timeline_path=self.timeline_path)
        self.assertEqual(result["classification"], "HEALTHY")

    def test_stale_lock_with_no_in_flight_task_is_recovering(self):
        result = startup_check.check_startup_safety(True, state_path=self.state_path, timeline_path=self.timeline_path)
        self.assertEqual(result["classification"], "RECOVERING")
        self.assertIsNone(result["current_task"])

    def test_stale_lock_mid_read_only_orchestrator_stage_is_recovering(self):
        factory_state.set_current_task("market_intelligence", idempotency_key="key1", path=self.state_path)
        result = startup_check.check_startup_safety(True, state_path=self.state_path, timeline_path=self.timeline_path)
        self.assertEqual(result["classification"], "RECOVERING")

    def test_stale_lock_mid_production_with_no_success_record_needs_confirmation(self):
        factory_state.set_current_task("production", idempotency_key="key1", path=self.state_path)
        result = startup_check.check_startup_safety(True, state_path=self.state_path, timeline_path=self.timeline_path)
        self.assertEqual(result["classification"], "NEEDS_CONFIRMATION")

    def test_stale_lock_mid_production_that_already_succeeded_is_recovering(self):
        """The real external side effect (e.g. Paddle create) already
        completed and was recorded before the crash -- safe to resume."""
        factory_state.set_current_task("production", idempotency_key="key1", path=self.state_path)
        timeline.append_execution(
            ExecutionResult(engine="production", status="SUCCESS", started_at="t1", finished_at="t2",
                             attempts=1, idempotency_key="key1", output={}, error=None),
            path=self.timeline_path,
        )
        result = startup_check.check_startup_safety(True, state_path=self.state_path, timeline_path=self.timeline_path)
        self.assertEqual(result["classification"], "RECOVERING")

    def test_stale_lock_mid_publishing_with_no_success_record_needs_confirmation(self):
        factory_state.set_current_task("publishing", idempotency_key="key2", path=self.state_path)
        result = startup_check.check_startup_safety(True, state_path=self.state_path, timeline_path=self.timeline_path)
        self.assertEqual(result["classification"], "NEEDS_CONFIRMATION")

    def test_stale_lock_mid_risky_golden_hunter_tick_step_needs_confirmation(self):
        factory_state.set_current_task("golden_hunter_tick", step="golden_hunter_bridge", path=self.state_path)
        result = startup_check.check_startup_safety(True, state_path=self.state_path, timeline_path=self.timeline_path)
        self.assertEqual(result["classification"], "NEEDS_CONFIRMATION")

    def test_stale_lock_mid_safe_golden_hunter_tick_step_is_recovering(self):
        factory_state.set_current_task("golden_hunter_tick", step="sales_poll", path=self.state_path)
        result = startup_check.check_startup_safety(True, state_path=self.state_path, timeline_path=self.timeline_path)
        self.assertEqual(result["classification"], "RECOVERING")

    def test_classification_is_persisted_into_recovery_info(self):
        factory_state.set_current_task("production", idempotency_key="key1", path=self.state_path)
        startup_check.check_startup_safety(True, state_path=self.state_path, timeline_path=self.timeline_path)
        state = factory_state.load_state(self.state_path)
        self.assertTrue(state["recovery_info"]["interrupted"])
        self.assertIsNotNone(state["recovery_info"]["detected_at"])

    def test_clean_start_never_touches_recovery_info(self):
        result = startup_check.check_startup_safety(False, state_path=self.state_path, timeline_path=self.timeline_path)
        self.assertEqual(result["classification"], "HEALTHY")
        # HEALTHY path never writes -- confirmed by the file not existing yet
        self.assertFalse(os.path.exists(self.state_path))


class TestResolveRecovery(unittest.TestCase):
    def setUp(self):
        self.state_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.state_path):
            os.remove(self.state_path)

    def test_resolve_recovery_clears_interrupted_flag(self):
        state = factory_state.load_state(self.state_path)
        state["recovery_info"] = {"interrupted": True, "detected_at": "t", "evidence": "e", "reason": "r"}
        factory_state.save_state(state, self.state_path)

        startup_check.resolve_recovery(self.state_path)
        state = factory_state.load_state(self.state_path)
        self.assertFalse(state["recovery_info"]["interrupted"])
        self.assertIsNone(state["recovery_info"]["reason"])


if __name__ == "__main__":
    unittest.main()
