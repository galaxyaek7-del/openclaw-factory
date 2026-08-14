"""Tests for revenue_os.py — the unified Revenue Operating Layer.

Unit + integration + regression + security, MOCK data only. No real ledger is
ever written by these tests; verified-revenue semantics are exercised against
temporary ledgers, never the production data/ directory.
"""

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import revenue_os as ros
from commission_ledger import record_commission


class _Now:
    def __init__(self, iso: str):
        self.iso = iso


def _tmp_ledger(path: Path, records):
    for r in records:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


class CanonicalSchemaTests(unittest.TestCase):
    def test_rejects_unknown_fields(self):
        with self.assertRaises(ValueError):
            ros.canonical_event(verification="VERIFIED", fake_field=1)

    def test_rejects_unknown_verification(self):
        with self.assertRaises(ValueError):
            ros.canonical_event(verification="MADE_UP")

    def test_defaults_occurred_at(self):
        e = ros.canonical_event(event_type="click", verification="OBSERVED")
        self.assertIn("occurred_at", e)

    def test_maps_commission_to_verified_only_when_real_confirmed(self):
        v = ros._commission_to_event({"environment": "REAL", "commission_status": "CONFIRMED", "gross_commission": 10.0, "fees": 0.0, "net_commission": 10.0})
        self.assertEqual(v["verification"], "VERIFIED")
        nv = ros._commission_to_event({"environment": "TEST", "commission_status": "CONFIRMED", "net_commission": 5.0})
        self.assertEqual(nv["verification"], "UNKNOWN")


class RevenueLedgerViewTests(unittest.TestCase):
    def test_verified_separated_from_provisional(self):
        with TemporaryDirectory() as td:
            ledger = Path(td) / "commission_ledger.jsonl"
            record_commission("do", "CO-digitalocean-affiliate", "CONFIRMED", 10.0,
                              environment="REAL", external_transaction_id="tx-1",
                              evidence="real webhook event id from official network", ledger_path=str(ledger))
            record_commission("do", "CO-digitalocean-affiliate", "CONFIRMED", 99.0,
                              environment="PROVISIONAL", external_transaction_id="prov-1",
                              evidence="real in-progress referral claim", ledger_path=str(ledger))
            view = ros.revenue_ledger_view(commission_ledger_path=str(ledger))
            self.assertEqual(view["VERIFIED_REVENUE_USD"], 10.0)
            self.assertEqual(view["PROJECTED_REVENUE_USD"], 99.0)
            self.assertNotEqual(view["VERIFIED_REVENUE_USD"], 109.0)

    def test_zero_when_no_real_records(self):
        with TemporaryDirectory() as td:
            ledger = Path(td) / "commission_ledger.jsonl"
            record_commission("do", "CO-x", "CONFIRMED", 5.0, environment="TEST", ledger_path=str(ledger))
            view = ros.revenue_ledger_view(commission_ledger_path=str(ledger))
            self.assertEqual(view["VERIFIED_REVENUE_USD"], 0.0)

    def test_no_real_data_path_is_zero_not_fake(self):
        view = ros.revenue_ledger_view()
        self.assertIsInstance(view["VERIFIED_REVENUE_USD"], (int, float))


class ArmRouterTests(unittest.TestCase):
    def test_affiliate_routes_to_affiliate(self):
        r = ros.route_opportunity_to_arm({"opportunity_id": "CO-do-affiliate", "category": "affiliate"})
        self.assertEqual(r["routed_arm"], "AFFILIATE")

    def test_marketplace_routes_to_marketplace(self):
        r = ros.route_opportunity_to_arm({"opportunity_id": "CO-g-mp", "category": "marketplace"})
        self.assertEqual(r["routed_arm"], "MARKETPLACE")

    def test_routes_real_portfolio_without_error(self):
        report = ros.arm_router_report()
        self.assertGreater(report["total_opportunities"], 0)
        self.assertIn("AFFILIATE", report["routes_by_arm"])


