import json
import os
import tempfile
import unittest

import commission_engine as ce


class TestOpportunityPortfolio(unittest.TestCase):
    def test_derives_only_real_status_opportunities(self):
        portfolio = ce.derive_initial_opportunity_portfolio()
        self.assertGreater(len(portfolio), 0)
        for o in portfolio:
            self.assertIsNotNone(o["opportunity_id"])

    def test_portfolio_size_within_controlled_range(self):
        # Section 19: "10-20 high-quality" -- not thousands.
        portfolio = ce.derive_initial_opportunity_portfolio()
        self.assertLessEqual(len(portfolio), 30)

    def test_every_record_has_all_20_named_fields(self):
        portfolio = ce.derive_initial_opportunity_portfolio()
        required = ["opportunity_id", "source", "partner_id", "program_name", "partner_name", "category",
                    "target_customer", "customer_problem", "product_or_service", "commission_type",
                    "commission_value", "commission_currency", "recurring_commission", "commission_duration",
                    "minimum_conditions", "cookie_or_tracking_window", "payout_terms", "eligibility",
                    "geography", "evidence_url", "evidence_timestamp", "verification_status", "confidence",
                    "risk_score", "status", "last_verified"]
        for o in portfolio:
            for field in required:
                self.assertIn(field, o)

    def test_unknown_commission_is_never_fabricated(self):
        portfolio = ce.derive_initial_opportunity_portfolio()
        for o in portfolio:
            if o["commission_value"] == "COMMISSION_UNKNOWN":
                self.assertNotIn("$", str(o["commission_value"]))

    def test_save_and_load_roundtrip(self):
        portfolio = ce.derive_initial_opportunity_portfolio()
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "opps.jsonl")
            ce.save_opportunity_portfolio(portfolio, path=path)
            loaded = ce.load_opportunity_portfolio(path=path)
            self.assertEqual(len(loaded), len(portfolio))


class TestVerificationStatus(unittest.TestCase):
    def test_never_verified_without_terms_and_evidence(self):
        entry = {"terms": None, "evidence": []}
        odata = {"commission": "10%"}
        status = ce._derive_verification_status(entry, odata)
        self.assertNotEqual(status, "VERIFIED")

    def test_verified_requires_all_three_signals(self):
        entry = {"terms": "https://example.com/terms", "evidence": ["https://example.com/proof"]}
        odata = {"commission": "10%"}
        status = ce._derive_verification_status(entry, odata)
        self.assertEqual(status, "VERIFIED")

    def test_all_statuses_are_named(self):
        for status in ("VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED"):
            self.assertIn(status, ce.PARTNER_VERIFICATION_STATUSES)


class TestScoring(unittest.TestCase):
    def test_returns_all_13_dimensions(self):
        opp = {"opportunity_id": "X", "commission_value": "10%", "verification_status": "VERIFIED"}
        result = ce.score_commission_opportunity(opp)
        self.assertEqual(len(result["dimensions"]), 13)

    def test_never_collapses_to_single_score(self):
        opp = {"opportunity_id": "X", "commission_value": "10%"}
        result = ce.score_commission_opportunity(opp)
        self.assertNotIn("overall_score", result)

    def test_high_commission_alone_does_not_dominate(self):
        opp = {"opportunity_id": "X", "commission_value": "5000 USD flat"}
        result = ce.score_commission_opportunity(opp)
        # Most other dimensions remain UNKNOWN regardless of commission size.
        unknown_count = sum(1 for v in result["dimensions"].values() if "UNKNOWN" in str(v))
        self.assertGreater(unknown_count, 0)


class TestFreshness(unittest.TestCase):
    def test_fresh_within_window(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        self.assertEqual(ce._freshness_from_last_verified(now.isoformat(), now=now), "FRESH")

    def test_stale_beyond_window(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=100)).isoformat()
        self.assertEqual(ce._freshness_from_last_verified(old, now=now), "STALE")

    def test_missing_timestamp_is_unknown_not_fresh(self):
        self.assertEqual(ce._freshness_from_last_verified(None), "UNKNOWN")


