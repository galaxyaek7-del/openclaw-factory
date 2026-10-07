"""Goal 2 DETECT/DECIDE tests.

Twelve required cases are covered explicitly, named below so the mapping to the
specification is auditable rather than implied.
"""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ci_health_detector as det   # noqa: E402


def job(name, status="completed", conclusion="success", run_id=1):
    return {"name": name, "status": status, "conclusion": conclusion, "run_id": run_id}


def run(rid, name="CI", status="completed", conclusion="success"):
    return {"id": rid, "name": name, "status": status, "conclusion": conclusion}


def evidence(jobs, runs=None, shards=2, **extra):
    ev = {"commit_sha": "abc1234", "runs": runs if runs is not None
          else [run(1)], "jobs": jobs, "expected_shards": shards,
          "evidence_error": None}
    ev.update(extra)
    return ev


ALL_OK = [job("test"), job("API contract shard 0 of 2"), job("API contract shard 1 of 2")]


class TestDecideRules(unittest.TestCase):
    def test_01_all_required_pass_is_pass(self):
        """1. All required checks PASS -> PASS"""
        v, why, _ = det.decide(evidence(list(ALL_OK)))
        self.assertEqual(v, det.PASS, why)

    def test_02_one_required_check_fails_is_blocked(self):
        """2. One required check FAIL -> BLOCKED"""
        jobs = [job("test"),
                job("API contract shard 0 of 2", conclusion="failure"),
                job("API contract shard 1 of 2")]
        v, why, d = det.decide(evidence(jobs))
        self.assertEqual(v, det.BLOCKED, why)
        self.assertIn("API contract shard 0 of 2", d.get("failed_jobs", []))

    def test_03_job_still_running_is_hold(self):
        """3. Job still running -> HOLD"""
        jobs = [job("test", status="in_progress", conclusion=None),
                job("API contract shard 0 of 2"), job("API contract shard 1 of 2")]
        v, why, _ = det.decide(evidence(jobs))
        self.assertEqual(v, det.HOLD, why)

    def test_04_required_conclusion_missing_is_unknown(self):
        """4. Required conclusion missing -> UNKNOWN (never PASS)"""
        jobs = [job("test", status="completed", conclusion=None),
                job("API contract shard 0 of 2"), job("API contract shard 1 of 2")]
        v, why, d = det.decide(evidence(jobs))
        self.assertEqual(v, det.UNKNOWN, why)
        self.assertIn("test", d.get("undecided_jobs", []))

    def test_05_cancellation_is_blocked(self):
        """5. Cancellation -> BLOCKED"""
        jobs = [job("test"), job("API contract shard 0 of 2", conclusion="cancelled"),
                job("API contract shard 1 of 2")]
        v, why, _ = det.decide(evidence(jobs))
        self.assertEqual(v, det.BLOCKED, why)

    def test_06_timeout_is_blocked(self):
        """6. Timeout -> BLOCKED"""
        jobs = [job("test"), job("API contract shard 0 of 2", conclusion="timed_out"),
                job("API contract shard 1 of 2")]
        v, why, _ = det.decide(evidence(jobs))
        self.assertEqual(v, det.BLOCKED, why)

    def test_07_empty_annotations_with_success_is_still_pass(self):
        """7. Empty annotations but successful checks -> PASS.

        Annotations are diagnostic, not load-bearing. Every required conclusion
        was independently observed as success, so PASS is earned on the jobs,
        not on the presence of an annotation.
        """
        jobs = list(ALL_OK)
        v, why, _ = det.decide(evidence(jobs, annotations=[]))
        self.assertEqual(v, det.PASS, why)

    def test_08_missing_required_job_is_unknown(self):
        """8. Missing required check -> UNKNOWN"""
        jobs = [job("API contract shard 0 of 2"), job("API contract shard 1 of 2")]
        v, why, _ = det.decide(evidence(jobs, shards=2))
        self.assertEqual(v, det.UNKNOWN, why)
        self.assertIn("test", why)

    def test_08b_shard_count_mismatch_is_unknown(self):
        """8b. Fewer shards than declared -> UNKNOWN, never PASS."""
        jobs = [job("test"), job("API contract shard 0 of 2")]
        v, why, _ = det.decide(evidence(jobs, shards=2))
        self.assertEqual(v, det.UNKNOWN, why)

    def test_10_evidence_unreadable_is_unknown(self):
        """10. API/transport error -> UNKNOWN, never PASS."""
        ev = evidence(list(ALL_OK), evidence_error="HTTP 403")
        v, why, _ = det.decide(ev)
        self.assertEqual(v, det.UNKNOWN, why)

    def test_11_malformed_response_is_unknown(self):
        """11. Malformed API response -> UNKNOWN."""
        for bad in ("not a dict", {"runs": "nope", "jobs": []}, {}):
            v, _, _ = det.decide(bad)
            self.assertEqual(v, det.UNKNOWN, "malformed input gave %s" % v)

    def test_no_runs_is_unknown(self):
        self.assertEqual(det.decide(evidence(list(ALL_OK), runs=[]))[0], det.UNKNOWN)

    def test_run_level_failure_is_blocked(self):
        jobs = list(ALL_OK)
        v, why, _ = det.decide(evidence(jobs, runs=[run(1, conclusion="failure")]))
        self.assertEqual(v, det.BLOCKED, why)