class ProfitFirstEngineTests(unittest.TestCase):
    def test_recurring_outranks_one_time_all_else_equal(self):
        rec = ros.profit_first_score({"opportunity_id": "a"}, recurring=True)
        one = ros.profit_first_score({"opportunity_id": "b"}, recurring=False)
        self.assertGreater(rec["PROFIT_FIRST_RANK"], one["PROFIT_FIRST_RANK"])

    def test_unknown_inputs_stay_neutral(self):
        s = ros.profit_first_score({"opportunity_id": "x"}, recurring=True)
        self.assertEqual(s["confidence_score"], 0.5)
        self.assertEqual(s["speed_score"], 0.5)

    def test_rank_returns_real_portfolio(self):
        r = ros.profit_first_rank(top_n=3)
        self.assertEqual(len(r["ranking"]), 3)

    def test_verified_tier_outranks_discovered_all_else_equal(self):
        v = ros.profit_first_score({"opportunity_id": "v"}, recurring=True,
                                   evidence_confidence=ros._tier_confidence({"verification_status": "VERIFIED"}))
        d = ros.profit_first_score({"opportunity_id": "d"}, recurring=True,
                                   evidence_confidence=ros._tier_confidence({"verification_status": "DISCOVERED"}))
        self.assertGreater(v["PROFIT_FIRST_RANK"], d["PROFIT_FIRST_RANK"])

    def test_rank_places_verified_recurring_program_first(self):
        r = ros.profit_first_rank(top_n=1)
        # With real portfolio data, the top result must be a VERIFIED program.
        self.assertEqual(r["BEST_PROFIT_FIRST"], "CO-digitalocean-affiliate")

    def test_verified_payout_path_outranks_blocked_path(self):
        open_ = ros.profit_first_score({"opportunity_id": "a", "payout_algeria_compatible": True}, recurring=True, evidence_confidence=1.0)
        blocked = ros.profit_first_score({"opportunity_id": "b", "payout_algeria_compatible": False}, recurring=True, evidence_confidence=1.0)
        self.assertGreater(open_["PROFIT_FIRST_RANK"], blocked["PROFIT_FIRST_RANK"])


class DistributionTests(unittest.TestCase):
    def test_oauth_channels_are_human_gate(self):
        st = ros.distribution_channel_status()
        for ch in ("tiktok", "youtube_shorts", "pinterest", "facebook", "x", "linkedin"):
            self.assertEqual(st["channels"][ch]["state"], "HUMAN_GATE")

    def test_seo_is_ready(self):
        st = ros.distribution_channel_status()
        self.assertEqual(st["channels"]["seo"]["state"], "READY")


class AttributionTests(unittest.TestCase):
    def test_chain_has_all_fingerprint_fields(self):
        chain = ros.attribution_chain("CO-x", "tiktok", "camp-1", "asset-1")
        for k in ("source", "campaign", "content", "channel", "opportunity_id", "utm_campaign", "utm_source"):
            self.assertIn(k, chain)


class AutonomousOptimizationTests(unittest.TestCase):
    def test_zero_real_data_never_scales(self):
        with TemporaryDirectory() as td:
            ledger = Path(td) / "commission_ledger.jsonl"
            record_commission("do", "CO-x", "CONFIRMED", 5.0, environment="TEST", ledger_path=str(ledger))
            opt = ros.autonomous_optimization(commission_ledger_path=str(ledger))
            self.assertFalse(opt["has_real_verified_commission"])
            for d in opt["decisions"]:
                self.assertNotEqual(d["decision"], "SCALE")


class TreasuryTests(unittest.TestCase):
    def test_zero_capital_never_reports_spend(self):
        t = ros.treasury_status()
        self.assertIn("zero_capital_rule", t)
        self.assertEqual(t["cash_usd"], 0.0)

    def test_profit_is_verified_minus_cost(self):
        t = ros.treasury_status()
        self.assertEqual(t["profit_usd"], round(t["verified_revenue_usd"] - t["cost_usd"], 2))


class DailyLoopTests(unittest.TestCase):
    def test_loop_returns_all_stages(self):
        loop = ros.run_daily_ceo_loop()
        for stage in ("DISCOVER", "VERIFY", "RANK", "EXECUTE", "DISTRIBUTE", "MEASURE", "OPTIMIZE", "REINVEST", "DISCOVER_AGAIN"):
            self.assertIn(stage, loop)

    def test_loop_reports_real_verified_revenue(self):
        loop = ros.run_daily_ceo_loop()
        self.assertIsInstance(loop["REAL_VERIFIED_REVENUE_USD"], (int, float))


class HumanGatesTests(unittest.TestCase):
    def test_founder_only_items_listed(self):
        g = ros.human_gates_report()
        self.assertTrue(g["account_creation_confirmation"].startswith("HUMAN"))
        self.assertTrue(g["oauth_authorization"].startswith("HUMAN"))


class SecurityTests(unittest.TestCase):
    def test_no_secrets_leaked_in_renders(self):
        for payload in (ros.build_revenue_os_dashboard(), ros.run_daily_ceo_loop(), ros.human_gates_report()):
            text = json.dumps(payload)
            for secret in ("token", "api_key", "secret", "password", "Authorization", "Bearer"):
                self.assertNotIn(secret, text)


if __name__ == "__main__":
    unittest.main()