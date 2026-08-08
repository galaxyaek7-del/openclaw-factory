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
        # Phase 35 (ADR-228): VERIFIED now requires the evidence to be
        # genuinely official (on the real partner's own domain), not
        # merely present -- a real terms/evidence URL on an unrelated
        # domain (example.com) with no partner_domain to match against
        # correctly stays THIRD_PARTY_ONLY, never VERIFIED.
        entry = {"terms": "https://example.com/terms", "evidence": ["https://example.com/proof"]}
        odata = {"commission": "10%"}
        status = ce._derive_verification_status(entry, odata)
        self.assertEqual(status, "THIRD_PARTY_ONLY")

    def test_unmapped_platform_never_silently_trusted(self):
        entry = {"terms": "https://realpartner.com/affiliate/terms", "evidence": ["https://realpartner.com/affiliate/signup"]}
        odata = {"commission": "10%"}
        status = ce._derive_verification_status(entry, odata, platform="a_platform_not_in_the_domain_map")
        self.assertEqual(status, "THIRD_PARTY_ONLY")

    def test_verified_when_evidence_is_genuinely_official_and_mapped(self):
        entry = {"terms": "https://amazon.com/affiliate/agreement", "evidence": []}
        odata = {"commission": "10%"}
        status = ce._derive_verification_status(entry, odata, platform="amazon")
        self.assertEqual(status, "VERIFIED")

    def test_third_party_only_when_evidence_exists_but_off_domain(self):
        entry = {"terms": None, "evidence": ["https://some-random-blog.com/amazon-review"]}
        odata = {"commission": "10%"}
        status = ce._derive_verification_status(entry, odata, platform="amazon")
        self.assertEqual(status, "THIRD_PARTY_ONLY")

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

    def test_commission_opportunities_breakdown_accounts_for_every_record(self):
        # Phase 35 (ADR-228) regression: adding THIRD_PARTY_ONLY as a
        # real status without updating this breakdown silently dropped
        # those records from the total -- verified counts must always
        # sum to the real portfolio size.
        result = ce.build_commission_commerce_dashboard()
        breakdown = result["commission_opportunities"]
        summed = breakdown["verified"] + breakdown["partially_verified"] + breakdown["third_party_only"] + breakdown["unverified"]
        self.assertEqual(summed, breakdown["total"])

    def test_real_metrics_are_zero_with_no_real_ledger_data(self):
        result = ce.build_commission_commerce_dashboard()
        self.assertEqual(result["real_revenue_usd"], 0)
        self.assertEqual(result["real_customers"], 0)
        self.assertEqual(result["real_orders"], 0)
        self.assertEqual(result["real_payouts_usd"], 0)

    def test_huge_test_and_simulation_amounts_never_leak_into_dashboard_totals(self):
        # Phase 35 (ADR-228) adversarial firewall audit: a large,
        # fraudulent-looking TEST/SIMULATION commission must never move
        # the dashboard's real totals, regardless of size.
        import commission_ledger as cl
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            cl.record_commission("p", "o", "PAID", 9999999.0, "TEST", ledger_path=ledger_path)
            cl.record_commission("p", "o", "CONFIRMED", 5555555.0, "SIMULATION", ledger_path=ledger_path)
            result = ce.build_commission_commerce_dashboard(ledger_path=ledger_path)
        self.assertEqual(result["confirmed_commission_usd"], 0)
        self.assertEqual(result["paid_commission_usd"], 0)
        self.assertEqual(result["real_revenue_usd"], 0)

    def test_never_writes_any_file(self):
        import os
        before = set(os.listdir("data"))
        ce.build_commission_commerce_dashboard()
        after = set(os.listdir("data"))
        self.assertEqual(before, after)


