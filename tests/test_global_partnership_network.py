import unittest
from unittest.mock import patch

import global_partnership_network as gpn

_TEST_PLATFORM = "amazon"


class TestPartnerRegistry(unittest.TestCase):
    def test_reuses_real_platform_registry(self):
        result = gpn.partner_registry_report()
        self.assertGreater(result["total_real_platforms"], 0)
        self.assertIn("business_development.py", result["source"])


class TestPartnerScore(unittest.TestCase):
    def test_score_always_shows_components(self):
        result = gpn.partner_score(_TEST_PLATFORM)
        self.assertIn("components", result)
        for key in ("program_confirmed", "joinable_by_small_business", "strategic_fit"):
            self.assertIn(key, result["components"])

    def test_unknown_platform_never_fabricates_a_score(self):
        result = gpn.partner_score("a platform that has never been registered")
        self.assertIsNone(result["score"])


class TestPartnerQualification(unittest.TestCase):
    def test_classification_always_named(self):
        result = gpn.partner_qualification(_TEST_PLATFORM)
        self.assertIn(result["qualification"], gpn.QUALIFICATION_LEVELS)

    def test_never_auto_assigns_strategic_or_paused(self):
        result = gpn.partner_qualification(_TEST_PLATFORM)
        self.assertNotIn(result["qualification"], ("STRATEGIC", "PAUSED"))


class TestPartnerDueDiligence(unittest.TestCase):
    def test_never_relies_solely_on_partner_claims(self):
        result = gpn.partner_due_diligence(_TEST_PLATFORM)
        self.assertIn("real_evidence", result)
        self.assertNotIn("partner_provided_claim", result)


class TestReferralResellerDistributor(unittest.TestCase):
    def test_all_three_honestly_not_built(self):
        for fn in (gpn.referral_engine_status, gpn.reseller_engine_status, gpn.distributor_engine_status):
            result = fn()
            self.assertEqual(result["status"], "NOT_BUILT")


class TestCustomerOwnership(unittest.TestCase):
    def test_every_field_honestly_unknown_with_no_real_contract(self):
        result = gpn.customer_ownership_matrix(_TEST_PLATFORM)
        for key in ("owns_customer_relationship", "provides_support", "bills",
                    "delivers", "renews", "handles_refunds", "handles_complaints"):
            self.assertTrue(result[key].startswith("UNKNOWN"))


class TestPartnerLifecycle(unittest.TestCase):
    def test_mapping_covers_every_real_stage(self):
        import business_development as bd
        for stage in bd.STAGES:
            self.assertIn(stage, gpn.LIFECYCLE_MAPPING)

    def test_every_mapped_value_is_a_named_lifecycle_stage(self):
        for named in gpn.LIFECYCLE_MAPPING.values():
            self.assertIn(named, gpn.PARTNER_LIFECYCLE_STAGES)


class TestPartnerFraudDetection(unittest.TestCase):
    def test_never_auto_accuses(self):
        result = gpn.partner_fraud_status()
        self.assertEqual(result["current_state"], "NONE")
        self.assertEqual(result["open_investigations"], [])

    def test_four_named_states_plus_none(self):
        self.assertEqual(len(gpn.FRAUD_STATES), 5)


class TestPartnerConflictCheck(unittest.TestCase):
    def test_no_conflict_possible_with_fewer_than_two_active_partners(self):
        result = gpn.partner_conflict_check()
        self.assertEqual(result["conflicts_found"], [])


class TestPartnerSecurity(unittest.TestCase):
    def test_honestly_not_built(self):
        result = gpn.partner_security_status()
        self.assertEqual(result["status"], "NOT_BUILT")

    def test_nine_required_controls(self):
        result = gpn.partner_security_status()
        self.assertEqual(len(result["required_controls"]), 9)


class TestPartnerTermination(unittest.TestCase):
    def test_refuses_without_real_approval(self):
        result = gpn.partner_termination_check()
        self.assertEqual(result["contract_commitment"]["decision"], "REFUSE")
        self.assertEqual(result["exclusivity_or_territory_commitment"]["decision"], "REFUSE")

    def test_allows_with_real_explicit_approval(self):
        result = gpn.partner_termination_check(context={"founder_approved": True, "approval_reference": "board-vote-1"})
        self.assertEqual(result["contract_commitment"]["decision"], "ALLOW")


class TestDistributionNetworkHealth(unittest.TestCase):
    def test_never_a_single_fabricated_score(self):
        result = gpn.distribution_network_health()
        self.assertNotIn("overall_score", result)
        self.assertNotIn("composite_score", result)
        self.assertIn("components", result)

    def test_ten_named_components(self):
        result = gpn.distribution_network_health()
        self.assertEqual(len(result["components"]), 10)


class TestPartnerAttribution(unittest.TestCase):
    def test_never_invents_attribution(self):
        result = gpn.partner_attribution_status()
        self.assertLessEqual(result["events_with_real_partner_attribution"], result["total_real_sale_events"])


class TestBuildDashboard(unittest.TestCase):
    def test_aggregator_computes_every_subreport(self):
        result = gpn.build_partnership_network_dashboard()
        for key in ("real_business_development_dashboard", "lifecycle", "affiliate", "referral",
                    "reseller", "distributor", "attribution", "conflict_check", "fraud_status",
                    "security", "network_health", "integration_signals"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()
