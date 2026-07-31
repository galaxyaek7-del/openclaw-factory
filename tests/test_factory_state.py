"""Tests for factory_state.py (Operational Resilience Architecture, Phase A,
2026-07-18): the Factory State Manager's Python side.

Runs with stdlib unittest. Never touches the real data/factory_state.json —
every test passes an explicit temp path.

    python -m unittest tests.test_factory_state -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import factory_state


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    return path


class TestLoadState(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_missing_file_reads_as_the_safe_default(self):
        state = factory_state.load_state(self.path)
        self.assertIsNone(state["current_task"])
        self.assertEqual(state["pending_retries"], [])

    def test_corrupt_file_reads_as_the_safe_default_never_raises(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        state = factory_state.load_state(self.path)
        self.assertIsNone(state["current_task"])

    def test_non_dict_json_reads_as_the_safe_default(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([1, 2, 3], f)
        state = factory_state.load_state(self.path)
        self.assertEqual(state, factory_state._default_state())

    def test_legacy_file_missing_new_keys_fills_in_safe_defaults(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"current_task": {"name": "x"}}, f)
        state = factory_state.load_state(self.path)
        self.assertEqual(state["current_task"], {"name": "x"})
        self.assertEqual(state["pending_retries"], [])


class TestSaveStateIsAtomic(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)
        tmp_glob = Path(self.path).parent.glob(f"{Path(self.path).name}.tmp-*")
        for p in tmp_glob:
            p.unlink()

    def test_no_tmp_file_left_behind_after_a_real_save(self):
        factory_state.save_state(factory_state._default_state(), self.path)
        self.assertTrue(os.path.exists(self.path))
        leftover = list(Path(self.path).parent.glob(f"{Path(self.path).name}.tmp-*"))
        self.assertEqual(leftover, [])

    def test_save_then_load_round_trips(self):
        state = factory_state._default_state()
        state["active_workflow"] = "test_workflow"
        factory_state.save_state(state, self.path)
        loaded = factory_state.load_state(self.path)
        self.assertEqual(loaded["active_workflow"], "test_workflow")


class TestCurrentTaskLifecycle(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_set_current_task_marks_in_flight(self):
        factory_state.set_current_task("production", step="generate", idempotency_key="key1", path=self.path)
        state = factory_state.load_state(self.path)
        self.assertEqual(state["current_task"]["name"], "production")
        self.assertEqual(state["current_task"]["step"], "generate")
        self.assertEqual(state["active_workflow"], "production")

    def test_clear_current_task_resolves_it(self):
        factory_state.set_current_task("production", path=self.path)
        factory_state.clear_current_task(path=self.path)
        state = factory_state.load_state(self.path)
        self.assertIsNone(state["current_task"])
        # Autonomous Company Runtime (ADR-157, 2026-07-31): a real,
        # pre-existing bug this test didn't catch -- active_workflow was
        # never cleared here, staying permanently "sticky" to whatever
        # task last started even long after it finished.
        self.assertIsNone(state["active_workflow"])

    def test_never_cleared_task_stays_in_flight_this_is_the_crash_evidence(self):
        """The whole point: if the process dies between set and clear, the
        next reader sees exactly this — a real, non-null current_task."""
        factory_state.set_current_task("publishing", idempotency_key="key2", path=self.path)
        state = factory_state.load_state(self.path)
        self.assertIsNotNone(state["current_task"])
        self.assertEqual(state["current_task"]["idempotency_key"], "key2")


class TestCheckpointAndRetryQueue(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_record_checkpoint(self):
        factory_state.record_checkpoint("learning", "key3", path=self.path)
        state = factory_state.load_state(self.path)
        self.assertEqual(state["last_successful_checkpoint"]["stage"], "learning")
        self.assertEqual(state["last_successful_checkpoint"]["idempotency_key"], "key3")

    def test_enqueue_and_due_retries(self):
        factory_state.enqueue_retry("telegram_notify", RuntimeError("ECONNREFUSED"), path=self.path)
        due = factory_state.due_retries(self.path)
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["task"], "telegram_notify")
        self.assertIn("ECONNREFUSED", due[0]["last_error"])

    def test_clear_retry_removes_only_matching_task(self):
        factory_state.enqueue_retry("telegram_notify", "err1", path=self.path)
        factory_state.enqueue_retry("paddle_publish", "err2", path=self.path)
        factory_state.clear_retry("telegram_notify", path=self.path)
        due = factory_state.due_retries(self.path)
        self.assertEqual([r["task"] for r in due], ["paddle_publish"])

    def test_multiple_retries_for_the_same_task_all_queued(self):
        factory_state.enqueue_retry("telegram_notify", "err1", path=self.path)
        factory_state.enqueue_retry("telegram_notify", "err2", path=self.path)
        due = factory_state.due_retries(self.path)
        self.assertEqual(len(due), 2)


class TestExponentialBackoff(unittest.TestCase):
    """Unified Recovery System §3: attempt=1 is due immediately (the
    factory's own ~10min tick cadence already exceeds any sub-minute
    backoff); attempt 2+ escalates 60s, 120s, 240s..., capped at 1h."""

    def test_backoff_seconds_schedule(self):
        self.assertEqual(factory_state._backoff_seconds(1), 0)
        self.assertEqual(factory_state._backoff_seconds(2), 60)
        self.assertEqual(factory_state._backoff_seconds(3), 120)
        self.assertEqual(factory_state._backoff_seconds(4), 240)

    def test_backoff_seconds_caps_at_one_hour(self):
        self.assertEqual(factory_state._backoff_seconds(20), 3600)

    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_first_attempt_is_immediately_due(self):
        factory_state.enqueue_retry("groq_generation", "timeout", path=self.path, attempt=1)
        due = factory_state.due_retries(self.path)
        self.assertEqual(len(due), 1)

    def test_second_attempt_is_not_due_within_the_backoff_window(self):
        factory_state.enqueue_retry("groq_generation", "timeout", path=self.path, attempt=2)
        due = factory_state.due_retries(self.path)
        self.assertEqual(due, [], "a 60s backoff must not be due immediately after enqueueing")

    def test_entry_missing_next_retry_at_is_treated_as_immediately_due(self):
        """Backward compatibility: a legacy entry (written before this
        field existed) must never get stuck forever."""
        state = factory_state.load_state(self.path)
        state["pending_retries"].append({"task": "legacy_task", "last_error": "x"})
        factory_state.save_state(state, self.path)
        due = factory_state.due_retries(self.path)
        self.assertEqual(len(due), 1)


if __name__ == "__main__":
    unittest.main()
