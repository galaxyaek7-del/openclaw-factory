"""Tier-1 tests: evidence provenance fields round-trip; old callers unaffected."""
import os
import tempfile
import unittest

import evidence_engine as ee


class TestProvenance(unittest.TestCase):
    def test_new_fields_round_trip(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl")
        tmp.close()
        try:
            rec = ee.record_evidence("TEST", "v70_selftest", "in", "out", 1.0,
                                     True, ledger_path=tmp.name,
                                     producer="pytest", provenance="OBSERVED",
                                     confidence="direct read")
            self.assertEqual(rec["producer"], "pytest")
            self.assertEqual(rec["provenance"], "OBSERVED")
            back = ee.read_evidence(module="v70_selftest", ledger_path=tmp.name)
            self.assertEqual(back[-1]["evidence_id"], rec["evidence_id"])
        finally:
            os.unlink(tmp.name)

    def test_old_style_call_defaults(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl")
        tmp.close()
        try:
            rec = ee.record_evidence("TEST", "v70_selftest", "in", "out", 1.0,
                                     True, ledger_path=tmp.name)
            self.assertEqual(rec["provenance"], "DERIVED")
            self.assertIsNone(rec["producer"])
        finally:
            os.unlink(tmp.name)


if __name__ == "__main__":
    unittest.main()