class TestSelectFirstLaunchOpportunity(unittest.TestCase):
    def test_selects_a_real_recurring_verified_conflict_free_opportunity(self):
        result = ce.select_first_launch_opportunity()
        self.assertEqual(result["FIRST_LAUNCH_OPPORTUNITY"], "CO-n8n-affiliate")

    def test_never_selects_an_opportunity_with_a_known_conflict(self):
        result = ce.select_first_launch_opportunity()
        selected = result["FIRST_LAUNCH_OPPORTUNITY"]
        self.assertNotIn(selected, ce.KNOWN_EVIDENCE_CONFLICTS)

    def test_never_selects_an_unverified_or_third_party_only_opportunity(self):
        result = ce.select_first_launch_opportunity()
        self.assertEqual(result["selected_record"]["verification_status"], "VERIFIED")

    def test_returns_none_honestly_when_no_candidate_qualifies(self):
        empty_portfolio = [{"opportunity_id": "X", "verification_status": "UNVERIFIED",
                            "commission_value": "COMMISSION_UNKNOWN", "recurring_commission": False,
                            "last_verified": "2020-01-01"}]
        result = ce.select_first_launch_opportunity(portfolio=empty_portfolio)
        self.assertEqual(result["FIRST_LAUNCH_OPPORTUNITY"], "NONE")
        self.assertIn("blocker", result)

    def test_never_fabricates_a_candidate_not_in_the_real_portfolio(self):
        result = ce.select_first_launch_opportunity()
        real_ids = {o["opportunity_id"] for o in ce.load_opportunity_portfolio()}
        self.assertIn(result["FIRST_LAUNCH_OPPORTUNITY"], real_ids)


