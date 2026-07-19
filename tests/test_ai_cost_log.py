"""Tests for book_generator.py's real AI-cost logging (ADR-041).

Runs with stdlib unittest (see tests/test_base_arm.py).

    python -m unittest tests.test_ai_cost_log -v
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

import sys
_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import book_generator as bg


class TestLogAiCost(unittest.TestCase):
    def setUp(self):
        fd, self.log_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.log_path)  # start from "file doesn't exist yet"

    def tearDown(self):
        if os.path.exists(self.log_path):
            os.remove(self.log_path)

    def _read_last(self):
        with open(self.log_path, encoding="utf-8") as f:
            lines = [l for l in f.read().split("\n") if l.strip()]
        return json.loads(lines[-1])

    def test_real_usage_computes_real_cost_from_published_groq_rates(self):
        bg._log_ai_cost(
            "llama-3.1-8b-instant",
            {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000, "total_tokens": 2_000_000},
            log_file=self.log_path,
        )
        record = self._read_last()
        # $0.05/M input + $0.08/M output at exactly 1M each = $0.13 total
        self.assertAlmostEqual(record["cost_usd"], 0.13, places=6)
        self.assertEqual(record["prompt_tokens"], 1_000_000)
        self.assertEqual(record["completion_tokens"], 1_000_000)

    def test_unknown_model_logs_tokens_but_no_invented_cost(self):
        bg._log_ai_cost("some-future-model", {"prompt_tokens": 100, "completion_tokens": 50}, log_file=self.log_path)
        record = self._read_last()
        self.assertIsNone(record["cost_usd"])
        self.assertEqual(record["prompt_tokens"], 100)

    def test_missing_usage_never_raises(self):
        try:
            bg._log_ai_cost("llama-3.1-8b-instant", None, log_file=self.log_path)
        except Exception as e:
            self.fail(f"_log_ai_cost raised on missing usage: {e}")
        record = self._read_last()
        self.assertEqual(record["prompt_tokens"], 0)

    def test_context_is_recorded_for_future_per_niche_cost_analysis(self):
        bg._log_ai_cost(
            "llama-3.1-8b-instant", {"prompt_tokens": 10, "completion_tokens": 10}, context={"niche": "test niche"},
            log_file=self.log_path,
        )
        record = self._read_last()
        self.assertEqual(record["context"], {"niche": "test niche"})

    def test_appends_multiple_calls_without_overwriting(self):
        bg._log_ai_cost("llama-3.1-8b-instant", {"prompt_tokens": 1, "completion_tokens": 1}, log_file=self.log_path)
        bg._log_ai_cost("llama-3.1-8b-instant", {"prompt_tokens": 2, "completion_tokens": 2}, log_file=self.log_path)
        with open(self.log_path, encoding="utf-8") as f:
            lines = [l for l in f.read().split("\n") if l.strip()]
        self.assertEqual(len(lines), 2)

    def test_latency_ms_is_recorded_when_provided(self):
        bg._log_ai_cost(
            "llama-3.1-8b-instant", {"prompt_tokens": 10, "completion_tokens": 10}, latency_ms=842,
            log_file=self.log_path,
        )
        record = self._read_last()
        self.assertEqual(record["latency_ms"], 842)

    def test_latency_ms_defaults_to_none_for_backward_compatibility(self):
        bg._log_ai_cost("llama-3.1-8b-instant", {"prompt_tokens": 10, "completion_tokens": 10}, log_file=self.log_path)
        record = self._read_last()
        self.assertIsNone(record["latency_ms"])

    def test_never_raises_even_if_log_dir_cannot_be_created(self):
        # A path with a null byte / invalid character is guaranteed to fail
        # os.makedirs — the function must still not raise.
        try:
            bg._log_ai_cost("llama-3.1-8b-instant", {"prompt_tokens": 1, "completion_tokens": 1}, log_file="\x00/bad/path.jsonl")
        except Exception as e:
            self.fail(f"_log_ai_cost raised on an unwritable path: {e}")


if __name__ == "__main__":
    unittest.main()
