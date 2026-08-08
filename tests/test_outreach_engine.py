import os
import tempfile
import unittest

import outreach_engine as oe

_OPP = {"opportunity_id": "CO-x", "program_name": "Test Program", "partner_name": "Test Partner", "customer_problem": "testing"}


class TestDraftOutreachMessage(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "log.jsonl")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_draft_starts_in_draft_state(self):
        draft = oe.draft_outreach_message(_OPP, {}, log_path=self.path)
        self.assertEqual(draft["state"], "DRAFT")

    def test_template_mode_never_calls_real_ai(self):
        draft = oe.draft_outreach_message(_OPP, {}, use_real_ai=False, log_path=self.path)
        self.assertIn("TEMPLATE DRAFT", draft["message_text"])


class TestApprovalGate(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "log.jsonl")
        self.draft = oe.draft_outreach_message(_OPP, {}, log_path=self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_send_blocked_without_approval(self):
        result = oe.send_outreach(self.draft, log_path=self.path)
        self.assertEqual(result["state"], "BLOCKED_NOT_APPROVED")

    def test_approval_requires_a_real_identity(self):
        result = oe.approve_outreach(self.draft, approved_by=None, log_path=self.path)
        self.assertFalse(result["ok"])

    def test_approval_succeeds_with_identity(self):
        result = oe.approve_outreach(self.draft, approved_by="founder", log_path=self.path)
        self.assertTrue(result["ok"])
        self.assertEqual(result["draft"]["state"], "APPROVED")

    def test_rejection_recorded(self):
        result = oe.reject_outreach(self.draft, rejected_by="founder", reason="too generic", log_path=self.path)
        self.assertEqual(result["draft"]["state"], "REJECTED")

    def test_rejected_draft_cannot_be_sent(self):
        rejected = oe.reject_outreach(self.draft, rejected_by="founder", log_path=self.path)
        result = oe.send_outreach(rejected["draft"], log_path=self.path)
        self.assertEqual(result["state"], "BLOCKED_NOT_APPROVED")


class TestSendGate(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "log.jsonl")
        draft = oe.draft_outreach_message(_OPP, {}, log_path=self.path)
        self.approved = oe.approve_outreach(draft, approved_by="founder", log_path=self.path)["draft"]

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_approved_send_blocked_no_credential(self):
        result = oe.send_outreach(self.approved, log_path=self.path)
        self.assertEqual(result["state"], "BLOCKED_NO_CREDENTIAL")

    def test_never_fabricates_a_sent_result(self):
        result = oe.send_outreach(self.approved, log_path=self.path)
        self.assertFalse(result["ok"])
        self.assertNotEqual(result.get("state"), "SENT")


class TestAuditTrail(unittest.TestCase):
    def test_full_lifecycle_is_traceable(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "log.jsonl")
            draft = oe.draft_outreach_message(_OPP, {}, log_path=path)
            approved = oe.approve_outreach(draft, approved_by="founder", log_path=path)["draft"]
            oe.send_outreach(approved, log_path=path)
            trail = oe.outreach_audit_trail(draft["draft_id"], log_path=path)
            events = [e["event"] for e in trail]
            self.assertIn("DRAFTED", events)
            self.assertIn("APPROVED", events)
            self.assertIn("SEND_ATTEMPT_BLOCKED", events)


class TestOutreachAdapterStatus(unittest.TestCase):
    def test_no_credential_reports_no_credential_state(self):
        result = oe.outreach_adapter_status(sending_credential_env_var="DEFINITELY_NOT_A_REAL_ENV_VAR")
        self.assertEqual(result["state"], "NO_CREDENTIAL")

    def test_never_claims_live_when_only_code_exists(self):
        result = oe.outreach_adapter_status()
        self.assertNotEqual(result["state"], "LIVE")

    def test_returns_all_11_named_capabilities(self):
        result = oe.outreach_adapter_status()
        self.assertEqual(len(result["capabilities"]), 11)

    def test_sending_adapter_exists_but_state_still_reports_no_credential(self):
        """Phase 37A (ADR-230) built a real adapter (outreach_adapter.py::
        SMTPOutreachAdapter) -- exists=True now honestly reflects that.
        The overall state must still never claim LIVE just because code
        exists: no real SMTP credential is configured, so state stays
        NO_CREDENTIAL."""
        result = oe.outreach_adapter_status()
        self.assertTrue(result["capabilities"]["sending_adapter"]["exists"])
        self.assertEqual(result["state"], "NO_CREDENTIAL")

    def test_all_named_states_are_valid(self):
        for state in ("NO_CREDENTIAL", "NOT_CONFIGURED", "READY_FOR_TEST", "READY_FOR_APPROVAL", "LIVE", "BLOCKED"):
            self.assertIn(state, oe.ADAPTER_STATES)


if __name__ == "__main__":
    unittest.main()