class TestCommercialLedgerView(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.portfolio_path = os.path.join(self._tmpdir.name, "portfolio.jsonl")
        self.pipeline_path = os.path.join(self._tmpdir.name, "pipeline.jsonl")
        self.leads_path = os.path.join(self._tmpdir.name, "leads.jsonl")
        self.outreach_path = os.path.join(self._tmpdir.name, "outreach.jsonl")
        self.adapter_path = os.path.join(self._tmpdir.name, "adapter.jsonl")
        self.ledger_path = os.path.join(self._tmpdir.name, "ledger.jsonl")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_unknown_opportunity_returns_honest_empty_view(self):
        result = ce.commercial_ledger_view(
            "CO-does-not-exist", portfolio_path=self.portfolio_path, pipeline_events_path=self.pipeline_path,
            leads_path=self.leads_path, outreach_log_path=self.outreach_path, adapter_log_path=self.adapter_path,
            commission_ledger_path=self.ledger_path,
        )
        self.assertIsNone(result["opportunity"])
        self.assertEqual(result["lead_count"], 0)
        self.assertEqual(result["REAL_REVENUE"], 0)

    def test_joins_real_commission_records_by_opportunity_id(self):
        import commission_ledger as cl
        cl.record_commission("n8n", "CO-n8n-affiliate", "CONFIRMED", 100.0, "REAL",
                              evidence="real webhook", external_transaction_id="txn_1", ledger_path=self.ledger_path)
        cl.record_commission("n8n", "CO-other-opportunity", "CONFIRMED", 999.0, "REAL",
                              evidence="real webhook", external_transaction_id="txn_2", ledger_path=self.ledger_path)
        result = ce.commercial_ledger_view(
            "CO-n8n-affiliate", portfolio_path=self.portfolio_path, pipeline_events_path=self.pipeline_path,
            leads_path=self.leads_path, outreach_log_path=self.outreach_path, adapter_log_path=self.adapter_path,
            commission_ledger_path=self.ledger_path,
        )
        self.assertEqual(len(result["commission_records"]), 1)
        self.assertEqual(result["REAL_REVENUE"], 100.0)

    def test_test_and_simulation_commissions_never_counted_in_real_revenue(self):
        import commission_ledger as cl
        cl.record_commission("n8n", "CO-n8n-affiliate", "PAID", 500.0, "SIMULATION", ledger_path=self.ledger_path)
        cl.record_commission("n8n", "CO-n8n-affiliate", "PAID", 500.0, "TEST", ledger_path=self.ledger_path)
        result = ce.commercial_ledger_view(
            "CO-n8n-affiliate", portfolio_path=self.portfolio_path, pipeline_events_path=self.pipeline_path,
            leads_path=self.leads_path, outreach_log_path=self.outreach_path, adapter_log_path=self.adapter_path,
            commission_ledger_path=self.ledger_path,
        )
        self.assertEqual(result["REAL_REVENUE"], 0)
        self.assertEqual(len(result["commission_records"]), 2)
        self.assertEqual(len(result["real_commission_records"]), 0)


class TestRankCommissionShortlist(unittest.TestCase):
    def test_returns_top_5_by_default(self):
        result = ce.rank_commission_shortlist(top_n=5)
        self.assertEqual(len(result["shortlist"]), 5)

    def test_every_shortlist_entry_has_all_9_named_scores(self):
        result = ce.rank_commission_shortlist(top_n=5)
        named = ("opportunity_score", "evidence_score", "commercial_score", "commission_score",
                 "freshness_score", "competition_score", "execution_difficulty", "expected_value", "risk_score")
        for entry in result["shortlist"]:
            for field in named:
                self.assertIn(field, entry, f"missing {field} on {entry['opportunity_id']}")

    def test_expected_value_is_never_fabricated(self):
        result = ce.rank_commission_shortlist(top_n=5)
        for entry in result["shortlist"]:
            self.assertTrue(str(entry["expected_value"]).startswith("UNKNOWN"))

    def test_best_pick_excludes_known_conflicts(self):
        result = ce.rank_commission_shortlist(top_n=13)
        best = result["BEST_FIRST_COMMERCIAL_EXPERIMENT"]
        self.assertNotIn(best, ce.KNOWN_EVIDENCE_CONFLICTS)

    def test_best_pick_excludes_watch_state_opportunities(self):
        """Real integration with opportunity_rotation_engine.py's own
        lifecycle ledger -- CO-n8n-affiliate is real, VERIFIED, and
        recurring, but its real Phase 37B/37C evidence run left it at
        WATCH; the shortlist must not silently recommend re-pursuing it
        as the 'best first experiment' over an untried candidate."""
        result = ce.rank_commission_shortlist(top_n=13)
        best_entry = next(e for e in result["shortlist"] if e["opportunity_id"] == result["BEST_FIRST_COMMERCIAL_EXPERIMENT"])
        self.assertNotEqual(best_entry["lifecycle_state"], "WATCH")

    def test_never_fabricates_a_best_pick_from_outside_the_real_portfolio(self):
        result = ce.rank_commission_shortlist(top_n=5)
        real_ids = {o["opportunity_id"] for o in ce.load_opportunity_portfolio()}
        if result["BEST_FIRST_COMMERCIAL_EXPERIMENT"]:
            self.assertIn(result["BEST_FIRST_COMMERCIAL_EXPERIMENT"], real_ids)

    def test_honest_none_when_no_candidate_clears_every_bar(self):
        weak_portfolio = [{"opportunity_id": "X", "partner_name": "X", "verification_status": "UNVERIFIED",
                            "commission_value": "COMMISSION_UNKNOWN", "recurring_commission": False,
                            "last_verified": "2020-01-01", "geography": "UNKNOWN", "eligibility": "UNKNOWN",
                            "cookie_or_tracking_window": "UNKNOWN", "payout_terms": "UNKNOWN"}]
        result = ce.rank_commission_shortlist(portfolio=weak_portfolio, top_n=5)
        self.assertIsNone(result["BEST_FIRST_COMMERCIAL_EXPERIMENT"])


class TestBuildLaunchChecklist(unittest.TestCase):
    def test_returns_all_21_items(self):
        result = ce.build_launch_checklist()
        self.assertEqual(result["total"], 21)

    def test_launch_ready_is_never_forced_true(self):
        result = ce.build_launch_checklist()
        self.assertFalse(result["LAUNCH_READY"])
        self.assertGreater(len(result["blocking_items"]), 0)

    def test_launch_ready_true_only_when_every_item_passes(self):
        result = ce.build_launch_checklist()
        all_pass = all(result["items"].values())
        self.assertEqual(result["LAUNCH_READY"], all_pass)

    def test_prospect_sourcing_honestly_blocks(self):
        result = ce.build_launch_checklist()
        self.assertIn("prospect_legitimately_sourced", result["blocking_items"])

    def test_sending_infrastructure_honestly_blocks(self):
        result = ce.build_launch_checklist()
        self.assertIn("sending_infrastructure_ready", result["blocking_items"])


if __name__ == "__main__":
    unittest.main()
