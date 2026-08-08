import unittest
from unittest.mock import patch

import enterprise_transformation_engine as ete

_TEST_NICHE = "AI-Powered Compliance Automation System for Accounting Firms"


class TestROIEngine(unittest.TestCase):
    def test_none_value_is_unknown_never_zero(self):
        result = ete.roi_evidence_tier(None, "no source")
        self.assertEqual(result["tier"], "UNKNOWN")

    def test_provided_value_defaults_to_estimated_never_verified(self):
        result = ete.roi_evidence_tier(5000, "founder estimate")
        self.assertEqual(result["tier"], "ESTIMATED")

    def test_roi_model_uses_all_named_tiers(self):
        result = ete.roi_model()
        for field in ("current_cost", "transformation_cost", "expected_savings"):
            self.assertIn(result[field]["tier"], ete.ROI_EVIDENCE_TIERS)


class TestQualification(unittest.TestCase):
    def test_classification_always_named(self):
        result = ete.qualify_opportunity(_TEST_NICHE)
        self.assertIn(result["qualification"], ete.QUALIFICATION_LEVELS)

    def test_zero_gates_passed_is_disqualified(self):
        with patch("product_innovation_engine.validation_gate_status") as mock_gates:
            mock_gates.return_value = {"gates": {g: {"passed": False} for g in ["A", "B", "C", "D", "E", "F"]}}
            result = ete.qualify_opportunity(_TEST_NICHE)
            self.assertEqual(result["qualification"], "DISQUALIFIED")

    def test_never_auto_assigns_enterprise_tier(self):
        with patch("product_innovation_engine.validation_gate_status") as mock_gates:
            mock_gates.return_value = {"gates": {g: {"passed": True} for g in ["A", "B", "C", "D", "E", "F"]}}
            result = ete.qualify_opportunity(_TEST_NICHE)
            self.assertNotEqual(result["qualification"], "ENTERPRISE")


class TestDecisionMakerIntelligence(unittest.TestCase):
    def test_never_fabricates_a_name_or_contact(self):
        result = ete.decision_maker_intelligence()
        for role, value in result["roles"].items():
            self.assertTrue(value.startswith("UNKNOWN"))


class TestVerticalSolutionEngine(unittest.TestCase):
    def test_never_enters_a_vertical_without_evidence(self):
        result = ete.vertical_solution_status()
        self.assertEqual(result["validated_verticals"], [])


class TestZeroHallucinationMode(unittest.TestCase):
    def test_reuses_evidence_engine_not_a_second_scanner(self):
        result = ete.zero_hallucination_check("We deployed this for the customer.")
        self.assertIn("evidence_engine.py", result["source"])

    def test_three_required_labels(self):
        self.assertEqual(len(ete.ZERO_HALLUCINATION_LABELS), 3)


class TestKnowledgeSystemAndSecurity(unittest.TestCase):
    def test_knowledge_system_honestly_not_built(self):
        result = ete.knowledge_system_status()
        self.assertEqual(result["status"], "NOT_BUILT")

    def test_multi_tenancy_honestly_not_built(self):
        result = ete.multi_tenancy_status()
        self.assertEqual(result["status"], "NOT_BUILT")

    def test_integrations_honestly_not_built(self):
        result = ete.enterprise_integration_status()
        self.assertEqual(result["status"], "NOT_BUILT")


class TestContractSafety(unittest.TestCase):
    def test_contract_commitment_refuses_without_approval(self):
        result = ete.contract_safety_check()
        self.assertEqual(result["contract_commitment"]["decision"], "REFUSE")

    def test_legal_liability_never_authorized_even_with_forced_context(self):
        result = ete.contract_safety_check(context={"founder_approved": True, "approval_reference": "x"})
        self.assertEqual(result["legal_or_liability_commitment"]["decision"], "REFUSE")
        self.assertEqual(result["legal_or_liability_commitment"]["required_level"], 6)


class TestReusabilityInventory(unittest.TestCase):
    def test_finds_real_reusable_components(self):
        result = ete.reusability_inventory()
        self.assertGreater(result["total_found"], 0)
        for entry in result["reusable_components"]:
            self.assertGreaterEqual(entry["real_dependent_count"], 2)


class TestKnowledgeProtection(unittest.TestCase):
    def test_policy_present(self):
        result = ete.knowledge_protection_policy()
        self.assertIn("Never reuse", result["policy"])


class TestAutonomousBoundaries(unittest.TestCase):
    def test_must_not_categories_are_level_5_or_6(self):
        result = ete.autonomous_enterprise_boundaries()
        for entry in result["must_not_autonomously"].values():
            self.assertIn(entry["level"], (5, 6))


class TestExpansionOpportunities(unittest.TestCase):
    def test_never_infers_expansion_ahead_of_real_success(self):
        result = ete.expansion_opportunities()
        self.assertEqual(result["real_expansion_signals"], [])


class TestBuildDashboard(unittest.TestCase):
    def test_aggregator_computes_every_subreport(self):
        result = ete.build_enterprise_transformation_dashboard()
        for key in ("problem_registry", "discovery_pipeline", "vertical_status", "knowledge_system",
                    "security", "multi_tenancy", "integrations", "revenue_model", "product_conversion",
                    "reusability", "success_metrics", "expansion", "autonomy_boundaries"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()
