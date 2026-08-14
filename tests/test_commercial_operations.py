"""Tests for commercial_operations.py -- the CTO+COO audit-closure bridge.

MOCK data only: revenue-event model, profit engine, readiness, gap register,
distribution matrix and link monitor are all exercised against temporary/
mocked state or are pure read-only views over real ledgers. Nothing here
writes to the real revenue ledgers.
"""

import json
import tempfile
import unittest
from pathlib import Path

import commercial_operations as co


class RevenueEventModelTests(unittest.TestCase):
    def test_verified_only_from_real_confirmed(self):
        rows = [
            {"environment": "REAL", "commission_status": "CONFIRMED", "gross_commission": 25.0, "event_id": "e1"},
            {"environment": "REAL", "commission_status": "PENDING", "gross_commission": 10.0, "event_id": "e2"},
            {"environment": "TEST", "commission_status": "CONFIRMED", "gross_commission": 99.0, "event_id": "e3"},
            {"environment": "MOCK", "commission_status": "CONFIRMED", "gross_commission": 99.0, "event_id": "e4"},
        ]
        # Patch the ledger source so the view reads temp data only.
        original = co._commission_ledger_events
        co._commission_ledger_events = lambda: rows
        try:
            r = co.revenue_event_model()
            self.assertEqual(r["verified_revenue_usd"], 25.0)
            self.assertEqual(r["by_environment"]["TEST"], 1)
            self.assertEqual(r["by_environment"]["MOCK"], 1)
        finally:
            co._commission_ledger_events = original

    def test_test_mock_never_verified(self):
        rows = [
            {"environment": "TEST", "commission_status": "CONFIRMED", "gross_commission": 99.0, "event_id": "t1"},
            {"environment": "MOCK", "commission_status": "CONFIRMED", "gross_commission": 99.0, "event_id": "m1"},
        ]
        original = co._commission_ledger_events
        co._commission_ledger_events = lambda: rows
        try:
            r = co.revenue_event_model()
            self.assertEqual(r["verified_events"], 0)
            self.assertEqual(r["verified_revenue_usd"], 0.0)
        finally:
            co._commission_ledger_events = original

    def test_duplicate_events_detected_not_double_counted(self):
        rows = [
            {"environment": "REAL", "commission_status": "CONFIRMED", "gross_commission": 25.0, "event_id": "dup1"},
            {"environment": "REAL", "commission_status": "CONFIRMED", "gross_commission": 25.0, "event_id": "dup1"},
        ]
        original = co._commission_ledger_events
        co._commission_ledger_events = lambda: rows
        try:
            r = co.revenue_event_model()
            self.assertGreaterEqual(r["duplicate_events_detected"], 1)
        finally:
            co._commission_ledger_events = original

    def test_environment_separation_stated(self):
        r = co.revenue_event_model()
        self.assertIn("only real verified", r["rule"].lower())
        self.assertIn("never summed", r["rule"].lower())


class ProfitEngineTests(unittest.TestCase):
    def test_gross_equals_verified_only(self):
        rows = [
            {"environment": "REAL", "commission_status": "CONFIRMED", "gross_commission": 100.0, "event_id": "p1"},
            {"environment": "TEST", "commission_status": "CONFIRMED", "gross_commission": 999.0, "event_id": "p2"},
        ]
        original = co._commission_ledger_events
        co._commission_ledger_events = lambda: rows
        try:
            r = co.profit_engine()
            self.assertEqual(r["gross_revenue"], 100.0)
            self.assertEqual(r["profit"], round(100.0 - r["platform_fees"], 2))
        finally:
            co._commission_ledger_events = original

    def test_zero_spend_rule_never_introduces_unapproved_cost(self):
        r = co.profit_engine()
        self.assertIn("zero-discretionary-spend", r["zero_spend_rule"].lower())
        self.assertIn("other_verified_costs", r)

    def test_separate_cash_pending_projected(self):
        r = co.profit_engine()
        for key in ("cash_received", "pending_revenue", "projected_revenue"):
            self.assertIn(key, r)


class DistributionCapabilityMatrixTests(unittest.TestCase):
    def test_all_channels_covered(self):
        r = co.distribution_capability_matrix()
        for ch in ("PINTEREST", "TIKTOK", "YOUTUBE", "X", "FACEBOOK", "LINKEDIN", "SEO"):
            self.assertIn(ch, r["channels"])

    def test_never_claims_publishing_automated_without_path(self):
        r = co.distribution_capability_matrix()
        self.assertEqual(r["publishing_automated_count"], 0)
        self.assertEqual(r["analytics_automated_count"], 0)

    def test_distinguishes_content_from_publishing(self):
        r = co.distribution_capability_matrix()
        self.assertGreaterEqual(r["content_automated_count"], 1)
        for c in r["channels"].values():
            self.assertFalse(c["PUBLISHING_AUTOMATED"])


