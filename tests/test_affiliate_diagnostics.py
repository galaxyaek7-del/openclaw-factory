#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for affiliate/diagnostics.py — the 13 required pre-signal cases."""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate import diagnostics as dg
from affiliate import signals as sig


class TestDiagnosticCases(unittest.TestCase):
    def test_01_no_data_state(self):
        f = dg.funnel_diagnostic()
        self.assertEqual(f["stages"]["EXPOSURE"]["status"], "NO_DATA")
        self.assertEqual(f["stages"]["EXPOSURE"]["evidence"], "UNKNOWN — no impression source on any channel")

    def test_02_unpublished_state(self):
        f = dg.funnel_diagnostic()
        for stage in ("LANDING", "SIGNUP", "PURCHASE", "COMMISSION", "PAYOUT"):
            self.assertEqual(f["stages"][stage]["status"], "NOT_IN_MARKET")

    def test_03_low_traffic_not_content_failure(self):
        f = dg.funnel_diagnostic()
        v = f["stages"]["VIEW"]
        self.assertIn(v["status"], ("LOW_TRAFFIC", "NO_DATA"))
        self.assertNotIn("CONTENT_FAILED", v["status"])

    def test_04_low_click_never_infers_conversion(self):
        f = dg.funnel_diagnostic()
        self.assertEqual(f["stages"]["COMMISSION"]["sample"], 0)
        self.assertNotEqual(f["stages"]["COMMISSION"]["status"], "LOW_CONVERSION")

    def test_05_insufficient_conversion_sample(self):
        b = dg.diagnose_bottleneck()
        self.assertIn(b["bottleneck"], ("NOT_IN_MARKET", "TRACKING_FAILURE", "INSUFFICIENT_DATA"))
        self.assertNotIn(b["bottleneck"], ("OFFER_PROBLEM",))

    def test_06_tracking_failure_holds(self):
        tw = dg.tracking_firewall()
        # EXP_001 (founder-authorized 2026-09-21): 1 registered link -> TRUSTED
        self.assertEqual(tw["status"], "TRUSTED")
        self.assertIn("reason", tw)

    def test_07_stale_evidence_flagged(self):
        dq = dg.data_quality_gate()
        self.assertIn(dq["status"], ("TRUSTWORTHY", "NOT_TRUSTWORTHY"))
        self.assertIn("failures", dq)
        self.assertIn("per_source", dq)

    def test_08_internal_contamination_quarantined(self):
        c = sig.classify_signal({"kind": "click", "note": "bot burst test run"})
        self.assertEqual(c["category"], "INTERNAL_TEST_SIGNAL")
        b = dg.diagnose_bottleneck()
        self.assertNotEqual(b["bottleneck"], "OFFER_PROBLEM")

    def test_09_first_external_signal_advances_once(self):
        r = sig.advance_signal_state("NO_EXTERNAL_SIGNAL", "EXTERNAL_TRAFFIC_SIGNAL")
        self.assertTrue(r["advanced"])
        self.assertTrue(r["diagnostic_event"])
        self.assertEqual(r["state"], "FIRST_EXTERNAL_TRAFFIC")

    def test_10_policy_change_wake_slot_exists(self):
        w = dg.wake_check()
        self.assertIn("fired", w)
        self.assertIsInstance(w["fired"], list)

    def test_11_window_completion_needs_sample(self):
        w = sig.measurement_window("c", "2026-09-20T00:00:00+00:00", 30, 100, 0)
        self.assertEqual(w["status"], "INSUFFICIENT_DATA")

    def test_12_founder_gate_generation(self):
        p = sig.first_signal_protocol({"category": "EXTERNAL_CLICK"})
        self.assertTrue(p["freeze_unnecessary_changes"])
        self.assertTrue(any("FOUNDER" in a for a in p["actions"]))
        self.assertIn("do NOT scale", " ".join(p["actions"]))

    def test_13_financial_immutability(self):
        import json
        fin = json.loads((Path(__file__).resolve().parent.parent / "finance_data.json").read_text(encoding="utf-8"))
        self.assertEqual(fin.get("totalSales"), 0)
        conf = dg.signal_confidence()
        self.assertEqual(conf["level"], "NO_EVIDENCE")


class TestQueueAndFounder(unittest.TestCase):
    def test_14_queue_transitions(self):
        from affiliate import opportunities as opp
        full = {g: "documented evidence text here" for g in opp.EVIDENCE_GATES}
        self.assertEqual(opp.assess_opportunity_status(full)["verdict"], "ACTIVE")
        weak = dict(full, weakened_gates=["buyer_evidence"])
        self.assertEqual(opp.assess_opportunity_status(weak)["verdict"], "DOWNGRADE")
        gone = dict(full)
        del gone["buyer_evidence"]
        self.assertEqual(opp.assess_opportunity_status(gone)["verdict"], "HOLD")
        self.assertEqual(
            opp.assess_opportunity_status(full, program_available=False)["verdict"],
            "HIBERNATE")

    def test_15_founder_single_action(self):
        feb = dg.founder_effort_blocker()
        for k in ("blocker", "why_it_exists", "factory_completed",
                  "factory_can_do", "single_founder_action"):
            self.assertTrue(feb[k])


if __name__ == "__main__":
    unittest.main(verbosity=2)
