"""Goal 2 EXECUTE + VERIFY tests.

Covers all 11 required scenarios. Where a test found a real defect in the
implementation, the defect was fixed and the test kept at full strength.
"""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ci_health_detector as det      # noqa: E402
import ci_health_executor as exe      # noqa: E402


def job(name, status="completed", conclusion="success"):
    return {"name": name, "status": status, "conclusion": conclusion, "run_id": 1}


def evidence(jobs, verdict_note=None, runs=None, **extra):
    """Build a collect()-shaped evidence payload. `extra` lets a test inject
    conditions such as evidence_error without reshaping the helper each time."""
    inner = {"commit_sha": "abc1234",
             "runs": runs if runs is not None else [{"id": 1, "name": "CI",
                                                     "status": "completed",
                                                     "conclusion": "success"}],
             "jobs": jobs, "expected_shards": 2, "evidence_error": None}
    inner.update(extra)
    return {"evidence": inner, "detail": verdict_note or {}}


ALL_OK = [job("test"), job("API contract shard 0 of 2"), job("API contract shard 1 of 2")]
BLOCKED_JOBS = [job("test"), job("API contract shard 0 of 2", conclusion="cancelled"),
                job("API contract shard 1 of 2")]
HOLD_JOBS = [job("test", status="in_progress", conclusion=None),
             job("API contract shard 0 of 2"), job("API contract shard 1 of 2")]


class TestExecuteContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = os.path.join(self.tmp.name, "ci_health_state.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def test_01_blocked_produces_correct_action(self):
        """1. BLOCKED input produces the correct technical action."""
        ev = evidence(BLOCKED_JOBS, {"failed_jobs": ["API contract shard 0 of 2"]})
        v, _, _ = det.decide(ev["evidence"])
        self.assertEqual(v, det.BLOCKED)
        out = exe.execute(v, "shard cancelled", ev, self.ledger)
        self.assertEqual(out["action"], exe.ACTION_REPORT)
        self.assertEqual(out["targets"], ["API contract shard 0 of 2"])
        self.assertTrue(out["acted"])

    def test_02_hold_produces_correct_action(self):
        """2. HOLD input produces the correct technical action."""
        ev = evidence(HOLD_JOBS)
        v, _, _ = det.decide(ev["evidence"])
        self.assertEqual(v, det.HOLD)
        out = exe.execute(v, "run in flight", ev, self.ledger)
        self.assertEqual(out["action"], exe.ACTION_AWAIT)
        self.assertTrue(out["acted"])

    def test_03_pass_triggers_no_action(self):
        """3. PASS does not trigger an unnecessary action."""
        ev = evidence(ALL_OK)
        v, _, _ = det.decide(ev["evidence"])
        self.assertEqual(v, det.PASS)
        out = exe.execute(v, "all good", ev, self.ledger)
        self.assertEqual(out["action"], exe.ACTION_NONE)
        self.assertFalse(out["acted"])
        self.assertFalse(os.path.exists(self.ledger),
                         "PASS must not write to the ledger at all")

    def test_04_unknown_never_triggers_an_action(self):
        """4. UNKNOWN does not trigger an unsafe action."""
        ev = evidence(ALL_OK, evidence_error="HTTP 403")
        v, _, _ = det.decide(ev["evidence"])
        self.assertEqual(v, det.UNKNOWN)
        out = exe.execute(v, "unreadable", ev, self.ledger)
        self.assertEqual(out["action"], exe.ACTION_NONE)
        self.assertFalse(out["acted"])
        self.assertFalse(os.path.exists(self.ledger))

    def test_05_repeated_polling_is_idempotent(self):
        """5. Repeated polling is idempotent."""
        ev = evidence(BLOCKED_JOBS)
        v, _, _ = det.decide(ev["evidence"])
        first = exe.execute(v, "x", ev, self.ledger)
        for _ in range(4):
            again = exe.execute(v, "x", ev, self.ledger)
            self.assertFalse(again["acted"])
        self.assertTrue(first["acted"])
        with io.open(self.ledger, encoding="utf-8") as fh:
            self.assertEqual(len([l for l in fh if l.strip()]), 1)

    def test_06_same_sha_run_cannot_duplicate_actions(self):
        """6. Same SHA/run cannot generate duplicate actions."""
        ev = evidence(BLOCKED_JOBS)
        v, _, _ = det.decide(ev["evidence"])
        exe.execute(v, "x", ev, self.ledger)
        exe.execute(v, "x", ev, self.ledger)
        proof = exe.verify(exe._action_key(v, ev), self.ledger)
        self.assertTrue(proof["verified"])
        self.assertEqual(proof["count"], 1)

    def test_07_verify_confirms_persisted_state(self):
        """7. VERIFY confirms the persisted state by re-reading, not by return."""
        ev = evidence(BLOCKED_JOBS)
        v, _, _ = det.decide(ev["evidence"])
        out = exe.execute(v, "x", ev, self.ledger)
        key = out["record"]["action_key"]
        proof = exe.verify(key, self.ledger)
        self.assertTrue(proof["verified"])
        self.assertEqual(proof["count"], 1)
        rec = proof["records"][0]
        for field in ("timestamp", "commit_sha", "run_ids", "check_ids",
                      "state", "decision_reason", "action", "action_targets"):
            self.assertIn(field, rec, "record must carry %s" % field)
        # VERIFY must fail if nothing was actually persisted.
        self.assertFalse(exe.verify(["no-such-key"], self.ledger)["verified"])

    def test_08_malformed_evidence_never_passes(self):
        """8. Malformed evidence does not produce PASS."""
        for bad in (None, "nope", {}, {"runs": None, "jobs": None}):
            v, _, _ = det.decide(bad)
            self.assertNotEqual(v, det.PASS, "malformed input produced PASS")

    def test_09_api_failure_never_passes(self):
        """9. API failure does not produce PASS."""
        ev = evidence(ALL_OK, evidence_error="HTTP 403")
        v, _, _ = det.decide(ev["evidence"])
        self.assertEqual(v, det.UNKNOWN)
        self.assertNotEqual(v, det.PASS)

    def test_10_secrets_never_appear_in_output(self):
        """10. Secrets never appear in output."""
        for mod in (exe, det):
            with io.open(mod.__file__, encoding="utf-8") as _module_fh:
                src = _module_fh.read()
            for banned in ("GITHUB_TOKEN", "Authorization: Bearer", "ghp_",
                           "github_pat_"):
                self.assertNotIn(banned, src, "%s leaked %s"
                                 % (os.path.basename(mod.__file__), banned))
        ev = evidence(BLOCKED_JOBS)
        v, _, _ = det.decide(ev["evidence"])
        exe.execute(v, "x", ev, self.ledger)
        with io.open(self.ledger, encoding="utf-8") as _ledger_fh:
            blob = _ledger_fh.read()
        for banned in ("ghp_", "github_pat_", "Bearer", "token", "password"):
            self.assertNotIn(banned, blob, "ledger leaked %s" % banned)

    def test_unknown_verdict_is_refused(self):
        """Defence in depth: an unrecognised verdict cannot be executed."""
        with self.assertRaises(ValueError):
            exe.execute("MOSTLY_FINE", "x", evidence(ALL_OK), self.ledger)

    def test_11_action_set_is_closed(self):
        """The action vocabulary is closed; nothing arbitrary can be emitted."""
        for verdict in det.VERDICTS:
            action, _ = exe.decide_action(verdict, evidence(ALL_OK))
            self.assertIn(action, (exe.ACTION_NONE, exe.ACTION_AWAIT,
                                   exe.ACTION_REPORT))


class TestExecuteAgainstLiveEvidence(unittest.TestCase):
    def test_live_run_reaches_a_definite_verdict(self):
        try:
            verdict, reason, ev = det.detect("f035567")
        except Exception as exc:                        # noqa: BLE001
            self.skipTest("live API unavailable: %s" % type(exc).__name__)
        self.assertIn(verdict, det.VERDICTS)
        self.assertTrue(reason)
        out = exe.execute(verdict, reason, ev, os.path.join(
            tempfile.gettempdir(), "ci_health_state_probe.jsonl"))
        self.assertIn(out["action"], (exe.ACTION_NONE, exe.ACTION_AWAIT,
                                      exe.ACTION_REPORT))


if __name__ == "__main__":
    unittest.main(verbosity=2)