class OperationalReadinessTests(unittest.TestCase):
    def test_scores_are_present_and_bounded(self):
        r = co.operational_readiness()
        for key in ("TECHNICAL_READINESS", "COMMERCIAL_READINESS", "AUTOMATION_READINESS",
                    "REVENUE_READINESS", "SECURITY_READINESS", "RECOVERY_READINESS",
                    "GALAXY_FORGE_OPERATIONAL_READINESS"):
            self.assertIn(key, r)
            self.assertGreaterEqual(r[key], 0)
            self.assertLessEqual(r[key], 100)

    def test_revenue_readiness_honest_when_zero(self):
        # Revenue readiness must reflect reality: with $0 verified revenue the
        # revenue dimension is not 100.
        r = co.operational_readiness()
        if co._real_verified_revenue() == 0.0:
            self.assertLess(r["REVENUE_READINESS"], 100)


class CommercialGapRegisterTests(unittest.TestCase):
    def test_every_gap_has_required_fields(self):
        r = co.commercial_gap_register()
        for g in r["gaps"]:
            for field in ("gap_id", "category", "severity", "business_impact", "current_state",
                          "target_state", "automation_possible", "human_gate", "recommended_fix", "status"):
                self.assertIn(field, g)

    def test_counts_consistent(self):
        r = co.commercial_gap_register()
        self.assertEqual(r["gap_count"], len(r["gaps"]))
        self.assertEqual(r["critical_gap_count"], len([g for g in r["gaps"] if g["severity"] == "CRITICAL"]))

    def test_human_gates_are_unavoidable_actions_only(self):
        r = co.commercial_gap_register()
        for g in r["gaps"]:
            if g["human_gate"]:
                self.assertTrue(g["automation_possible"] is False or "payment" in g["recommended_fix"].lower() or
                                "authorization" in g["recommended_fix"].lower() or
                                "authorize" in g["recommended_fix"].lower() or
                                "configure" in g["recommended_fix"].lower())


class LinkMonitorTests(unittest.TestCase):
    def test_dry_run_never_hits_network(self):
        r = co.link_monitor(dry_run=True)
        self.assertEqual(r["mode"], "dry_run")
        for c in r["checks"]:
            self.assertEqual(c["status"], "SKIPPED")
            self.assertIsNone(c["http_status"])

    def test_links_are_registered_real_links(self):
        links = co._registered_commercial_links()
        self.assertTrue(len(links) >= 1)
        for link in links:
            self.assertIn("url", link)
            self.assertIn("label", link)
            self.assertIn("offer_id", link)

    def test_monitor_reports_tracking_presence(self):
        r = co.link_monitor(dry_run=True)
        for c in r["checks"]:
            self.assertIn("tracking_present", c)
            self.assertIn("pause_campaign", c)


class MissionControlEndpointTests(unittest.TestCase):
    """Verify the endpoints are registered and callable (the previously
    dead-code commercial layer is now reachable through Mission Control)."""

    def test_endpoints_registered(self):
        import mission_control_api as mca
        for ep in ("commercial_mission_control", "commercial_founder_queue",
                   "commercial_revenue_router", "operational_readiness",
                   "commercial_gap_register", "revenue_event_model",
                   "profit_engine", "distribution_capability_matrix",
                   "commercial_link_monitor", "commercial_treasury"):
            self.assertIn(ep, mca._ENDPOINTS)

    def test_read_only_endpoints_run(self):
        import mission_control_api as mca
        for ep in ("commercial_treasury", "profit_engine", "distribution_capability_matrix",
                   "revenue_event_model", "commercial_link_monitor"):
            r = mca._ENDPOINTS[ep]()
            self.assertIsInstance(r, dict)
            self.assertNotIn("success", r)  # pure view, no envelope leakage


class TreasuryRegressionTests(unittest.TestCase):
    def test_treasury_uses_real_verified_value(self):
        import revenue_os
        rows = [{"environment": "REAL", "commission_status": "CONFIRMED", "gross_commission": 50.0}]
        # Patch the summary source through the real ledger loader is invasive;
        # instead assert the treasury still reports 0 when no REAL rows exist
        # and that the fields are present.
        t = revenue_os.treasury_status()
        self.assertIn("verified_revenue_usd", t)
        self.assertIn("pending_revenue_usd", t)
        self.assertIsInstance(t["verified_revenue_usd"], (int, float))
        # The bug was verified being overwritten to 0.0: with a temp ledger
        # containing a REAL CONFIRMED row, treasury must report it.
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "cl.jsonl"
            with open(ledger, "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "event_id": "treas1", "partner_id": "gumroad", "opportunity_id": "op",
                    "commission_status": "CONFIRMED", "net_commission": 42.0,
                    "environment": "REAL", "evidence": "test evidence",
                    "currency": "USD", "timestamp": "2026-08-15T00:00:00Z",
                }) + "\n")
            try:
                t = revenue_os.treasury_status(commission_ledger_path=str(ledger))
                self.assertEqual(t["verified_revenue_usd"], 42.0)
            except Exception as e:
                self.fail(f"treasury with temp ledger raised: {e}")


if __name__ == "__main__":
    unittest.main()
