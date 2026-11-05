"""GF-ROS Milestone 2: evidence lineage fields + idempotent ingestion.

Every external record must be traceable to its source and must never be
appended twice for the same (source_system, source_record_id, evidence_type).
Old callers must be unaffected.
"""
import json
import os
import tempfile
import unittest

import evidence_engine as ee


class TestEvidenceLineage(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def _rows(self):
        with open(self.path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def _record(self, **kwargs):
        base = dict(evidence_type="FINANCIAL", module="m", input_summary="in",
                    output_summary="out", duration_ms=1.0, success=True,
                    ledger_path=self.path)
        base.update(kwargs)
        return ee.record_evidence(**base)

    def test_new_fields_round_trip(self):
        rec = self._record(source_system="gumroad", source_record_id="sale_1",
                           observed_at="2026-11-01T00:00:00+00:00",
                           verification_status="VERIFIED",
                           reconciliation_status="MATCHED",
                           raw_reference="data/finance_data.json#sale_1")
        self.assertEqual(rec["source_system"], "gumroad")
        self.assertEqual(rec["source_record_id"], "sale_1")
        self.assertEqual(rec["verification_status"], "VERIFIED")
        self.assertEqual(rec["reconciliation_status"], "MATCHED")
        self.assertIsNotNone(rec["ingested_at"])
        back = ee.read_evidence(module="m", ledger_path=self.path)[-1]
        self.assertEqual(back["evidence_id"], rec["evidence_id"])

    def test_replayed_export_is_not_double_counted(self):
        first = self._record(source_system="gumroad", source_record_id="sale_1",
                             verification_status="VERIFIED", reconciliation_status="MATCHED")
        second = self._record(source_system="gumroad", source_record_id="sale_1",
                              verification_status="VERIFIED", reconciliation_status="MATCHED")
        self.assertEqual(first["evidence_id"], second["evidence_id"])
        self.assertEqual(len(self._rows()), 1)

    def test_same_source_id_different_type_is_a_new_record(self):
        self._record(evidence_type="FINANCIAL", source_system="paddle",
                     source_record_id="txn_1")
        self._record(evidence_type="TEST", source_system="paddle",
                     source_record_id="txn_1")
        self.assertEqual(len(self._rows()), 2)

    def test_no_source_id_is_never_deduplicated(self):
        self._record()
        self._record()
        self.assertEqual(len(self._rows()), 2)

    def test_unknown_verification_status_rejected(self):
        with self.assertRaises(ValueError):
            self._record(source_system="x", source_record_id="1",
                         verification_status="PROBABLY")

    def test_unknown_reconciliation_status_rejected(self):
        with self.assertRaises(ValueError):
            self._record(reconciliation_status="MAYBE")

    def test_old_style_call_gets_none_lineage(self):
        rec = self._record()
        self.assertIsNone(rec["source_system"])
        self.assertIsNone(rec["source_record_id"])
        self.assertIsNone(rec["verification_status"])
        self.assertIsNone(rec["reconciliation_status"])

    def test_find_evidence_scoped_by_type(self):
        self._record(evidence_type="FINANCIAL", source_system="amazon",
                     source_record_id="order_9")
        self.assertIsNotNone(ee.find_evidence("amazon", "order_9", ledger_path=self.path))
        self.assertIsNotNone(ee.find_evidence("amazon", "order_9",
                                              evidence_type="FINANCIAL", ledger_path=self.path))
        self.assertIsNone(ee.find_evidence("amazon", "order_9",
                                           evidence_type="CUSTOMER", ledger_path=self.path))
        self.assertIsNone(ee.find_evidence("amazon", "missing", ledger_path=self.path))


if __name__ == "__main__":
    unittest.main()
