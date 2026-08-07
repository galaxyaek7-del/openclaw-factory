"""Tests for commercial_experiments.py (ADR-202, 2026-08-07).

    python -m unittest tests.test_commercial_experiments -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import commercial_experiments as ce


class TestCreateExperiment(unittest.TestCase):
    def test_rejects_unknown_experiment_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "exp.jsonl")
            with self.assertRaises(ce.UnknownExperimentTypeError):
                ce.create_experiment("e1", "not_a_real_type", "h", "b", "c", "m", experiments_path=path)

    def test_valid_type_creates_running_experiment(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "exp.jsonl")
            record = ce.create_experiment("e1", "pricing", "h", "b", "c", "conversion_rate", experiments_path=path)
            self.assertEqual(record["status"], "RUNNING")


class TestEvaluateExperiment(unittest.TestCase):
    def test_not_found_when_never_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "exp.jsonl")
            result = ce.evaluate_experiment("does-not-exist", experiments_path=path)
            self.assertEqual(result["status"], "NOT_FOUND")

    def test_insufficient_data_below_minimum_sample_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "exp.jsonl")
            ce.create_experiment("e1", "pricing", "h", "b", "c", "m", experiments_path=path)
            for _ in range(5):
                ce.record_observation("e1", "baseline", 10.0, experiments_path=path)
                ce.record_observation("e1", "variant", 12.0, experiments_path=path)
            result = ce.evaluate_experiment("e1", experiments_path=path, min_sample_size=30)
            self.assertEqual(result["decision"], "INSUFFICIENT_DATA")
            self.assertEqual(result["confidence"], "INSUFFICIENT_DATA")

    def test_never_declares_success_from_insufficient_data_even_with_a_huge_apparent_lift(self):
        """Regression proof of the directive's own literal rule -- a
        single observation showing a 1000% lift must still be
        INSUFFICIENT_DATA, never ADOPT."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "exp.jsonl")
            ce.create_experiment("e1", "pricing", "h", "b", "c", "m", experiments_path=path)
            ce.record_observation("e1", "baseline", 1.0, experiments_path=path)
            ce.record_observation("e1", "variant", 100.0, experiments_path=path)
            result = ce.evaluate_experiment("e1", experiments_path=path, min_sample_size=30)
            self.assertEqual(result["decision"], "INSUFFICIENT_DATA")

    def test_adopt_decision_once_real_minimum_sample_reached(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "exp.jsonl")
            ce.create_experiment("e1", "pricing", "h", "b", "c", "m", experiments_path=path)
            for _ in range(30):
                ce.record_observation("e1", "baseline", 10.0, experiments_path=path)
                ce.record_observation("e1", "variant", 15.0, experiments_path=path)
            result = ce.evaluate_experiment("e1", experiments_path=path, min_sample_size=30)
            self.assertEqual(result["decision"], "ADOPT")
            self.assertEqual(result["result"]["lift_pct"], 50.0)

    def test_reject_decision_on_negative_lift(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "exp.jsonl")
            ce.create_experiment("e1", "pricing", "h", "b", "c", "m", experiments_path=path)
            for _ in range(30):
                ce.record_observation("e1", "baseline", 10.0, experiments_path=path)
                ce.record_observation("e1", "variant", 5.0, experiments_path=path)
            result = ce.evaluate_experiment("e1", experiments_path=path, min_sample_size=30)
            self.assertEqual(result["decision"], "REJECT")


class TestListExperiments(unittest.TestCase):
    def test_honestly_empty_when_no_experiment_ever_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "exp.jsonl")
            result = ce.list_experiments(experiments_path=path)
            self.assertEqual(result["total"], 0)
            self.assertIn("0 real", result["note"])


if __name__ == "__main__":
    unittest.main()
