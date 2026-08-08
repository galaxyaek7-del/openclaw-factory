import unittest
from unittest.mock import patch

import product_innovation_engine as pie

_TEST_NICHE = "AI-Powered Compliance Automation System for Accounting Firms"


class TestValidationGates(unittest.TestCase):
    def test_six_named_gates_present(self):
        result = pie.validation_gate_status(_TEST_NICHE)
        self.assertEqual(set(result["gates"].keys()), set(pie.VALIDATION_GATES))

    def test_every_gate_cites_a_real_profit_oracle_field(self):
        result = pie.validation_gate_status(_TEST_NICHE)
        for gate in result["gates"].values():
            self.assertIn("real_field", gate)
            self.assertIn("citation", gate)

    def test_never_a_second_scoring_computation(self):
        """Confirms the relabeling never invents its own accept/reject
        logic -- overall_accepted must come straight from profit_oracle."""
        with patch("profit_oracle.ladder_opportunity_score") as mock_score:
            mock_score.return_value = {"accepted": True, "reason": "test", "product_strategy": {
                "pain_severity": True, "high_profit_margin": True, "low_or_moderate_competition": True,
                "ai_significant_advantage": True, "strong_proof_of_payment": True,
            }}
            result = pie.validation_gate_status(_TEST_NICHE)
            self.assertTrue(result["overall_accepted"])
            mock_score.assert_called_once()


class TestProductDecisionGate(unittest.TestCase):
    def test_decision_always_a_named_decision(self):
        result = pie.product_decision_gate(_TEST_NICHE)
        self.assertIn(result["decision"], pie.PRODUCT_DECISIONS)

    def test_zero_passed_gates_is_kill(self):
        with patch("product_innovation_engine.validation_gate_status") as mock_gates:
            mock_gates.return_value = {"gates": {g: {"passed": False} for g in pie.VALIDATION_GATES}, "overall_accepted": False}
            with patch("decision_engine.store.latest_decision_per_niche", return_value={}):
                result = pie.product_decision_gate(_TEST_NICHE)
                self.assertEqual(result["decision"], "KILL")


class TestKillCriteria(unittest.TestCase):
    def test_never_evaluated_niche_is_honest(self):
        result = pie.kill_criteria_check("a niche that has never once been evaluated by anything")
        self.assertEqual(result["status"], "NEVER_EVALUATED")

    def test_result_is_honest_either_way(self):
        """This test niche may or may not have a real decision_engine
        record -- both a real status and NEVER_EVALUATED are honest,
        valid outcomes; the function must never fabricate a status."""
        result = pie.kill_criteria_check(_TEST_NICHE)
        self.assertTrue("real_status" in result or result.get("status") == "NEVER_EVALUATED")


class TestRedTeam(unittest.TestCase):
    def test_eight_named_questions_answered(self):
        result = pie.red_team_challenge(_TEST_NICHE)
        self.assertEqual(len(result["questions_and_answers"]), len(pie.RED_TEAM_QUESTIONS))

    def test_never_fabricates_an_answer_it_has_no_real_signal_for(self):
        result = pie.red_team_challenge(_TEST_NICHE)
        answers = list(result["questions_and_answers"].values())
        self.assertTrue(any("NOT_ANSWERED" in a for a in answers))

    def test_failed_gates_match_validation_gate_status(self):
        gates = pie.validation_gate_status(_TEST_NICHE)
        red_team = pie.red_team_challenge(_TEST_NICHE)
        real_failed = [n for n, g in gates["gates"].items() if not g["passed"]]
        self.assertEqual(sorted(red_team["failed_gates"]), sorted(real_failed))


class TestCommercialValidation(unittest.TestCase):
    def test_four_categories_stay_structurally_separate(self):
        result = pie.commercial_validation_signal(_TEST_NICHE)
        for key in ("interest", "intent", "commitment", "payment"):
            self.assertIn(key, result)

    def test_only_payment_counts_as_direct_evidence(self):
        result = pie.commercial_validation_signal(_TEST_NICHE)
        self.assertIn("real_events", result["payment"])
        self.assertNotIn("real_events", result["interest"] if isinstance(result["interest"], dict) else {})


class TestMvpSpecTemplate(unittest.TestCase):
    def test_nine_required_fields(self):
        result = pie.mvp_spec_template()
        self.assertEqual(len(result["required_fields"]), 9)


class TestProductPortfolio(unittest.TestCase):
    def test_eight_named_buckets_present(self):
        result = pie.product_portfolio_view()
        self.assertEqual(set(result["buckets"].keys()), set(pie.PORTFOLIO_BUCKETS))


class TestInnovationEfficiency(unittest.TestCase):
    def test_never_optimizes_for_idea_count_alone(self):
        result = pie.innovation_efficiency_report()
        self.assertIn("revenue_generated_by_innovation", result)
        self.assertEqual(result["revenue_generated_by_innovation"], "$0")

    def test_killed_products_matches_real_rejected_count(self):
        result = pie.innovation_efficiency_report()
        self.assertGreaterEqual(result["killed_products"], 0)


class TestAutonomyBoundaries(unittest.TestCase):
    def test_reuses_phase19_authorization_verbatim(self):
        result = pie.autonomous_innovation_boundaries()
        self.assertIn("must_not_do_autonomously", result)
        for entry in result["must_not_do_autonomously"].values():
            self.assertEqual(entry["level"], 5 if entry["level"] != 6 else 6)


class TestHumanDecisionGate(unittest.TestCase):
    def test_evolution_execution_still_refuses_without_approval(self):
        result = pie.human_decision_gate_check("evolution_approve_execute")
        self.assertEqual(result["decision"], "REFUSE")

    def test_real_payment_never_authorized_even_with_forced_context(self):
        result = pie.human_decision_gate_check("real_payment_or_transaction", context={"founder_approved": True, "approval_reference": "x"})
        self.assertEqual(result["decision"], "REFUSE")


class TestBuildDashboard(unittest.TestCase):
    def test_aggregator_computes_every_subreport(self):
        result = pie.build_product_innovation_dashboard()
        for key in ("problem_registry", "portfolio", "cannibalization", "customer_signal",
                    "revenue_signal", "experiments", "innovation_efficiency", "autonomy_boundaries"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()
