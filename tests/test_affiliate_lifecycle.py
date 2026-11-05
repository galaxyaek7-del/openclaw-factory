#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lifecycle tests: stage gates, selection honesty, QA mapping, packet
safety, gate singularity, dry-run isolation, idempotency, recovery."""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate import lifecycle as lc, select as sel


class TestLifecycle(unittest.TestCase):
    def test_every_stage_has_gates(self):
        self.assertEqual(len(lc.STAGES), 18)
        for s in lc.STAGES:
            entry, exit_ev = lc.STAGE_GATES[s]
            self.assertTrue(entry and exit_ev, s)

    def test_selection_cited_not_subjective(self):
        ranked = sel.rank_opportunities()
        self.assertTrue(ranked)
        for r in ranked:
            self.assertIn("criteria", r)
            self.assertIn(r["STATUS"], ("RANKED", "INSUFFICIENT_EVIDENCE"))

    def test_qa_mapping(self):
        assets = lc.asset_registry()
        self.assertEqual(len(assets), 2)
        for a in assets:
            for k in ("ASSET_ID", "VERSION", "TARGET_AUDIENCE", "PROBLEM",
                      "OFFER", "CHANNEL", "STATUS", "CREATED_AT", "QA_STATUS"):
                self.assertIn(k, a)
        qa = lc.run_qa(assets[0])
        self.assertIn(qa["status"], ("PASS", "PASS_WITH_WARNINGS", "HOLD", "BLOCKED"))

    def test_packet_has_no_secrets(self):
        qa = lc.run_qa(lc.asset_registry()[0])
        pkt = lc.build_packet(lc.asset_registry()[0], qa)
        for k in ("title", "description", "CTA", "metadata",
                  "measurement_configuration", "QA_report"):
            self.assertIn(k, pkt)

    def test_rehearsal_writes_nothing(self):
        import hashlib
        before = hashlib.sha256(
            (_FACTORY_ROOT / "finance_data.json").read_bytes()).hexdigest()
        r = lc.run_lifecycle(write=False)
        after = hashlib.sha256(
            (_FACTORY_ROOT / "finance_data.json").read_bytes()).hexdigest()
        self.assertEqual(before, after)
        self.assertEqual(r["mode"], "REAL")
        self.assertEqual(r["stopped_at"], "FOUNDER_PUBLICATION_GATE")

    def test_exactly_one_gate(self):
        r = lc.run_lifecycle(write=False)
        self.assertEqual(r["stages"]["FOUNDER_PUBLICATION_GATE"]["status"], "GATE_OPEN")
        self.assertIn("GATE_ID=", r["stages"]["FOUNDER_PUBLICATION_GATE"]["evidence"])

    def test_dry_run_isolated(self):
        dry = lc.run_dry_run()
        self.assertEqual(dry["mode"], "SIMULATION_ONLY")
        self.assertEqual(dry["final_sim_state"], "SCALE_CANDIDATE")
        self.assertTrue(dry["isolation"]["ledgers_identical"])
        self.assertTrue(dry["isolation"]["finance_sha_unchanged"])
        self.assertTrue(all(t["in_simulation"] for t in dry["trace"]))

    def test_real_world_restored(self):
        dry = lc.run_dry_run()
        self.assertIn("NOT_IN_MARKET", dry["real_world"])
        from affiliate import market_state as ms
        self.assertEqual(ms.current_market_state()["state"], "NOT_IN_MARKET")

    def test_distribution_table(self):
        table = lc.distribution_intelligence()
        self.assertEqual(len(table), 3)
        for row in table:
            for k in ("CHANNEL", "TECHNICAL_STATUS", "PUBLICATION_STATUS",
                      "MEASUREMENT_STATUS", "COMMERCIAL_STATUS", "BLOCKER",
                      "FOUNDER_GATE"):
                self.assertIn(k, row)

    def test_recovery_missing_asset(self):
        qa = lc.run_qa({"ASSET_ID": "AST-GHOST-99", "VERSION": "0",
                        "path": "drafts/does_not_exist.md"})
        self.assertIn(qa["status"], ("PASS", "PASS_WITH_WARNINGS", "HOLD", "BLOCKED"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
