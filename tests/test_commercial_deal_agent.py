import os
import tempfile
import unittest

import commercial_deal_agent as cda
import commission_engine as ce


class TestDealPriorityScore(unittest.TestCase):
    def setUp(self):
        self.opp = ce.load_opportunity_portfolio()[0]
        self.customer = {"pain_point": "UNKNOWN", "budget": "UNKNOWN", "urgency": "UNKNOWN"}

    def test_returns_all_11_named_factors(self):
        result = cda.deal_priority_score(self.customer, self.opp)
        self.assertEqual(len(result["factors"]), 11)

    def test_never_fabricates_expected_value_without_economics(self):
        result = cda.deal_priority_score(self.customer, self.opp)
        self.assertIn("UNKNOWN", result["EXPECTED_VALUE"])

    def test_expected_value_present_with_complete_economics(self):
        econ = ce.commission_economics(self.opp, expected_conversion_rate=0.1, expected_deal_value=1000)
        result = cda.deal_priority_score(self.customer, self.opp, economics=econ)
        self.assertIsInstance(result["EXPECTED_VALUE"], float)

    def test_low_confidence_when_most_factors_unknown(self):
        blank_customer = {}
        blank_opp = {"opportunity_id": "X", "commission_value": "COMMISSION_UNKNOWN"}
        result = cda.deal_priority_score(blank_customer, blank_opp)
        self.assertEqual(result["CONFIDENCE"], "LOW")

    def test_never_collapses_to_single_fabricated_number(self):
        result = cda.deal_priority_score(self.customer, self.opp)
        self.assertIsInstance(result["DEAL_SCORE"], str)
        self.assertIn("/", result["DEAL_SCORE"])


class TestDealStateTracking(unittest.TestCase):
    def test_track_deal_state_empty_for_unknown_opportunity(self):
        result = cda.track_deal_state("CO-does-not-exist")
        self.assertEqual(result, [])

    def test_monitor_commission_state_empty_for_unknown_opportunity(self):
        result = cda.monitor_commission_state("CO-does-not-exist")
        self.assertEqual(result, [])


class TestEscalation(unittest.TestCase):
    def test_high_risk_category_refuses_without_approval(self):
        result = cda.escalation_required("partner_exclusivity_or_territory_commitment")
        self.assertEqual(result["decision"], "REFUSE")

    def test_read_only_category_does_not_require_escalation(self):
        result = cda.escalation_required("read_only_reporting")
        self.assertNotEqual(result["decision"], "REFUSE")


class TestAgentHealth(unittest.TestCase):
    def test_no_events_reports_idle_honestly(self):
        with tempfile.TemporaryDirectory() as d:
            events_path = os.path.join(d, "events.jsonl")
            health = cda.agent_health(events_path=events_path)
        self.assertEqual(health["status"], "IDLE")
        self.assertIsNone(health["last_run"])

    def test_never_fabricates_error_rate_with_no_data(self):
        with tempfile.TemporaryDirectory() as d:
            events_path = os.path.join(d, "events.jsonl")
            health = cda.agent_health(events_path=events_path)
        self.assertIn("UNKNOWN", health["error_rate"])

    def test_returns_all_named_health_fields(self):
        with tempfile.TemporaryDirectory() as d:
            events_path = os.path.join(d, "events.jsonl")
            health = cda.agent_health(events_path=events_path)
        for field in ("status", "last_run", "last_success", "last_failure", "error_rate",
                      "queue_size", "current_task", "blocked_reason"):
            self.assertIn(field, health)

    def test_real_error_rate_computed_from_real_events(self):
        with tempfile.TemporaryDirectory() as d:
            events_path = os.path.join(d, "events.jsonl")
            ce.record_pipeline_transition("CO-x", "OPPORTUNITY", "VERIFIED_PARTNER", events_path=events_path)
            ce.record_pipeline_transition("CO-y", "OPPORTUNITY", "REJECTED", events_path=events_path)
            health = cda.agent_health(events_path=events_path)
        self.assertEqual(health["status"], "ACTIVE")
        self.assertEqual(health["error_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
