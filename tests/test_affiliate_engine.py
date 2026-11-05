#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate engine tests (offline; live revalidation ran separately)."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate import aff_lifecycle as al, economics as ec
from affiliate import aff_ledger as led, attribution as at


def prog(vstatus="VERIFIED", scoring="PROMISING", comm="5%"):
    return {"opportunity_id": "CO-test",
            "record": {"fields": {
                "verification_status": {"value": vstatus},
                "commission_value": {"value": comm}}},
            "scoring": {"category": scoring}}


class TestAffEngine(unittest.TestCase):
    def test_funnel_parks_without_evidence(self):
        s = al.stage_of(prog())
        self.assertEqual(s["stage"], "OFFER_QUALIFIED")
        # PARTIAL verification is strict-parked at DISCOVERED (incomplete proof)
        s2 = al.stage_of(prog(vstatus="PARTIAL", scoring="WEAK"))
        self.assertEqual(s2["stage"], "PROGRAM_DISCOVERED")

    def test_clicks_never_commissions(self):
        s = al.stage_of(prog(), clicks=5)
        self.assertEqual(s["stage"], "CLICK_OBSERVED")
        self.assertNotIn("COMMISSION", s["stage"])

    def test_gate_names_missing(self):
        g = al.advance_allowed("CLICK_OBSERVED", {})
        self.assertFalse(g["allowed"])
        self.assertIn("conversion_event", g["reason"])
        g2 = al.advance_allowed("CLICK_OBSERVED", {"conversion_event": "x"})
        self.assertTrue(g2["allowed"])

    def test_economics_split(self):
        m = ec.model(prog())
        self.assertEqual(m["commission_pct"]["source"], "OBSERVED")
        self.assertEqual(m["average_order_value"]["source"], "UNKNOWN")
        self.assertIsNone(m["commission_per_conversion"]["value"])
        m2 = ec.model(prog(comm=None))
        self.assertEqual(m2["verdict"], "ECONOMICS_UNKNOWN")

    def test_rank_unknown_last(self):
        ranked = ec.select_rank([ec.model(prog(comm=None)), ec.model(prog())])
        self.assertEqual(ranked[0]["verdict"], "QUALIFIED_FOR_TEST")

    def test_ledger_guards(self):
        p = Path(tempfile.mkdtemp()) / "aff.jsonl"
        with self.assertRaises(led.LedgerError):
            led.record_commission({"source": "test", "verified": True,
                                   "transaction_id": "t"}, p)
        with self.assertRaises(led.LedgerError):
            led.record_commission({"source": "external", "verified": False,
                                   "transaction_id": "t"}, p)
        r = led.record_commission({"source": "external", "verified": True,
                                   "transaction_id": "t1", "program": "CO-x",
                                   "commission": 5}, p)
        self.assertEqual(r["commission_status"], "PENDING")
        t = led.totals(p)
        self.assertEqual(t["pending"], 1)
        self.assertEqual(t["confirmed"], 0)
        c = led.confirm_commission("t1", p)
        self.assertTrue(c["ok"] and not c["already"])
        c2 = led.confirm_commission("t1", p)
        self.assertTrue(c2["already"])
        dup = led.record_commission({"source": "external", "verified": True,
                                     "transaction_id": "t1"}, p)
        self.assertFalse(dup["recorded"])

    def test_attribution_internal(self):
        rows = [{"referrer": None, "note": "burst"}, {"referrer": None}]
        c = at.classify_clicks(rows)
        self.assertEqual(c["ATTRIBUTED"], 0)
        self.assertEqual(c["UNATTRIBUTED"], 2)

    def test_synergy_ids_real(self):
        from affiliate import intelligence as I
        ids = {r.get("opportunity_id") for r in I.portfolio_intelligence()}
        for s in at.SYNERGIES:
            if s["program"].startswith("CO-"):
                self.assertIn(s["program"], ids, s["program"])

    def test_url_health_mocked(self):
        from affiliate import healthcheck as h
        with patch("urllib.request.urlopen", side_effect=TimeoutError("x")):
            out = h.url_health(["https://example.com/x"])
            self.assertFalse(out[0]["ok"])

    def test_revalidation_record(self):
        import json
        r = json.loads((_FACTORY_ROOT / "data" / "affiliate_revalidation_2026-09-21.json").read_text(encoding="utf-8"))
        self.assertEqual(r["programs"], 17)
        self.assertTrue(all("NEXT_ACTION" in t for t in r["table"]))


class TestTowerBlock(unittest.TestCase):
    def test_affiliate_block_shape(self):
        from affiliate import control_tower as ct
        b = ct.affiliate_block()
        for k in ("ACTIVE_PROGRAMS", "VERIFIED_PROGRAMS", "ACTIVE_LINKS",
                  "VERIFIED_CONVERSIONS", "PENDING_COMMISSIONS",
                  "CONFIRMED_COMMISSIONS", "CONFIRMED_PAYOUTS",
                  "VERIFIED_AFFILIATE_REVENUE", "BOTTLENECK", "NEXT_SAFE_ACTION"):
            self.assertIn(k, b, k)
        # EXP_001 (founder-authorized 2026-09-21): first link live
        self.assertEqual(b["ACTIVE_LINKS"], 1)
        self.assertEqual(b["VERIFIED_CONVERSIONS"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
