#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Security & integrity tests for lib/commission_attribution.py (ANALYSIS ledger only).

These tests verify: no-PII, duplicate protection, concurrency-safe append,
ledger integrity, crash/anomaly/malformed/corruption handling. They NEVER touch
the real financial truth and use a temporary ledger path.
"""

import os
import sys
import tempfile
import threading
import unittest

# Appended, not inserted first: lib/ holds http.py, which at the front of
# sys.path shadows the standard http package for every later test in the same
# process (2026-10-30: three test_commission_engine tests failed with "http is
# not a package" when this file ran first).
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lib"))

import commission_attribution as ca  # noqa: E402


class TestCommissionAttribution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.ledger = os.path.join(self.tmp, "commission_attribution_log.jsonl")
        self.lock = self.ledger + ".lock"
        ca.ATTRIBUTION_PATH = type(ca.ATTRIBUTION_PATH)(self.ledger)
        ca.ATTRIBUTION_LOCK = type(ca.ATTRIBUTION_LOCK)(self.lock)

    def _anon(self):
        return ca.new_anon_id()

    def test_no_pii_shape(self):
        r = ca.record_event(self._anon(), "affiliate_click", "p1", "test")
        self.assertTrue(r["ok"])
        evt = r["event"]
        self.assertNotIn("email", evt)
        self.assertNotIn("ip", evt)
        self.assertNotIn("name", evt)
        self.assertEqual(evt["bot_status"], "UNKNOWN")

    def test_duplicate_protection(self):
        a = self._anon()
        self.assertTrue(ca.record_event(a, "affiliate_click", "p1", "test")["ok"])
        dup = ca.record_event(a, "affiliate_click", "p1", "test")
        self.assertFalse(dup["ok"])
        self.assertEqual(dup["error"], "duplicate")

    def test_malformed_inputs_rejected(self):
        self.assertFalse(ca.record_event("", "affiliate_click", "p1")["ok"])
        self.assertFalse(ca.record_event(self._anon(), "bogus_event", "p1")["ok"])
        self.assertFalse(ca.record_event(self._anon(), "affiliate_click", "")["ok"])
        self.assertFalse(ca.record_event(self._anon(), "affiliate_click", "p1", "", -5)["ok"])
        # ledger must remain empty
        self.assertEqual(ca.read_ledger()["total_events"], 0)

    def test_concurrency_no_loss(self):
        anons = [self._anon() for _ in range(50)]
        errors = []

        def worker(i):
            try:
                ca.record_event(anons[i % 50], "affiliate_click", f"p{i % 7}")
            except Exception as e:  # pragma: no cover
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # 50 unique anon_ids * 7 products = 350 possible; with duplicates within window some dropped,
        # but NONE should be lost (atomic append). Total parsed must equal file line count.
        ledger = ca.read_ledger()
        with open(self.ledger, "r", encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
        self.assertEqual(ledger["total_events"], len(lines))
        self.assertEqual(len(errors), 0)

    def test_corruption_resistance(self):
        # write a corrupt trailing line then a valid event
        with open(self.ledger, "a", encoding="utf-8") as f:
            f.write("{ this is not valid json\n")
        r = ca.record_event(self._anon(), "affiliate_click", "p1", "test")
        self.assertTrue(r["ok"])
        ledger = ca.read_ledger()
        # valid event counted; corrupt line skipped, not fatal
        self.assertEqual(ledger["total_events"], 1)

    def test_anomaly_flag(self):
        a = self._anon()
        # fire many DISTINCT events quickly (vary product so dedup doesn't suppress) -> burst anomaly
        flagged = False
        for i in range(ca.BURST_THRESHOLD + 1):
            r = ca.record_event(a, "affiliate_click", f"pX{i}")
            if r.get("ok") and r["event"].get("anomaly"):
                flagged = True
        self.assertTrue(flagged)

    def test_server_route_event_types_accepted(self):
        # The real server.js customer-site route emits content_view /
        # outbound_click into the same ANALYSIS ledger; the validator must
        # accept the actual producer vocabulary (analysis only, never revenue).
        for et in ("content_view", "outbound_click"):
            r = ca.record_event(self._anon(), et, "p1", "test")
            self.assertTrue(r["ok"], et)
        self.assertFalse(ca.record_event(self._anon(), "bogus_event", "p1")["ok"])

    def test_read_ledger_no_pii(self):
        ca.record_event(self._anon(), "affiliate_click", "p1", "test")
        summary = ca.read_ledger()
        self.assertFalse(summary["has_pii"])
        self.assertIn("affiliate_click", summary["by_type"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
