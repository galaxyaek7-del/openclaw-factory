import os
import tempfile
import unittest

import commission_engine as ce
import lead_outreach_agent as loa


class TestProspectPipeline(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "events.jsonl")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_valid_transition_recorded(self):
        result = loa.record_prospect_transition("P1", "PROSPECT", "RESEARCHED", events_path=self.path)
        self.assertTrue(result["ok"])

    def test_invalid_state_rejected(self):
        result = loa.record_prospect_transition("P1", "PROSPECT", "NOT_A_REAL_STATE", events_path=self.path)
        self.assertFalse(result["ok"])

    def test_terminal_exits_valid(self):
        for exit_state in loa.PROSPECT_PIPELINE_TERMINAL_EXITS:
            result = loa.record_prospect_transition("P1", "QUALIFIED_DEAL", exit_state, events_path=self.path)
            self.assertTrue(result["ok"])

    def test_history_filters_by_prospect(self):
        loa.record_prospect_transition("P1", "PROSPECT", "RESEARCHED", events_path=self.path)
        loa.record_prospect_transition("P2", "PROSPECT", "RESEARCHED", events_path=self.path)
        history = loa.prospect_history("P1", events_path=self.path)
        self.assertEqual(len(history), 1)


class TestExplainCustomerMatch(unittest.TestCase):
    def setUp(self):
        self.opp = ce.load_opportunity_portfolio()[0]

    def test_returns_all_6_named_fields(self):
        result = loa.explain_customer_match({"industry": "UNKNOWN", "budget": "UNKNOWN"}, self.opp)
        for field in ("WHY_THIS_CUSTOMER", "WHY_THIS_PARTNER", "WHY_NOW", "WHY_THIS_OFFER", "EXPECTED_VALUE", "RISK"):
            self.assertIn(field, result)

    def test_never_returns_only_a_numerical_score(self):
        result = loa.explain_customer_match({"industry": "UNKNOWN", "budget": "UNKNOWN"}, self.opp)
        self.assertIsInstance(result["WHY_THIS_CUSTOMER"], str)
        self.assertGreater(len(result["WHY_THIS_CUSTOMER"]), 10)

    def test_unknown_customer_data_never_falsely_claims_real_signals(self):
        result = loa.explain_customer_match({"industry": "UNKNOWN", "budget": "UNKNOWN"}, self.opp)
        self.assertNotIn("Real signals present", result["WHY_THIS_CUSTOMER"])

    def test_real_customer_data_correctly_cited(self):
        result = loa.explain_customer_match({"industry": "software", "budget": "5000-20000"}, self.opp)
        self.assertIn("Real signals present", result["WHY_THIS_CUSTOMER"])

    def test_stale_data_flagged_in_why_now(self):
        opp = dict(self.opp)
        opp["last_verified"] = "2020-01-01"
        result = loa.explain_customer_match({}, opp)
        self.assertIn("STALE", result["WHY_NOW"])


class TestDuplicateContact(unittest.TestCase):
    def test_no_log_no_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            log_path = os.path.join(d, "log.jsonl")
            result = loa.is_duplicate_contact("lead1", outreach_log_path=log_path)
        self.assertFalse(result["duplicate"])

    def test_prior_approved_contact_flagged(self):
        import outreach_engine as oe
        with tempfile.TemporaryDirectory() as d:
            log_path = os.path.join(d, "log.jsonl")
            draft = oe.draft_outreach_message({"opportunity_id": "lead1"}, {}, log_path=log_path)
            oe.approve_outreach(draft, approved_by="founder", log_path=log_path)
            result = loa.is_duplicate_contact("lead1", outreach_log_path=log_path)
        self.assertTrue(result["duplicate"])


class TestAgentHealth(unittest.TestCase):
    def test_no_events_reports_idle(self):
        with tempfile.TemporaryDirectory() as d:
            events_path = os.path.join(d, "events.jsonl")
            health = loa.agent_health(events_path=events_path)
        self.assertEqual(health["status"], "IDLE")

    def test_blocked_reason_cites_no_send_credential(self):
        with tempfile.TemporaryDirectory() as d:
            events_path = os.path.join(d, "events.jsonl")
            health = loa.agent_health(events_path=events_path)
        self.assertIn("credential", health["blocked_reason"].lower())


if __name__ == "__main__":
    unittest.main()
