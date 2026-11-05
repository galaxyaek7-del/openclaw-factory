#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Autonomy upgrade tests: state machine, gates, firewall, anomalies,
experiments, assets, maintenance, loop idempotency, publication truth."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate import market_state as ms, gates as gt, anomalies as an
from affiliate import firewall as fw, experiments as xp, assets as at
from affiliate import maintenance as mn, loop as lp, diagnostics as dg


class TestStateMachine(unittest.TestCase):
    def test_transition_needs_evidence(self):
        r = ms.transition("PUBLICATION_GATE", "publication_confirmed", {})
        self.assertFalse(r["advanced"])
        r2 = ms.transition("PUBLICATION_GATE", "publication_confirmed",
                           {"confirmation": "x"})
        self.assertTrue(r2["advanced"])
        self.assertEqual(r2["state"], "MARKET_ACTIVE")

    def test_transition_wrong_state(self):
        r = ms.transition("NOT_IN_MARKET", "publication_confirmed",
                          {"confirmation": "x"})
        self.assertFalse(r["advanced"])

    def test_draft_is_not_publication(self):
        pub = ms.publication_status()
        self.assertEqual(pub["overall"], "PUBLICATION_NOT_CONFIRMED")
        self.assertEqual(ms.current_market_state()["state"], "NOT_IN_MARKET")

    def test_not_in_market_vs_low_traffic(self):
        b = dg.diagnose_bottleneck()
        self.assertEqual(b["bottleneck"], "NOT_IN_MARKET")
        self.assertNotEqual(b["bottleneck"], "LOW_TRAFFIC")


class TestGates(unittest.TestCase):
    def test_packet_shape_and_dedupe(self):
        p1 = gt.publication_gate_packet()
        for k in ("GATE_ID", "ACTION_REQUIRED", "WHY_REQUIRED", "CURRENT_STATE",
                  "EVIDENCE", "RISK", "COST", "EXPECTED_EFFECT",
                  "EXACT_HUMAN_ACTION", "POST_ACTION_VERIFICATION",
                  "ROLLBACK_IF_APPLICABLE"):
            self.assertIn(k, p1)
        p2 = gt.publication_gate_packet()
        self.assertEqual(p1["GATE_ID"], p2["GATE_ID"])


class TestFirewall(unittest.TestCase):
    def test_blocks_tests_mocks_internal(self):
        for ev in ({"source": "test", "verified": True, "transaction_id": "t1"},
                   {"source": "external", "verified": False, "transaction_id": "t1"},
                   {"source": "external", "verified": True},
                   {"source": "internal"}, {}):
            with self.assertRaises(fw.CommercialTruthFirewallError):
                fw.assert_write_allowed(ev)

    def test_allows_real_external(self):
        r = fw.assert_write_allowed({"source": "external", "verified": True,
                                     "transaction_id": "txn_1"})
        self.assertTrue(r["allowed"])

    def test_ledger_integrity_zero(self):
        self.assertTrue(fw.ledger_integrity()["ok"])


class TestAnomalies(unittest.TestCase):
    def test_detects_known_conditions_no_critical(self):
        rows = {
            "affiliate_clicks.jsonl": [
                {"timestamp": "2026-10-21T00:00:00+00:00", "referrer": None},
                {"timestamp": "2026-10-21T00:01:00+00:00", "referrer": None},
            ],
            "affiliate_page_views.jsonl": [
                {"timestamp": "2026-10-21T00:00:00+00:00"},
            ],
            "commission_attribution_log.jsonl": [{"i": i} for i in range(1001)],
        }
        with patch.object(an, "_read_rows", side_effect=rows.__getitem__):
            r = an.detect_anomalies()
        kinds = {f["kind"] for f in r["findings"]}
        self.assertIn("quarantined_flood", kinds)
        self.assertIn("clicks_exceed_views", kinds)
        self.assertFalse(r["automation_hold"])
        self.assertEqual(r["critical"], [])


class TestExperimentsAssets(unittest.TestCase):
    def test_no_experiment_without_sample(self):
        r = xp.propose_experiment()
        self.assertIsNone(r["proposal"])

    def test_lifecycle_order(self):
        self.assertFalse(xp.experiment_lifecycle(
            {"history": ["RUNNING", "HYPOTHESIS"]})["valid"])
        self.assertTrue(xp.experiment_lifecycle(
            {"history": ["HYPOTHESIS", "BASELINE"]})["valid"])

    def test_reuse_before_new(self):
        self.assertTrue(at.DO_NOT_CLONE_WITHOUT_EVIDENCE)
        r = at.find_reuse_candidates("social post")
        self.assertTrue(r["candidates"])
        self.assertIn("NOT justified", r["verdict"])


class TestMaintenanceLoop(unittest.TestCase):
    def test_sweep_readonly(self):
        r = mn.sweep()
        self.assertEqual(r["repairs"], [])
        self.assertTrue(r["checks"])

    def test_loop_idempotent(self):
        first = lp.run_cycle()
        second = lp.run_cycle()
        self.assertTrue(second["idempotent_repeat"])
        self.assertEqual(first["fingerprint"], second["fingerprint"])

    def test_loop_writes_never_touch_protected(self):
        import json
        fin = json.loads((_FACTORY_ROOT / "finance_data.json").read_text(encoding="utf-8"))
        self.assertEqual(fin.get("totalSales"), 0)

    def test_self_awareness_shape(self):
        a = ms.self_awareness()
        for k in ("CURRENT_STATE", "WHY_THIS_STATE", "CURRENT_BOTTLENECK",
                  "BOTTLENECK_CONFIDENCE", "AVAILABLE_ACTIONS", "SAFE_AUTOMATIONS",
                  "FOUNDER_GATES", "NEXT_WAKE_EVENT", "NEXT_MEASUREMENT_WINDOW",
                  "LAST_EVIDENCE", "EVIDENCE_FRESHNESS"):
            self.assertIn(k, a)

    def test_bottleneck_engine_shape(self):
        b = dg.bottleneck_engine()
        for k in ("PRIMARY_BOTTLENECK", "SECONDARY_BOTTLENECKS", "EVIDENCE",
                  "CONFIDENCE", "RECOMMENDED_NEXT_ACTION", "AUTOMATION_LEVEL",
                  "FOUNDER_GATE_REQUIRED"):
            self.assertIn(k, b)
        self.assertEqual(b["PRIMARY_BOTTLENECK"], "NO_PUBLICATION")

    def test_signal_quality_ladder(self):
        q = dg.signal_quality()
        self.assertEqual(q["level"], "NO_EVIDENCE")
        self.assertEqual(len(q["ladder"]), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
