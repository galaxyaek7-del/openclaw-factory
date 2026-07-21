"""Tests for department_events.py (EOS Phase 2, Round 2, 2026-07-19):
the Python-side shared JSONL correlation-index envelope.

Runs with stdlib unittest. Every function reads/writes only temp-file-
isolated paths -- never the real data/department_events.jsonl.

    python -m unittest tests.test_department_events -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import department_events as de


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestEmit(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_unknown_department_raises(self):
        with self.assertRaises(ValueError):
            de.emit("not_a_real_department", "some.event", path=self.path)

    def test_real_department_writes_a_real_envelope(self):
        record = de.emit("golden_hunter", "opportunity.attempted", ref_id="niche-x",
                          source_log="data/golden_hunter_events.jsonl", summary="test", path=self.path)
        self.assertEqual(record["department"], "golden_hunter")
        self.assertIn("event_id", record)
        self.assertIn("emitted_at", record)
        entries = de.read_events(path=self.path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["ref_id"], "niche-x")

    def test_never_duplicates_business_data_envelope_only(self):
        record = de.emit("ai_capability_manager", "capability.request_logged", ref_id="req-1", path=self.path)
        # Envelope-only guarantee: no arbitrary business fields beyond the schema.
        self.assertEqual(set(record.keys()), {"event_id", "emitted_at", "department", "event_type", "ref_id", "source_log", "summary"})

    def test_append_only_never_overwrites(self):
        de.emit("recovery", "recovery.action_taken", path=self.path)
        de.emit("recovery", "recovery.action_taken", path=self.path)
        entries = de.read_events(path=self.path)
        self.assertEqual(len(entries), 2)

    def test_write_failure_degrades_honestly_never_throws(self):
        record = de.emit("golden_hunter", "x", path="\x00/bad/path.jsonl")
        self.assertTrue(record.get("_log_failed"))


class TestReadEvents(unittest.TestCase):
    def test_missing_file_reads_as_empty_never_throws(self):
        entries = de.read_events(path="/no/such/department_events.jsonl")
        self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main()
