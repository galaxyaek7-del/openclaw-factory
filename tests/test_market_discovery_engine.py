#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V5.7 regression tests: MARKET_DISCOVERY_ENGINE.

Offline, hermetic: temp register files + inline signals only -- never
production data, never network. Proves the ladder discipline (no
promotion without evidence), the gate mapping, and register idempotency.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import market_discovery_engine as M


def _sig(**kw):
    base = {"signal_id": "T-1", "source": "test", "audience": "testers",
            "problem": "test pain", "observed_signal": "someone complained",
            "signal_type": "SIGNAL", "evidence_level": "OBSERVED"}
    base.update(kw)
    return base


class TestLadder(unittest.TestCase):
    def test_levels_in_order(self):
        self.assertEqual(M.LADDER, ("TREND", "SIGNAL", "INTEREST", "INTENT",
                                    "QUALIFIED_DEMAND", "TRANSACTION"))

    def test_trend_never_counts_as_demand(self):
        self.assertEqual(M.classify_level(_sig(signal_type="TREND")), "TREND")
        gates = M.evaluate_gates(signals=[_sig(signal_type="TREND")])
        self.assertEqual(gates[0]["gate"], "GATE_A")

    def test_no_demand_word_without_evidence(self):
        # A DEMAND-typed signal is rejected at record time.
        d = tempfile.mkdtemp()
        p = str(Path(d) / "reg.jsonl")
        res = M.record_signal(_sig(signal_type="DEMAND"), path=p)
        self.assertFalse(res["recorded"])

    def test_indirect_intent_demoted_to_interest(self):
        s = _sig(signal_type="INTENT",
                 buying_intent_indicator="INDIRECT (guides monetize leads)")
        self.assertEqual(M.classify_level(s), "INTEREST")

    def test_interest_without_intent_stays(self):
        self.assertEqual(M.classify_level(_sig(signal_type="INTEREST")),
                         "INTEREST")

    def test_unknown_type_falls_to_signal(self):
        self.assertEqual(M.classify_level(_sig(signal_type="???")), "SIGNAL")


class TestRegister(unittest.TestCase):
    def test_idempotent_by_signal_id(self):
        d = tempfile.mkdtemp()
        p = str(Path(d) / "reg.jsonl")
        self.assertTrue(M.record_signal(_sig(), path=p)["recorded"])
        dup = M.record_signal(_sig(), path=p)
        self.assertFalse(dup["recorded"])
        self.assertEqual(dup["reason"], "DUPLICATE_EVENT_IGNORED")

    def test_missing_fields_rejected(self):
        d = tempfile.mkdtemp()
        res = M.record_signal({"signal_id": "T-9"}, path=str(Path(d) / "r.jsonl"))
        self.assertFalse(res["recorded"])
        self.assertIn("missing fields", res["reason"])


class TestGates(unittest.TestCase):
    def test_empty_register_is_gate_a(self):
        gates = M.evaluate_gates(signals=[])
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0]["gate"], "GATE_A")

    def test_signal_only_is_gate_b(self):
        gates = M.evaluate_gates(signals=[_sig()])
        self.assertEqual(gates[0]["gate"], "GATE_B")
        self.assertEqual(gates[0]["action"], "DEEPER_DISCOVERY")

    def test_interest_is_gate_c(self):
        gates = M.evaluate_gates(signals=[_sig(signal_type="INTEREST")])
        self.assertEqual(gates[0]["gate"], "GATE_C")
        self.assertEqual(gates[0]["action"], "TEST_OFFER")

    def test_live_register_summary_shape(self):
        s = M.discovery_summary()
        self.assertGreaterEqual(s["total_signals"], 1)
        self.assertFalse(s["demand_word_used"])
        self.assertTrue(s["gates"])
        self.assertGreaterEqual(len(s["unknowns"]), 1)
        for g in s["gates"]:
            self.assertIn(g["gate"], ("GATE_A", "GATE_B", "GATE_C", "GATE_D", "GATE_E"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
