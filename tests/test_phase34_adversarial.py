"""Phase 34 (ADR-227), Section 13: adversarial testing for the 3 agents
+ the Section 12 voyage counts. Expected behavior: FAIL SAFE, FLAG,
LOG, ESCALATE -- never fabricate. Scenarios already covered by Phase
33's tests/test_commission_adversarial.py (hallucinated partner/
commission, stale partner, duplicate commission, fake payout, missing
evidence, conflicting terms, expired program, AI provider failure) are
not repeated here -- only the genuinely new scenarios this round's
directive adds."""

import os
import tempfile
import unittest

import commercial_deal_agent as cda
import commission_engine as ce
import commission_simulation as cs
import lead_outreach_agent as loa
import outreach_engine as oe
import partner_intelligence_agent as pia


class TestFakeCustomer(unittest.TestCase):
    def test_fake_customer_never_produces_real_match_confidence(self):
        opp = ce.load_opportunity_portfolio()[0]
        fake_customer = {"industry": "definitely not a real company", "budget": "definitely fake"}
        # No mechanism validates industry/budget strings as "real" --
        # the match honestly treats any non-empty value the same way,
        # since this factory has no real identity-verification signal.
        # The real safeguard is downstream: deal_priority_score() never
        # promotes this to a high-confidence deal without economics.
        result = cda.deal_priority_score(fake_customer, opp)
        self.assertIn(result["EXPECTED_VALUE"], ["UNKNOWN -- requires real deal-value and conversion-rate inputs"])


class TestFakeSale(unittest.TestCase):
    def test_fake_sale_rejected_at_ledger_level(self):
        import commission_ledger as cl
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            with self.assertRaises(cl.AntiFabricationError):
                cl.record_commission("p", "o", "CONFIRMED", 500.0, "REAL", evidence="claimed sale, no real transaction id", ledger_path=path)


class TestDuplicateLead(unittest.TestCase):
    def test_same_prospect_transitioned_twice_both_logged_not_merged(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.jsonl")
            loa.record_prospect_transition("P1", "TARGET_CUSTOMER", "PROSPECT", events_path=path)
            loa.record_prospect_transition("P1", "TARGET_CUSTOMER", "PROSPECT", events_path=path)
            history = loa.prospect_history("P1", events_path=path)
        self.assertEqual(len(history), 2, "both real events preserved for real reconciliation, never silently deduped away")


class TestDuplicateOutreach(unittest.TestCase):
    def test_second_contact_attempt_flagged_by_is_duplicate_contact(self):
        with tempfile.TemporaryDirectory() as d:
            log_path = os.path.join(d, "log.jsonl")
            draft = oe.draft_outreach_message({"opportunity_id": "lead1"}, {}, log_path=log_path)
            oe.approve_outreach(draft, approved_by="founder", log_path=log_path)
            result = loa.is_duplicate_contact("lead1", outreach_log_path=log_path)
        self.assertTrue(result["duplicate"])


class TestPartnerApiFailure(unittest.TestCase):
    def test_malformed_registry_data_never_crashes_categorization(self):
        result = pia.categorize_evidence_source("not a valid url at all", partner_domain="amazon")
        self.assertIn(result["category"], pia.EVIDENCE_SOURCE_CATEGORIES + ("UNKNOWN",))

    def test_missing_opportunity_fields_never_crash_scoring(self):
        # Simulates a partial/failed API response -- an opportunity
        # record missing most real fields.
        partial_opp = {"opportunity_id": "X"}
        result = ce.score_commission_opportunity(partial_opp)
        self.assertIn("dimensions", result)


class TestCrmFailure(unittest.TestCase):
    def test_corrupted_prospect_events_file_never_crashes_history_read(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                f.write("not valid json\n{also not valid\n")
            history = loa.prospect_history("P1", events_path=path)
        self.assertEqual(history, [])

    def test_corrupted_deal_events_file_never_crashes_agent_health(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                f.write("garbage\n")
            health = cda.agent_health(events_path=path)
        self.assertEqual(health["status"], "IDLE")


class TestNotificationFailure(unittest.TestCase):
    def test_agent_health_never_blocked_by_missing_notification_infra(self):
        # No real notification dispatch is wired to any of the 3 agents
        # yet (Phase 33's own disclosed scope decision) -- confirms
        # agent_health() computes purely from local event data, never
        # depends on a real Telegram call succeeding.
        with tempfile.TemporaryDirectory() as d:
            events_path = os.path.join(d, "events.jsonl")
            health = cda.agent_health(events_path=events_path)
        self.assertIn("status", health)


class TestPhase34SimulationCounts(unittest.TestCase):
    def test_matches_section_12_named_counts(self):
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            result = cs.run_phase34_commercial_voyage_simulation(ledger_path=ledger_path)
        self.assertEqual(result["partners"], 20)
        self.assertEqual(result["prospects"], 100)
        self.assertEqual(result["qualified_leads"], 30)
        self.assertEqual(result["outreach_responses"], 10)
        self.assertEqual(result["deals"], 5)

    def test_never_moves_real_commission_totals(self):
        import commission_ledger as cl
        before = cl.real_commission_summary()
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            cs.run_phase34_commercial_voyage_simulation(ledger_path=ledger_path)
        after = cl.real_commission_summary()
        self.assertEqual(before["real_commission_records"], after["real_commission_records"])


if __name__ == "__main__":
    unittest.main()
