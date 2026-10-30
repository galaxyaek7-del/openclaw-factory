"""kids_studio/feedback/record_feedback.py: answers are validated, contact
details are refused, nothing identifies a child, the ledger is git-ignored,
and the summary applies the protocol's continue rule. Temp ledgers only."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "kids_studio" / "feedback"))
import record_feedback as rf  # noqa: E402

GOOD = {"age_band": "4-5", "watched": "yes", "alone": "with_me", "completion": "all", "language": "right", "next": "yes"}


class KidsFeedback(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ledger = Path(self.dir.name) / "kids_feedback.jsonl"

    def tearDown(self):
        self.dir.cleanup()

    def test_a_valid_answer_is_recorded_without_identifying_fields(self):
        rec = rf.make_record("ep01", GOOD, issues="the owl's line is fast", where="YouTube")
        self.assertEqual(set(rec), set(rf.CHOICES) | {"episode", "recorded_at", "issues", "where", "feedback_id"})

    def test_bad_choices_and_contradictions_are_refused(self):
        for bad in ({"age_band": "3"}, {"watched": "maybe"}, {"watched": "no", "completion": "all"}):
            with self.assertRaises(rf.Refused):
                rf.make_record("ep01", dict(GOOD, **bad))
        with self.assertRaises(rf.Refused):
            rf.make_record("episode one", GOOD)

    def test_contact_details_in_free_text_are_refused(self):
        for text in ("call me on +213 555 12 34 56", "write to mum@example.com", "x" * 501):
            with self.assertRaises(rf.Refused):
                rf.make_record("ep01", GOOD, issues=text)

    def test_summary_applies_the_continue_rule(self):
        self.assertFalse(rf.summary(self.ledger)["criteria"]["continue"])
        for alone in ("yes", "with_me", "no"):
            rf.append(rf.make_record("ep01", dict(GOOD, alone=alone)), self.ledger)
        s = rf.summary(self.ledger)
        self.assertEqual(s["responses"], 3)
        self.assertEqual(s["alone"], {"yes": 1, "with_me": 1, "no": 1})
        self.assertTrue(s["criteria"]["continue"])

    def test_the_command_line_refuses_and_records(self):
        base = [sys.executable, str(ROOT / "kids_studio" / "feedback" / "record_feedback.py"), "--ledger", str(self.ledger)]
        ok = base + ["--age-band", "6-8", "--watched", "no", "--alone", "no", "--completion", "did_not_watch",
                     "--language", "too_hard", "--next", "maybe"]
        self.assertEqual(subprocess.run(ok, capture_output=True, timeout=60).returncode, 0)
        bad = ok + ["--where", "ask a@b.co"]
        self.assertEqual(subprocess.run(bad, capture_output=True, timeout=60).returncode, 1)
        self.assertEqual(len(self.ledger.read_text(encoding="utf-8").splitlines()), 1)

    def test_the_real_ledger_is_git_ignored(self):
        r = subprocess.run(["git", "check-ignore", "-q", "--no-index", "data/kids_feedback.jsonl"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
