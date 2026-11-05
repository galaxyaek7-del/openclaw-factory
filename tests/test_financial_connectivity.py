"""Financial connectivity tests (2026-10-24).

They lock the honesty rules of the provider/settlement layer:

  * a key is CONFIGURED_NOT_VERIFIED, never PAYMENT_CAPABLE;
  * a published listing is not revenue;
  * TEST/SANDBOX/SIMULATION rows never become orders;
  * an unknown fee or amount stays null, never zero;
  * credential values are never returned, only presence booleans;
  * BADR is settlement-only until a real settlement is recorded;
  * Stripe stays blocked for Algeria regardless of credentials.

No network, no provider, no real state: every fixture is injected.
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import financial_connectivity as fc  # noqa: E402


def _write_json(root, rel, payload):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(root, rel, rows):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


class FinancialConnectivityFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fc_test_"))

    def _base(self, connectivity=None, products=None, sales=None, commissions=None):
        _write_json(self.tmp, "data/payment_connectivity.json", {
            "at": "2026-10-02T15:14:22+00:00",
            "connections": connectivity or {},
        })
        _write_json(self.tmp, "data/product_registry.json", {
            "products": products or [],
        })
        _write_json(self.tmp, "data/paddle_products.json", [])
        _write_jsonl(self.tmp, "data/sales_ledger.jsonl", sales or [])
        _write_jsonl(self.tmp, "data/commission_ledger.jsonl", commissions or [])

    def _snapshot(self, env=None):
        return fc.build_financial_connectivity_snapshot(root=self.tmp, env=env or {})


class ProviderStatusTests(FinancialConnectivityFixture):
    def test_gumroad_configured_key_is_not_payment_capable(self):
        self._base(
            connectivity={"gumroad": {"api": "CONNECTED", "checkout": "LIVE"}},
            products=[{"internal_id": "P1", "published": True, "external_ids": {"gumroad": "g1"}}],
        )
        snap = self._snapshot(env={"GUMROAD_ACCESS_TOKEN": "secret-token-value"})
        provider = snap["providers"]["gumroad"]
        self.assertEqual(provider["status"], "CONFIGURED_NOT_VERIFIED")
        self.assertTrue(provider["credential_presence"]["GUMROAD_ACCESS_TOKEN"])
        channel = next(c for c in snap["channels"] if c["channel"] == "gumroad")
        self.assertEqual(channel["state"], "PUBLIC_LISTING_ONLY")

    def test_credential_values_are_never_returned(self):
        self._base()
        snap = self._snapshot(env={
            "GUMROAD_ACCESS_TOKEN": "super-secret-gumroad",
            "PADDLE_API_KEY": "super-secret-paddle",
            "STRIPE_SECRET_KEY": "super-secret-stripe",
        })
        serialized = json.dumps(snap, ensure_ascii=False)
        for secret in ("super-secret-gumroad", "super-secret-paddle", "super-secret-stripe"):
            self.assertNotIn(secret, serialized)

    def test_paddle_blocked_checkout_is_connected_read_only(self):
        self._base(connectivity={"paddle": {
            "api": "CONNECTED", "checkout": "BLOCKED", "webhook": "NOT_CONFIGURED",
        }})
        snap = self._snapshot(env={"PADDLE_API_KEY": "k"})
        self.assertEqual(snap["providers"]["paddle"]["status"], "CONNECTED_READ_ONLY")
        channel = next(c for c in snap["channels"] if c["channel"] == "paddle")
        self.assertEqual(channel["state"], "BLOCKED")

    def test_stripe_is_blocked_for_algeria_with_or_without_keys(self):
        self._base()
        without = self._snapshot(env={})["providers"]["stripe"]
        with_key = self._snapshot(env={"STRIPE_SECRET_KEY": "k"})["providers"]["stripe"]
        self.assertEqual(without["status"], "BLOCKED_BY_PROVIDER_ELIGIBILITY")
        self.assertEqual(with_key["status"], "BLOCKED_BY_PROVIDER_ELIGIBILITY")

    def test_paypal_without_keys_is_not_configured_and_eligibility_is_conditional(self):
        self._base()
        provider = self._snapshot(env={})["providers"]["paypal"]
        self.assertEqual(provider["status"], "NOT_CONFIGURED")
        self.assertIn("CONDITIONAL", provider["eligibility"])

    def test_badr_is_unknown_and_settlement_only_without_records(self):
        self._base()
        provider = self._snapshot(env={})["providers"]["badr"]
        self.assertEqual(provider["status"], "UNKNOWN")
        self.assertEqual(provider["settlement_model"], "Bank settlement / manual reconciliation only")
        self.assertFalse(provider["api_available"])
        self.assertFalse(provider["credentials_required"])

    def test_badr_becomes_settlement_verified_only_with_a_verified_record(self):
        self._base()
        _write_jsonl(self.tmp, "data/bank_settlements.jsonl", [{
            "settlement_id": "S1", "status": "SETTLEMENT_VERIFIED",
            "amount_cents": 10000, "net_cents": 9500,
            "currency": "USD", "settlement_date": "2026-10-20",
        }])
        snap = self._snapshot(env={})
        self.assertEqual(snap["providers"]["badr"]["status"], "SETTLEMENT_VERIFIED")
        self.assertIn("badr", snap["unified_financial_state"]["available_payment_rails"])

    def test_auth_failure_evidence_wins_over_a_configured_key(self):
        self._base(connectivity={"gumroad": {"api": "401 AUTH FAILED"}})
        provider = self._snapshot(env={"GUMROAD_ACCESS_TOKEN": "k"})["providers"]["gumroad"]
        self.assertEqual(provider["status"], "AUTHENTICATION_FAILED")

    def test_a_real_order_moves_the_provider_to_payment_capable(self):
        self._base(sales=[
            {"event_type": "sale", "platform": "gumroad", "raw": {"id": "s1", "price": 10}},
        ])
        snap = self._snapshot(env={"GUMROAD_ACCESS_TOKEN": "k"})
        self.assertEqual(snap["providers"]["gumroad"]["status"], "PAYMENT_CAPABLE")
        channel = next(c for c in snap["channels"] if c["channel"] == "gumroad")
        self.assertEqual(channel["state"], "SALES_OBSERVED")

    def test_stale_connectivity_evidence_is_labeled_not_upgraded(self):
        self._base(connectivity={"gumroad": {"api": "CONNECTED", "checkout": "LIVE"}})
        snap = fc.build_financial_connectivity_snapshot(
            root=self.tmp, env={"GUMROAD_ACCESS_TOKEN": "k"},
            now=datetime(2026, 10, 24, tzinfo=timezone.utc),
        )
        self.assertEqual(snap["evidence_freshness"]["state"], "STALE")
        self.assertGreater(snap["evidence_freshness"]["age_days"], 7)
        self.assertEqual(snap["providers"]["gumroad"]["status"], "CONFIGURED_NOT_VERIFIED")

    def test_status_vocabulary_is_exact(self):
        self._base()
        snap = self._snapshot(env={})
        self.assertEqual(snap["status_vocabulary"], [
            "NOT_CONFIGURED", "CONFIGURED_NOT_VERIFIED", "AUTHENTICATION_FAILED",
            "CONNECTED_READ_ONLY", "PAYMENT_CAPABLE", "SETTLEMENT_VERIFIED",
            "BLOCKED_BY_PROVIDER_ELIGIBILITY", "UNKNOWN",
        ])


class OrderAndRevenueTests(FinancialConnectivityFixture):
    def test_zero_orders_is_zero_gross_zero_net_not_unknown(self):
        self._base()
        sales = self._snapshot(env={})["sales"]
        self.assertEqual(sales["orders_count"], 0)
        self.assertEqual(sales["gross_revenue_cents"], 0)
        self.assertEqual(sales["fees_cents"], 0)
        self.assertEqual(sales["net_revenue_cents"], 0)
        self.assertEqual(sales["verified_revenue_cents"], 0)

    def test_test_and_sandbox_events_are_excluded(self):
        self._base(sales=[
            {"event_type": "sale", "platform": "gumroad", "raw": {"id": "t1", "price": 9.99}, "environment": "TEST"},
            {"event_type": "sale", "platform": "gumroad", "raw": {"id": "s1", "price": 9.99}, "environment": "SANDBOX"},
            {"event_type": "sale", "platform": "gumroad", "raw": {"id": "r1", "price": 9.99}},
        ])
        sales = self._snapshot(env={})["sales"]
        self.assertEqual(sales["orders_count"], 1)
        self.assertEqual(sales["excluded_test_rows"], 2)
        self.assertEqual(sales["gross_revenue_cents"], 999)

    def test_duplicate_external_ids_are_counted_once(self):
        self._base(sales=[
            {"event_type": "sale", "platform": "gumroad", "raw": {"id": "same", "price": 10}},
            {"event_type": "sale", "platform": "gumroad", "raw": {"id": "same", "price": 10}},
        ])
        sales = self._snapshot(env={})["sales"]
        self.assertEqual(sales["orders_count"], 1)
        self.assertEqual(sales["duplicate_rows_skipped"], 1)
        self.assertEqual(sales["gross_revenue_cents"], 1000)

    def test_unpriced_sale_leaves_gross_net_and_verified_null(self):
        self._base(sales=[
            {"event_type": "sale", "platform": "gumroad", "raw": {"id": "no-price"}},
        ])
        sales = self._snapshot(env={})["sales"]
        self.assertEqual(sales["orders_count"], 1)
        self.assertEqual(sales["unpriced_orders"], 1)
        self.assertIsNone(sales["gross_revenue_cents"])
        self.assertIsNone(sales["net_revenue_cents"])
        self.assertIsNone(sales["verified_revenue_cents"])
        self.assertFalse(sales["gross_complete"])
        self.assertIsNone(sales["by_platform"]["gumroad"]["gross_cents"])

    def test_unknown_fee_keeps_net_null_even_when_gross_is_known(self):
        self._base(sales=[
            {"event_type": "sale", "platform": "gumroad", "raw": {"id": "s1", "price": 20}},
        ])
        sales = self._snapshot(env={})["sales"]
        self.assertEqual(sales["gross_revenue_cents"], 2000)
        self.assertIsNone(sales["fees_cents"])
        self.assertIsNone(sales["net_revenue_cents"])
        self.assertEqual(sales["verified_revenue_cents"], 2000)

    def test_recorded_fee_produces_net(self):
        self._base(sales=[
            {"event_type": "sale", "platform": "gumroad",
             "raw": {"id": "s1", "price": 20, "fees": {"total": 2.5}}},
        ])
        sales = self._snapshot(env={})["sales"]
        self.assertEqual(sales["fees_cents"], 250)
        self.assertEqual(sales["net_revenue_cents"], 1750)

    def test_paddle_sale_uses_grand_total_cents(self):
        self._base(sales=[
            {"event_type": "sale", "platform": "paddle", "raw": {
                "id": "txn_1", "details": {"totals": {"grand_total": "1999"}},
            }},
        ])
        sales = self._snapshot(env={})["sales"]
        self.assertEqual(sales["gross_revenue_cents"], 1999)

    def test_only_real_confirmed_commissions_count(self):
        self._base(commissions=[
            {"commission_id": "c1", "environment": "TEST", "commission_status": "CONFIRMED", "net_commission": 500},
            {"commission_id": "c2", "environment": "REAL", "commission_status": "PENDING", "net_commission": 20},
            {"commission_id": "c3", "environment": "REAL", "commission_status": "PAID", "net_commission": 12.5},
        ])
        sales = self._snapshot(env={})["sales"]
        self.assertEqual(sales["commission_revenue_cents"], 1250)
        self.assertEqual(sales["verified_revenue_cents"], 1250)

    def test_real_order_marks_revenue_verified_but_not_settled(self):
        self._base(sales=[
            {"event_type": "sale", "platform": "gumroad", "raw": {"id": "s1", "price": 10}},
        ])
        state = self._snapshot(env={})["unified_financial_state"]
        self.assertTrue(state["revenue_verified"])
        self.assertIsNone(state["settled_cents"])
        self.assertEqual(state["available_payment_rails"], ["gumroad"])


class ChannelStateTests(FinancialConnectivityFixture):
    def test_channel_states_are_not_upgraded_without_evidence(self):
        self._base()
        states = {c["channel"]: c["state"] for c in self._snapshot(env={})["channels"]}
        self.assertEqual(states["gumroad"], "NOT_CONFIGURED")
        self.assertEqual(states["etsy"], "BLOCKED")
        self.assertEqual(states["shopify"], "NOT_CONFIGURED")
        self.assertEqual(states["payhip"], "NOT_IMPLEMENTED")
        self.assertEqual(states["amazon_kdp"], "MANUAL_UPLOAD_ONLY")
        self.assertEqual(states["direct_website"], "PARTIAL")

    def test_published_listing_without_orders_is_public_listing_only(self):
        self._base(products=[
            {"internal_id": "P1", "published": True, "external_ids": {"gumroad": "g1"}},
            {"internal_id": "P2", "published": False, "external_ids": {"gumroad": "g2"}},
        ])
        channel = next(c for c in self._snapshot(env={})["channels"] if c["channel"] == "gumroad")
        self.assertEqual(channel["published_count"], 1)
        self.assertEqual(channel["product_count"], 2)
        self.assertEqual(channel["state"], "PUBLIC_LISTING_ONLY")

    def test_snapshot_is_read_only(self):
        self._base()
        snap = self._snapshot(env={})
        self.assertEqual(snap["mode"], "READ_ONLY")
        self.assertEqual(snap["network_calls"], 0)
        self.assertEqual(snap["writes"], 0)
        self.assertFalse((self.tmp / "data" / "bank_settlements.jsonl").exists())


class RoutingPolicyTests(FinancialConnectivityFixture):
    def _routing(self, **overrides):
        payload = {
            "version": 4,
            "updated": "2026-09-08",
            "hard_stop_active": True,
            "treasury": {"provider": "BADR", "currency": "EUR", "role": "FINAL_TREASURY", "status": "FOUNDER_CONFIRMED"},
            "hub": {"provider": "Payoneer", "role": "PRIMARY_HUB", "verification": "PENDING", "identity": "aekgalaxy47@gmail.com"},
            "fallbacks": {
                "paypal": {"role": "FALLBACK_EXCEPTION_ONLY", "algeria_receiving": "PROBLEMATIC"},
                "wise": {"role": "FALLBACK_EXCEPTION_ONLY", "status": "NOT_CONFIGURED"},
                "redotpay": {"role": "FALLBACK_EXCEPTION_ONLY", "status": "COMPLETELY_ABSENT"},
            },
            "financial_truth": {"real_revenue_usd": 0.0},
            "account_routing": {
                "total_classified_platforms": 28,
                "verified_count": 6,
                "unknown_count": 22,
            },
            "platform_classification": {
                "paddle": {"classification": "PAYONEER_HUB", "status": "SUPPORTED_NOT_CONFIGURED", "routing": "Paddle -> Payoneer -> BADR EUR"},
                "gumroad": {"classification": "BANK_ROUTE", "status": "BANK_ROUTE_CONFIRMED", "routing": "Gumroad -> BADR"},
            },
        }
        payload.update(overrides)
        _write_json(self.tmp, "config/financial_connectivity.json", payload)

    def test_canonical_policy_is_cited_without_leaking_identity(self):
        self._routing()
        self._base()
        snap = self._snapshot(env={})
        self.assertEqual(snap["routing"]["source"], "config/financial_connectivity.json")
        self.assertEqual(snap["routing"]["version"], 4)
        self.assertEqual(snap["routing"]["hub"]["verification"], "PENDING")
        self.assertNotIn("aekgalaxy47@gmail.com", json.dumps(snap))
        self.assertNotIn("galaxyaek7@gmail.com", json.dumps(snap))

    def test_disagreement_is_reported_not_resolved(self):
        self._routing()
        self._base()
        consistency = self._snapshot(env={})["routing_consistency"]
        self.assertEqual(consistency["state"], "UNRECONCILED")
        paddle = next(p for p in consistency["pairs"] if p["platform"] == "paddle")
        self.assertEqual(paddle["policy_method"], "Payoneer")
        self.assertEqual(paddle["account_routing_method"], "UNKNOWN")
        self.assertEqual(paddle["state"], "UNRECONCILED")

    def test_stale_config_revenue_is_flagged_not_trusted(self):
        self._routing()
        self._base(commissions=[
            {"commission_id": "c1", "environment": "REAL", "commission_status": "PAID", "net_commission": 500},
        ])
        truth = self._snapshot(env={})["financial_truth_consistency"]
        self.assertEqual(truth["config_declared_real_revenue_usd"], 0.0)
        self.assertEqual(truth["ledger_verified_revenue_usd"], 500.0)
        self.assertFalse(truth["consistent"])

    def test_settlement_routes_are_honest(self):
        self._routing()
        self._base()
        routes = {r["route"]: r for r in self._snapshot(env={})["settlement_routes"]}
        self.assertEqual(routes["badr"]["status"], "UNKNOWN")
        self.assertEqual(routes["payoneer"]["status"], "UNKNOWN")
        self.assertEqual(routes["wise"]["status"], "NOT_CONFIGURED")
        self.assertEqual(routes["redotpay"]["status"], "NOT_CONFIGURED")

    def test_account_routing_count_drift_is_reported(self):
        self._routing()
        self._base()
        counts = self._snapshot(env={})["routing_consistency"]["account_routing_counts"]
        self.assertEqual(counts["config_declared"]["total_classified_platforms"], 28)
        self.assertGreaterEqual(counts["live"]["total_classified_platforms"], 28)
        self.assertFalse(counts["consistent"])


class BankSettlementWriterTests(FinancialConnectivityFixture):
    def test_record_is_idempotent(self):
        path = self.tmp / "data" / "bank_settlements.jsonl"
        payload = {
            "settlement_id": "S1", "amount_cents": 10000, "fees_cents": 500,
            "currency": "usd", "settlement_date": "2026-10-20",
            "status": "SETTLEMENT_VERIFIED", "bank": "BADR",
        }
        first = fc.record_bank_settlement(payload, path=path)
        second = fc.record_bank_settlement(payload, path=path)
        self.assertTrue(first["recorded"])
        self.assertEqual(first["settlement"]["net_cents"], 9500)
        self.assertEqual(first["settlement"]["currency"], "USD")
        self.assertFalse(second["recorded"])
        self.assertEqual(second["reason"], "DUPLICATE")
        self.assertEqual(len(path.read_text(encoding="utf-8").strip().splitlines()), 1)

    def test_invalid_settlement_is_rejected(self):
        path = self.tmp / "data" / "bank_settlements.jsonl"
        with self.assertRaises(ValueError):
            fc.record_bank_settlement({"settlement_id": "S1"}, path=path)
        with self.assertRaises(ValueError):
            fc.record_bank_settlement({
                "settlement_id": "S2", "amount_cents": -1,
                "currency": "USD", "settlement_date": "2026-10-20",
            }, path=path)
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
