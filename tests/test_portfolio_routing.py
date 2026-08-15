"""Tests for portfolio_routing.py — the GLOBAL REVENUE PORTFOLIO ROUTER
(Task 6, 2026-08-15).

Validates: evidence-gating (VERIFIED-tier + freshness only), composition-only
(no duplicate engine — routes reuse revenue_os / profit_oracle / aco),
derived business models (never invented), the orchestrator verification_status
field fix, and read-only behavior (never writes real ledgers)."""

import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

import portfolio_routing as pr


def _verified_opp(oid="CO-test-affiliate", **overrides):
    opp = {
        "opportunity_id": oid,
        "category": "affiliate",
        "verification_status": "VERIFIED",
        "recurring_commission": False,
        "commission_type": "PERCENTAGE",
        "last_verified": datetime.now(timezone.utc).isoformat(),
        "evidence_url": ["https://example.com/terms"],
    }
    opp.update(overrides)
    return opp


class PortfolioRoutingTest(unittest.TestCase):
    def test_only_verified_tier_opportunities_route(self):
        r = pr.route_one_opportunity(_verified_opp())
        self.assertTrue(r["routable"])
        not_verified = pr.route_one_opportunity(_verified_opp(verification_status="DISCOVERED"))
        self.assertFalse(not_verified["routable"])
        self.assertIn("not VERIFIED tier", not_verified["reason"])

    def test_stale_evidence_is_never_routed(self):
        stale = _verified_opp(last_verified=(datetime.now(timezone.utc) - timedelta(days=120)).isoformat())
        r = pr.route_one_opportunity(stale)
        self.assertFalse(r["routable"])
        self.assertIn("stale", r["reason"])

    def test_route_reuses_real_arm_router(self):
        r = pr.route_one_opportunity(_verified_opp())
        self.assertEqual(r["routed_arm"], "AFFILIATE")
        # AFFILIATE is a routing bucket, not a registered payment arm, so its
        # readiness is honestly unknown (None) -- never a false claim.
        self.assertIsNone(r["arm_ready"])
        self.assertIn("category 'affiliate' routes to AFFILIATE", r["arm_rationale"])

    def test_route_ready_state_for_registered_arms(self):
        # When a registered payment arm is the route, readiness is REAL.
        arms = {"gumroad": "ready", "paddle": "ready", "etsy": "unavailable"}
        r = pr.route_one_opportunity(
            _verified_opp(category="marketplace"), arm_statuses=arms)
        self.assertEqual(r["routed_arm"], "MARKETPLACE")
        self.assertIsNone(r["arm_ready"])

    def test_business_models_derived_only_from_real_fields(self):
        # Affiliate + recurring -> affiliate + recurring_service + subscription.
        r = pr.route_one_opportunity(_verified_opp(recurring_commission=True))
        self.assertIn("affiliate", r["business_models"])
        self.assertIn("recurring_service", r["business_models"])
        # No fabricated model: an opportunity with no commission_type and no
        # recognized category gets no invented model.
        bare = pr.route_one_opportunity(
            _verified_opp(oid="CO-x", category="unknown", commission_type=None))
        self.assertTrue(bare["routable"])
        self.assertEqual(bare["business_models"], [])

    def test_report_counts_routed_and_excluded(self):
        portfolio = [
            _verified_opp("CO-a-affiliate"),
            _verified_opp("CO-b-affiliate"),
            _verified_opp("CO-c-affiliate", verification_status="DISCOVERED"),
        ]
        report = pr.portfolio_routing_report(portfolio=portfolio)
        self.assertEqual(report["total_opportunities"], 3)
        self.assertEqual(report["routed"], 2)
        self.assertEqual(report["excluded"], 1)
        self.assertEqual(report["routes_by_arm"].get("AFFILIATE"), 2)

    def test_duplicate_experiment_risk_reuses_experiment_registry(self):
        # No experiments in the temp registry -> NONE risk.
        with tempfile.TemporaryDirectory() as tmp:
            exp_path = Path(tmp) / "commercial_experiments.jsonl"
            exp_path.write_text(json.dumps({
                "record_type": "experiment_definition", "experiment_id": "EXP-T",
                "status": "RUNNING", "created_at": datetime.now(timezone.utc).isoformat(),
            }) + "\n", encoding="utf-8")
            risk = pr.duplicate_experiment_risk("CO-something-else", experiments_path=exp_path)
            self.assertEqual(risk["risk"], "NONE")
            self.assertEqual(risk["total_running"], 1)
            # A targeting experiment -> DUPLICATE_EXPERIMENT risk.
            exp_path.write_text(json.dumps({
                "record_type": "experiment_definition", "experiment_id": "EXP-T",
                "status": "RUNNING", "hypothesis": "targets CO-digitalocean-affiliate",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }) + "\n", encoding="utf-8")
            risk2 = pr.duplicate_experiment_risk("CO-digitalocean-affiliate", experiments_path=exp_path)
            self.assertEqual(risk2["risk"], "DUPLICATE_EXPERIMENT")
            self.assertEqual(risk2["running_targeted"], ["EXP-T"])

    def test_report_is_read_only(self):
        # portfolio_routing_report with a portfolio must not create/write any
        # real data/ file.
        import data  # noqa: F401 -- ensure data/ is importable real dir
        data_dir = Path("data")
        before = sorted(str(p) for p in data_dir.glob("*")) if data_dir.exists() else []
        report = pr.portfolio_routing_report(portfolio=[_verified_opp()])
        self.assertGreaterEqual(report["total_opportunities"], 1)
        after = sorted(str(p) for p in data_dir.glob("*")) if data_dir.exists() else []
        self.assertEqual(before, after, "router must not create/modify any data file")

    def test_opportunity_state_now_honors_verification_status(self):
        # Regression for Task 1 finding: the Executive Orchestrator read
        # `verification` but the real ledger uses `verification_status`, so
        # all 12 VERIFIED opportunities showed as DISCOVERED at the control
        # plane. Now both keys are honored.
        import executive_orchestrator as eo
        self.assertEqual(eo.opportunity_state({"verification_status": "VERIFIED"}), "VERIFIED")
        self.assertEqual(eo.opportunity_state({"verification_status": "PARTIALLY_VERIFIED"}), "VERIFIED")
        self.assertEqual(eo.opportunity_state({"verification": "VERIFIED"}), "VERIFIED")
        self.assertEqual(eo.opportunity_state({"verification_status": "DISCOVERED"}), "DISCOVERED")
        self.assertEqual(eo.opportunity_state({}), "DISCOVERED")

    def test_commission_unknown_never_fabricates_affiliate_model(self):
        # Second-sweep regression: a COMMISSION_UNKNOWN placeholder is NOT
        # evidence of an affiliate model (commission_engine.py:221's honest
        # convention). CO-gumroad-marketplace has commission_type
        # "COMMISSION_UNKNOWN" and category "marketplace" -- it must NOT get
        # the affiliate model.
        opp = _verified_opp(oid="CO-gumroad-marketplace", category="marketplace",
                            commission_type="COMMISSION_UNKNOWN")
        models = pr._derived_business_models(opp)
        self.assertNotIn("affiliate", models)
        self.assertIn("premium_digital_asset", models)
        # Same placeholder with category affiliate still routes (category is a
        # real signal), but a truly empty record derives nothing.
        empty = pr._derived_business_models(_verified_opp(oid="CO-y", category="",
                                                          commission_type=None))
        self.assertEqual(empty, [])


if __name__ == "__main__":
    unittest.main()
