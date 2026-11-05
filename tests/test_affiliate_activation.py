#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the affiliate activation layer (read-only modules only).
No network. No ledger writes (notify dedupe uses a temp state path)."""
import json
import unittest

from affiliate import registry, priority, performance
from affiliate import daily_health as dh
from affiliate import reconcile as rc


class TestRegistry(unittest.TestCase):
    def test_summary_shape(self):
        s = registry.registry_summary()
        self.assertGreater(s["total_programs"], 0)
        self.assertIn("QUALIFIED", s["by_status"])
        self.assertEqual(s["authoritative_source"],
                         "data/commission_opportunities.jsonl")

    def test_statuses_valid(self):
        s = registry.registry_summary()
        for r in s["records"]:
            self.assertIn(r["affiliate_status"], registry.VALID_STATUSES)
            for k in ("program_name", "commission_rate", "cookie_duration",
                      "payout_threshold", "affiliate_link", "lifecycle"):
                self.assertIn(k, r)

    def test_no_approved_without_record(self):
        s = registry.registry_summary()
        for r in s["records"]:
            self.assertNotIn(r["affiliate_status"], ("APPROVED", "ACTIVE"))

    def test_lifecycle_mapping(self):
        self.assertEqual(registry.lifecycle_stage("QUALIFIED"), "QUALIFIED")
        self.assertEqual(registry.lifecycle_stage("CANDIDATE"), "DISCOVERED")


class TestPriority(unittest.TestCase):
    def test_rank_shape(self):
        r = priority.rank_all()
        self.assertGreater(len(r["ranked"]), 0)
        top = r["ranked"][0]
        self.assertIn("score", top)
        self.assertTrue(top["not_a_performance_claim"])
        scores = [s["score"] for s in r["ranked"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_missing_is_zero_never_imputed(self):
        rec = {"opportunity_id": "X", "program_name": "X",
               "affiliate_status": "CANDIDATE", "recurring": "UNKNOWN",
               "commission_rate": "UNKNOWN", "cookie_duration": "UNKNOWN",
               "verification_date": "UNKNOWN", "payout_threshold": "UNKNOWN",
               "prohibited_traffic_sources": "UNKNOWN", "refund_rules": "UNKNOWN",
               "attribution_rules": "UNKNOWN",
               "geographic_restrictions": "UNKNOWN"}
        s = priority.score_program(rec)
        self.assertEqual(s["score"], 0)
        self.assertTrue(all(c["basis"] == "UNKNOWN" for c in s["components"]))

    def test_recurring_scores(self):
        rec = {"opportunity_id": "X", "program_name": "X",
               "affiliate_status": "QUALIFIED", "recurring": True,
               "commission_rate": "30% recurring", "cookie_duration": "60-day cookie",
               "verification_date": "2026-09-20",
               "payout_threshold": "$100", "prohibited_traffic_sources": "none stated",
               "refund_rules": "30-day", "attribution_rules": "last-click",
               "geographic_restrictions": "global"}
        s = priority.score_program(rec)
        self.assertGreaterEqual(s["score"], 80)


class TestPerformance(unittest.TestCase):
    def test_verdicts_valid(self):
        p = performance.classify_all()
        for x in p["programs"]:
            self.assertIn(x["verdict"], ("SCALE_CANDIDATE", "MEASURE_MORE",
                                         "DIAGNOSE", "HOLD", "DROP"))
        self.assertEqual(p["totals"]["verified_commissions"], 0)

    def test_no_auto_scale_without_evidence(self):
        p = performance.classify_all()
        self.assertEqual(sum(1 for x in p["programs"]
                             if x["verdict"] == "SCALE_CANDIDATE"), 0)


class TestHealthReconcile(unittest.TestCase):
    def test_health_shape(self):
        h = dh.daily_health(probe=False)
        self.assertEqual(h["affiliate_revenue_verified_usd"], 0)
        self.assertEqual(h["affiliate_payouts_verified_usd"], 0)
        self.assertIn("top_priority", h)

    def test_reconcile_separation(self):
        r = rc.reconcile()
        self.assertEqual(r["affiliate_revenue_verified_usd"], 0)
        self.assertIn("simulation_note", r)


class TestNotifyDedupe(unittest.TestCase):
    def test_check_idempotent(self):
        import tempfile
        from pathlib import Path
        from affiliate import notify as N
        tmp = Path(tempfile.mkdtemp()) / "state.json"
        N.STATE, orig = tmp, N.STATE
        try:
            first = N.check()
            second = N.check()
            self.assertEqual(second["notifications"], [])
            self.assertTrue(json.loads(tmp.read_text()))
            _ = first
        finally:
            N.STATE = orig


if __name__ == "__main__":
    unittest.main()