class TestIdempotency(unittest.TestCase):
    def test_09_same_evidence_twice_records_once(self):
        """9. Same SHA/run processed twice -> no duplicate state/action."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.jsonl")
            ev = evidence(list(ALL_OK))
            first = det.record_state(det.PASS, "all good", {"evidence": ev}, path)
            second = det.record_state(det.PASS, "all good", {"evidence": ev}, path)
            self.assertTrue(first["recorded"])
            self.assertFalse(second["recorded"])
            with io.open(path, encoding="utf-8") as fh:
                lines = [l for l in fh if l.strip()]
            self.assertEqual(len(lines), 1, "ledger must not grow on re-poll")

    def test_verdict_change_does_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.jsonl")
            ev = {"commit_sha": "abc1234", "runs": [run(1)], "jobs": list(ALL_OK),
                  "expected_shards": 2}
            det.record_state(det.PASS, "all good", {"evidence": ev}, path)
            again = det.record_state(det.BLOCKED, "shard failed", {"evidence": ev}, path)
            self.assertTrue(again["recorded"], "a real transition must be recorded")


class TestSecretHygiene(unittest.TestCase):
    def test_12_no_secret_values_appear_in_output(self):
        """12. Secret values never appear in output."""
        src = io.open(det.__file__, encoding="utf-8").read()
        for banned in ("GITHUB_TOKEN", "Authorization: Bearer", "ghp_", "github_pat_"):
            self.assertNotIn(banned, src,
                             "detector must contain no credential handling: %s" % banned)

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.jsonl")
            ev = {"commit_sha": "abc1234", "runs": [run(1)], "jobs": list(ALL_OK),
                  "expected_shards": 2}
            det.record_state(det.PASS, "ok", {"evidence": ev}, path)
            blob = io.open(path, encoding="utf-8").read()
            for banned in ("ghp_", "github_pat_", "Bearer", "token"):
                self.assertNotIn(banned, blob, "ledger leaked %s" % banned)

    def test_json_output_is_serialisable(self):
        v, why, payload = det.detect("f244f43")
        self.assertIn(v, det.VERDICTS)
        json.dumps(payload)


class TestAgainstRealEvidence(unittest.TestCase):
    """Detects against the live public API. Read-only, never asserts GREEN --
    it asserts only that the detector reaches a definite, valid verdict."""

    def test_live_head_commit_yields_a_definite_verdict(self):
        try:
            v, why, payload = det.detect("f244f43")
        except Exception as exc:                       # noqa: BLE001
            self.skipTest("live API unavailable: %s" % type(exc).__name__)
        self.assertIn(v, det.VERDICTS)
        self.assertTrue(why)
        self.assertIsInstance(payload.get("evidence"), dict)


if __name__ == "__main__":
    unittest.main(verbosity=2)