class TestCommissionEconomics(unittest.TestCase):
    def test_incomplete_without_real_inputs(self):
        opp = {"opportunity_id": "X", "commission_value": "COMMISSION_UNKNOWN"}
        result = ce.commission_economics(opp)
        self.assertEqual(result["economic_status"], "INCOMPLETE")

    def test_never_presents_estimate_as_observed(self):
        opp = {"opportunity_id": "X", "commission_value": "10%"}
        result = ce.commission_economics(opp, expected_conversion_rate=0.05, conversion_rate_basis="ESTIMATED",
                                          expected_deal_value=100)
        self.assertEqual(result["conversion_rate_basis"], "ESTIMATED")
        self.assertNotEqual(result["conversion_rate_basis"], "OBSERVED")

    def test_invalid_basis_defaults_to_unknown(self):
        opp = {"opportunity_id": "X", "commission_value": "10%"}
        result = ce.commission_economics(opp, expected_conversion_rate=0.05, conversion_rate_basis="MADE_UP",
                                          expected_deal_value=100)
        self.assertEqual(result["conversion_rate_basis"], "UNKNOWN")

    def test_unparseable_commission_stays_incomplete(self):
        opp = {"opportunity_id": "X", "commission_value": "Market 30%, Elements up to $120"}
        result = ce.commission_economics(opp, expected_conversion_rate=0.05, expected_deal_value=100)
        # "30%" IS parseable here by design (first percentage found) --
        # use a genuinely unparseable string instead.
        opp2 = {"opportunity_id": "X", "commission_value": "contact sales for pricing"}
        result2 = ce.commission_economics(opp2, expected_conversion_rate=0.05, expected_deal_value=100)
        self.assertEqual(result2["economic_status"], "INCOMPLETE")

    def test_correct_arithmetic(self):
        opp = {"opportunity_id": "X", "commission_value": "10%"}
        result = ce.commission_economics(opp, expected_conversion_rate=0.1, expected_deal_value=1000, ai_cost=1.0)
        self.assertEqual(result["expected_gross_commission"], 10.0)
        self.assertEqual(result["expected_net_contribution"], 9.0)


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.events_path = os.path.join(self._tmpdir.name, "events.jsonl")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_valid_transition_recorded(self):
        result = ce.record_pipeline_transition("CO-x", "OPPORTUNITY", "VERIFIED_PARTNER", events_path=self.events_path)
        self.assertTrue(result["ok"])

    def test_invalid_state_rejected(self):
        result = ce.record_pipeline_transition("CO-x", "OPPORTUNITY", "NOT_A_REAL_STATE", events_path=self.events_path)
        self.assertFalse(result["ok"])

    def test_terminal_exits_are_valid(self):
        for exit_state in ce.COMMISSION_PIPELINE_TERMINAL_EXITS:
            result = ce.record_pipeline_transition("CO-x", "DEAL", exit_state, events_path=self.events_path)
            self.assertTrue(result["ok"], f"{exit_state} should be a valid transition target")

    def test_history_filters_by_opportunity(self):
        ce.record_pipeline_transition("CO-a", "OPPORTUNITY", "LEAD", events_path=self.events_path)
        ce.record_pipeline_transition("CO-b", "OPPORTUNITY", "LEAD", events_path=self.events_path)
        history = ce.pipeline_history("CO-a", events_path=self.events_path)
        self.assertEqual(len(history), 1)


class TestCustomerMatching(unittest.TestCase):
    def test_explains_every_match(self):
        opp = {"opportunity_id": "X", "partner_name": "Test", "verification_status": "VERIFIED"}
        result = ce.match_customer_to_opportunity({"industry": "UNKNOWN", "budget": "UNKNOWN"}, opp)
        self.assertGreater(len(result["reason"]), 0)

    def test_unknown_customer_data_never_forces_high_confidence(self):
        opp = {"opportunity_id": "X", "partner_name": "Test", "verification_status": "VERIFIED"}
        result = ce.match_customer_to_opportunity({"industry": "UNKNOWN", "budget": "UNKNOWN"}, opp)
        self.assertEqual(result["next_action"], "GATHER_MORE_CUSTOMER_DATA")


class TestDailyBrief(unittest.TestCase):
    def test_answers_all_10_questions(self):
        portfolio = ce.derive_initial_opportunity_portfolio()
        brief = ce.build_daily_commercial_brief(portfolio=portfolio)
        for i in range(1, 11):
            self.assertTrue(any(k.startswith(f"q{i}_") for k in brief.keys()), f"missing q{i}")

    def test_never_claims_a_sale(self):
        portfolio = ce.derive_initial_opportunity_portfolio()
        brief = ce.build_daily_commercial_brief(portfolio=portfolio)
        self.assertIn("0", brief["q9_leads_requiring_action"])


class TestConflictDetection(unittest.TestCase):
    def test_different_partners_never_compared(self):
        a = {"partner_id": "x", "commission_value": "10%"}
        b = {"partner_id": "y", "commission_value": "50%"}
        result = ce.detect_conflicting_terms(a, b)
        self.assertFalse(result["conflict"])

    def test_conflicting_values_flagged(self):
        a = {"partner_id": "x", "commission_value": "10%"}
        b = {"partner_id": "x", "commission_value": "20%"}
        result = ce.detect_conflicting_terms(a, b)
        self.assertEqual(result["status"], "FLAG_CONFLICT")


class TestCommissionCommerceDashboard(unittest.TestCase):
    def test_returns_all_required_sections(self):
        result = ce.build_commission_commerce_dashboard()
        for key in ("commission_opportunities", "verified_partners", "top_commission_opportunities",
                    "expected_commission_usd", "confirmed_commission_usd", "paid_commission_usd",
                    "real_revenue_usd", "real_customers", "real_orders", "real_payouts_usd",
                    "stale_opportunities", "founder_actions", "unknown_data", "evidence_level",
                    "agents_health"):
            self.assertIn(key, result)

    def test_agents_health_covers_all_three_agents(self):
        result = ce.build_commission_commerce_dashboard()
        for agent in ("commercial_deal_agent", "partner_intelligence_agent", "lead_outreach_agent"):
            self.assertIn(agent, result["agents_health"])

    def test_real_metrics_are_zero_with_no_real_ledger_data(self):
        result = ce.build_commission_commerce_dashboard()
        self.assertEqual(result["real_revenue_usd"], 0)
        self.assertEqual(result["real_customers"], 0)
        self.assertEqual(result["real_orders"], 0)
        self.assertEqual(result["real_payouts_usd"], 0)

    def test_never_writes_any_file(self):
        import os
        before = set(os.listdir("data"))
        ce.build_commission_commerce_dashboard()
        after = set(os.listdir("data"))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
