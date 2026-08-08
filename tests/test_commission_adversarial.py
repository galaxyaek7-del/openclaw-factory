"""Phase 33, Section 15: adversarial testing. Expected behavior across
every scenario: FAIL SAFE, FLAG, LOG, DO NOT INVENT -- never a
fabricated success."""

import os
import tempfile
import unittest

import commission_engine as ce
import commission_ledger as cl
import outreach_engine as oe


class TestFakePartnerAndCommission(unittest.TestCase):
    def test_fake_partner_never_marked_verified(self):
        # No terms, no evidence -- the hallmark of an AI-hallucinated or fabricated partner.
        entry = {"terms": None, "evidence": []}
        odata = {"commission": "50%"}
        status = ce._derive_verification_status(entry, odata)
        self.assertNotEqual(status, "VERIFIED")

    def test_fake_commission_rejected_at_ledger_level(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            with self.assertRaises(cl.AntiFabricationError):
                cl.record_commission("fake-partner", "fake-opp", "PAID", 999999.0, "REAL", ledger_path=path)


class TestStaleAndExpired(unittest.TestCase):
    def test_stale_commission_data_flagged_stale(self):
        from datetime import datetime, timezone, timedelta
        old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        self.assertEqual(ce._freshness_from_last_verified(old), "STALE")

    def test_expired_program_same_mechanism_as_stale(self):
        # "Expired program" has no distinct signal beyond staleness in
        # this factory's real data model -- verified this is the same,
        # honest mechanism, not a silently-different one.
        from datetime import datetime, timezone, timedelta
        very_old = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        self.assertEqual(ce._freshness_from_last_verified(very_old), "STALE")


class TestConflictingTerms(unittest.TestCase):
    def test_conflicting_commission_flagged_not_resolved(self):
        a = {"partner_id": "x", "commission_value": "10%", "commission_currency": "USD"}
        b = {"partner_id": "x", "commission_value": "20%", "commission_currency": "USD"}
        result = ce.detect_conflicting_terms(a, b)
        self.assertEqual(result["status"], "FLAG_CONFLICT")

    def test_no_conflict_when_terms_agree(self):
        a = {"partner_id": "x", "commission_value": "10%", "commission_currency": "USD"}
        b = {"partner_id": "x", "commission_value": "10%", "commission_currency": "USD"}
        result = ce.detect_conflicting_terms(a, b)
        self.assertFalse(result["conflict"])


class TestDuplicateCommission(unittest.TestCase):
    def test_duplicate_commission_ids_both_recorded_but_distinguishable(self):
        # commission_ledger.py does not silently merge -- both real
        # records exist with their own real created_at, so a downstream
        # reconciliation can detect the duplicate rather than losing it.
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            cl.record_commission("p", "o", "PAID", 100.0, "REAL", evidence="evidence-1",
                                  external_transaction_id="txn_dup", ledger_path=path)
            cl.record_commission("p", "o", "PAID", 100.0, "REAL", evidence="evidence-2",
                                  external_transaction_id="txn_dup", ledger_path=path)
            records = cl.load_ledger(ledger_path=path)
            txn_ids = [r["external_transaction_id"] for r in records]
            self.assertEqual(txn_ids.count("txn_dup"), 2, "both records preserved for real reconciliation, never silently dropped")


class TestFakeOrderAndPayout(unittest.TestCase):
    def test_fake_order_rejected_same_as_fake_commission(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            with self.assertRaises(cl.AntiFabricationError):
                cl.record_commission("p", "fake-order", "CONFIRMED", 50.0, "REAL", evidence="e", ledger_path=path)

    def test_fake_payout_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            with self.assertRaises(cl.AntiFabricationError):
                cl.record_commission("p", "o", "PAID", 50.0, "REAL", evidence="e", ledger_path=path)


class TestMissingData(unittest.TestCase):
    def test_missing_customer_in_matching_is_honest(self):
        opp = {"opportunity_id": "X", "partner_name": "Test", "verification_status": "VERIFIED"}
        result = ce.match_customer_to_opportunity({}, opp)
        self.assertIn("UNKNOWN", " ".join(result["reason"]))

    def test_missing_partner_id_in_economics_never_crashes(self):
        opp = {}
        result = ce.commission_economics(opp)
        self.assertEqual(result["economic_status"], "INCOMPLETE")

    def test_missing_evidence_blocks_real_commission(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            with self.assertRaises(cl.AntiFabricationError):
                cl.record_commission("p", "o", "EXPECTED", 10.0, "REAL", evidence=None, ledger_path=path)


class TestInvalidCredentialAndOutage(unittest.TestCase):
    def test_invalid_webhook_credential_rejected(self):
        from channels import paddle_webhook
        with tempfile.TemporaryDirectory() as d:
            events_path = os.path.join(d, "events.jsonl")
            result = paddle_webhook.process_paddle_webhook(b"{}", "ts=1;h1=bad", secret="wrong_secret", processed_events_path=events_path)
        self.assertEqual(result["status"], "REJECTED")

    def test_outreach_send_reports_no_credential_never_fabricates_sent(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "log.jsonl")
            draft = oe.draft_outreach_message({"opportunity_id": "X"}, {}, log_path=path)
            approved = oe.approve_outreach(draft, approved_by="founder", log_path=path)["draft"]
            result = oe.send_outreach(approved, sending_credential_env_var="DEFINITELY_NOT_A_REAL_ENV_VAR", log_path=path)
        self.assertEqual(result["state"], "BLOCKED_NO_CREDENTIAL")


class TestPartialApiResponse(unittest.TestCase):
    def test_malformed_webhook_payload_never_partially_accepted(self):
        from channels import paddle_webhook
        with tempfile.TemporaryDirectory() as d:
            events_path = os.path.join(d, "events.jsonl")
            result = paddle_webhook.process_paddle_webhook(b"{incomplete", "ts=1;h1=x", secret="s", processed_events_path=events_path)
        self.assertEqual(result["status"], "REJECTED")


class TestAiHallucination(unittest.TestCase):
    def test_hallucinated_partner_with_no_real_terms_never_verified(self):
        # Simulates an AI claiming a partner program exists with no
        # real backing evidence -- the mechanical check must reject it
        # regardless of how confident the claim reads.
        entry = {"display_name": "Totally Real Partner Program", "terms": None, "evidence": []}
        odata = {"commission": "90% -- an unusually generous rate an AI might hallucinate", "status": "REAL"}
        status = ce._derive_verification_status(entry, odata)
        self.assertIn(status, ("UNVERIFIED",))

    def test_hallucinated_price_never_enters_economics_as_observed(self):
        opp = {"opportunity_id": "X", "commission_value": "10%"}
        # An AI-suggested conversion rate must be explicitly tagged --
        # never silently treated as OBSERVED.
        result = ce.commission_economics(opp, expected_conversion_rate=0.5, conversion_rate_basis="SIMULATED",
                                          expected_deal_value=100)
        self.assertEqual(result["conversion_rate_basis"], "SIMULATED")

    def test_hallucinated_commission_rejected_by_real_ledger_guard(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            # An AI claiming a huge real commission with no evidence must
            # still be rejected -- the guard doesn't special-case "large."
            with self.assertRaises(cl.AntiFabricationError):
                cl.record_commission("p", "o", "PAID", 1000000.0, "REAL", ledger_path=path)


if __name__ == "__main__":
    unittest.main()
