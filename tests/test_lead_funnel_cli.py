import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import lead_funnel as cli  # noqa: E402
import lead_discovery as ld  # noqa: E402


class LeadFunnelCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "pipeline.jsonl")
        # never touch the live evidence ledger
        p = mock.patch("evidence_engine.record_evidence", return_value={"evidence_id": "EV-test"})
        p.start()
        self.addCleanup(p.stop)

    def go(self, *argv):
        return cli.run(cli.build_args(list(argv)))

    def test_dry_run_writes_nothing(self):
        self.assertEqual(0, self.go("move", "--path", self.path, "--lead", "a", "--to", "QUALIFIED", "--source", "fair"))
        self.assertFalse(os.path.exists(self.path))

    def test_new_lead_needs_a_real_source(self):
        self.assertEqual(2, self.go("move", "--path", self.path, "--lead", "a", "--to", "QUALIFIED", "--apply"))
        self.assertIsNone(ld.lead_stage("a", self.path))

    def test_legal_path_is_recorded_and_counted(self):
        self.assertEqual(0, self.go("move", "--path", self.path, "--lead", "a", "--to", "QUALIFIED",
                                    "--source", "met at the fair", "--apply"))
        self.assertEqual(0, self.go("move", "--path", self.path, "--lead", "a", "--to", "CONTACTED", "--apply"))
        self.assertEqual("CONTACTED", ld.lead_stage("a", self.path))
        self.assertEqual(1, ld.funnel_summary(self.path)["counts"]["CONTACTED"])

    def test_skipping_a_stage_is_refused(self):
        self.go("move", "--path", self.path, "--lead", "a", "--to", "QUALIFIED", "--source", "fair", "--apply")
        self.assertEqual(2, self.go("move", "--path", self.path, "--lead", "a", "--to", "WON", "--apply"))
        self.assertEqual("QUALIFIED", ld.lead_stage("a", self.path))

    def test_show_works_on_an_empty_funnel(self):
        self.assertEqual(0, self.go("show", "--path", self.path))


if __name__ == "__main__":
    unittest.main()
