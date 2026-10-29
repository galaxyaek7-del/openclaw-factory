"""lib/customer_evidence.py (the store behind POST /api/customer/interest):
unexpected input, storage failure, and what never leaves the ledger.
Temp ledgers only; the real data/customer_interest.jsonl is never touched."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import customer_evidence as ce  # noqa: E402

GOOD = {"email": "reader@example.org", "message": "Please tell me more about the GPSR checklist.",
        "product_interest": "gpsr-checklist"}


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ledger = Path(self.dir.name) / "interest.jsonl"
        self.rejected = Path(self.dir.name) / "rejected.jsonl"

    def tearDown(self):
        self.dir.cleanup()

    def record(self, payload):
        return ce.record_interest_signal(payload, ledger_path=self.ledger, rejected_ledger_path=self.rejected)


class UnexpectedInput(Base):
    def test_odd_types_are_rejected_without_a_crash(self):
        for payload in (None, [], "text", 42, {"email": ["a@b.org"], "message": {"x": 1}},
                        {"email": None, "message": None}, {}):
            out = self.record(payload)
            self.assertEqual(out["status"], "rejected", repr(payload))
        self.assertFalse(self.ledger.exists())

    def test_oversized_and_control_characters(self):
        self.assertEqual(self.record(dict(GOOD, message="x" * 5000))["status"], "rejected")
        self.assertEqual(self.record(dict(GOOD, email="a" * 3000 + "@example.org"))["status"], "rejected")
        self.assertEqual(self.record(dict(GOOD, email="bad address@example.org"))["status"], "rejected")

    def test_accepted_result_names_the_offer_but_not_the_person(self):
        out = self.record(GOOD)
        self.assertEqual(out["status"], "accepted")
        self.assertEqual(out["product_interest"], "gpsr-checklist")
        self.assertNotIn("reader@example.org", json.dumps(out))

    def test_case_and_whitespace_do_not_defeat_dedup(self):
        self.assertEqual(self.record(GOOD)["status"], "accepted")
        again = dict(GOOD, email="  READER@example.org ", message=GOOD["message"].upper())
        self.assertEqual(self.record(again)["status"], "duplicate")
        self.assertEqual(len(ce.read_signals(self.ledger)), 1)


class Privacy(Base):
    def test_rejections_keep_only_a_hash(self):
        self.record(dict(GOOD, message="short"))
        self.record(GOOD)
        self.record(GOOD)  # duplicate
        text = self.rejected.read_text(encoding="utf-8")
        self.assertNotIn("reader@example.org", text)
        self.assertNotIn("GPSR", text)
        for line in text.splitlines():
            self.assertEqual(set(json.loads(line)), {"received_at", "reason", "classification", "dedup_hash"})

    def test_cli_output_never_echoes_the_address(self):
        env = dict(os.environ)
        code = ("import sys,json; sys.path.insert(0, %r); from lib import customer_evidence as ce; "
                "ce.LEDGER_PATH=ce.Path(%r); ce.REJECTED_LEDGER_PATH=ce.Path(%r); ce.main()"
                % (str(ROOT), str(self.ledger), str(self.rejected)))
        p = subprocess.run([sys.executable, "-c", code, "record"], input=json.dumps(GOOD), capture_output=True,
                           text=True, env=env, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["status"], "accepted")
        self.assertNotIn("reader@example.org", p.stdout + p.stderr)


class SafeFailure(Base):
    def test_a_storage_failure_raises_and_leaves_no_partial_record(self):
        real_open = open

        def failing_open(path, mode="r", *a, **k):
            if str(path) == str(self.ledger) and "a" in mode:
                raise OSError("disk full")
            return real_open(path, mode, *a, **k)

        with mock.patch("builtins.open", failing_open):
            with self.assertRaises(OSError):
                self.record(GOOD)
        self.assertFalse(self.ledger.exists())
        # the lock is released: the next write succeeds
        self.assertEqual(self.record(GOOD)["status"], "accepted")

    def test_cli_rejects_invalid_json_without_writing(self):
        code = ("import sys; sys.path.insert(0, %r); from lib import customer_evidence as ce; "
                "ce.LEDGER_PATH=ce.Path(%r); ce.main()" % (str(ROOT), str(self.ledger)))
        p = subprocess.run([sys.executable, "-c", code, "record"], input="{not json", capture_output=True,
                           text=True, timeout=60)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.loads(p.stdout), {"success": False, "error": "invalid json"})
        self.assertFalse(self.ledger.exists())


if __name__ == "__main__":
    unittest.main()
