"""Phase 37A, Sections 12-21 — Outreach Adapter Infrastructure tests
(ADR-230). Every test is isolated (tempfile paths); the REAL smtplib
client is always replaced by an injected fake -- zero real network
calls, zero real credentials required."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import outreach_adapter as oa
import outreach_engine as oe

OPPORTUNITY = {"opportunity_id": "CO-n8n-affiliate", "partner_id": "n8n", "program_name": "n8n affiliate",
               "partner_name": "n8n", "customer_problem": "manual workflow automation"}
LEAD = {"lead_id": "LEAD-abc123", "industry": "agency", "problem_signal": "manual workflow pain"}


class FakeSMTP:
    """Context-manager fake -- never touches the network."""
    raise_on = None

    def __init__(self, *a, **kw):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def ehlo(self):
        pass

    def starttls(self):
        pass

    def login(self, user, password):
        if self.raise_on == "auth":
            import smtplib
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    def sendmail(self, from_addr, to_addrs, msg):
        if self.raise_on == "reject":
            import smtplib
            raise smtplib.SMTPRecipientsRefused({to_addrs[0]: (550, b"rejected")})
        if self.raise_on == "timeout":
            raise TimeoutError("connection timed out")
        if self.raise_on == "network":
            raise OSError("network unreachable")


def _fake_factory(raise_on=None):
    def factory():
        client = FakeSMTP()
        client.raise_on = raise_on
        return client
    return factory


class AdapterTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.log_path = self.tmp / "adapter.jsonl"
        self.draft_log = self.tmp / "drafts.jsonl"
        self.now = datetime(2026, 8, 8, tzinfo=timezone.utc)

    def _approved_draft(self, env=None):
        adapter = oa.SMTPOutreachAdapter(env=env or {})
        draft = oa.prepare_scoped_draft(OPPORTUNITY, LEAD, channel="email", log_path=self.draft_log, now=self.now)
        approved = oe.approve_outreach(draft, approved_by="test-ceo", log_path=self.draft_log, now=self.now)
        return adapter, approved["draft"]


class TestMissingCredential(AdapterTestCase):
    def test_real_send_blocked_with_no_credentials_configured(self):
        adapter, draft = self._approved_draft(env={})
        result = adapter.send(draft, destination="prospect@example.com", mode="REAL", log_path=self.log_path, now=self.now)
        self.assertFalse(result["ok"])
        self.assertIn("CREDENTIAL_STATUS=MISSING", result["reason"])


class TestInvalidCredential(AdapterTestCase):
    def test_smtp_auth_error_is_classified_not_crashed(self):
        env = {"OUTREACH_SMTP_HOST": "smtp.example.com", "OUTREACH_SMTP_PORT": "587",
               "OUTREACH_SMTP_USERNAME": "u", "OUTREACH_SMTP_PASSWORD": "p", "OUTREACH_FROM_ADDRESS": "noreply@example.com"}
        adapter = oa.SMTPOutreachAdapter(smtp_client_factory=_fake_factory("auth"), env=env)
        draft = oa.prepare_scoped_draft(OPPORTUNITY, LEAD, log_path=self.draft_log, now=self.now)
        approved = oe.approve_outreach(draft, approved_by="test-ceo", log_path=self.draft_log, now=self.now)["draft"]
        result = adapter.send(approved, destination="prospect@example.com", mode="REAL", log_path=self.log_path, now=self.now)
        self.assertFalse(result["ok"])
        self.assertEqual(result["failure_class"], "INVALID_OR_EXPIRED_CREDENTIAL")


class TestInvalidDestination(AdapterTestCase):
    def test_malformed_email_is_blocked_before_any_send_attempt(self):
        adapter, draft = self._approved_draft()
        result = adapter.send(draft, destination="not-an-email", mode="DRY_RUN", log_path=self.log_path, now=self.now)
        self.assertFalse(result["ok"])
        self.assertIn("not a real, well-formed email", result["reason"])


class TestProviderTimeout(AdapterTestCase):
    def test_timeout_is_classified_as_provider_timeout(self):
        env = {"OUTREACH_SMTP_HOST": "h", "OUTREACH_SMTP_PORT": "587", "OUTREACH_SMTP_USERNAME": "u",
               "OUTREACH_SMTP_PASSWORD": "p", "OUTREACH_FROM_ADDRESS": "noreply@example.com"}
        adapter = oa.SMTPOutreachAdapter(smtp_client_factory=_fake_factory("timeout"), env=env)
        draft = oa.prepare_scoped_draft(OPPORTUNITY, LEAD, log_path=self.draft_log, now=self.now)
        approved = oe.approve_outreach(draft, approved_by="test-ceo", log_path=self.draft_log, now=self.now)["draft"]
        result = adapter.send(approved, destination="prospect@example.com", mode="REAL", log_path=self.log_path, now=self.now)
        self.assertFalse(result["ok"])
        self.assertEqual(result["failure_class"], "PROVIDER_TIMEOUT")


class TestProviderRejection(AdapterTestCase):
    def test_recipient_refused_is_classified_as_invalid_destination(self):
        """SMTPRecipientsRefused means the provider itself rejected the
        specific destination address -- classified as INVALID_DESTINATION
        (a real, more specific failure_class than the generic PROVIDER_
        REJECTION, which this module reserves for SMTPDataError)."""
        env = {"OUTREACH_SMTP_HOST": "h", "OUTREACH_SMTP_PORT": "587", "OUTREACH_SMTP_USERNAME": "u",
               "OUTREACH_SMTP_PASSWORD": "p", "OUTREACH_FROM_ADDRESS": "noreply@example.com"}
        adapter = oa.SMTPOutreachAdapter(smtp_client_factory=_fake_factory("reject"), env=env)
        draft = oa.prepare_scoped_draft(OPPORTUNITY, LEAD, log_path=self.draft_log, now=self.now)
        approved = oe.approve_outreach(draft, approved_by="test-ceo", log_path=self.draft_log, now=self.now)["draft"]
        result = adapter.send(approved, destination="prospect@example.com", mode="REAL", log_path=self.log_path, now=self.now)
        self.assertFalse(result["ok"])
        self.assertEqual(result["failure_class"], "INVALID_DESTINATION")


class TestNetworkFailure(AdapterTestCase):
    def test_oserror_is_classified_as_network_failure(self):
        env = {"OUTREACH_SMTP_HOST": "h", "OUTREACH_SMTP_PORT": "587", "OUTREACH_SMTP_USERNAME": "u",
               "OUTREACH_SMTP_PASSWORD": "p", "OUTREACH_FROM_ADDRESS": "noreply@example.com"}
        adapter = oa.SMTPOutreachAdapter(smtp_client_factory=_fake_factory("network"), env=env)
        draft = oa.prepare_scoped_draft(OPPORTUNITY, LEAD, log_path=self.draft_log, now=self.now)
        approved = oe.approve_outreach(draft, approved_by="test-ceo", log_path=self.draft_log, now=self.now)["draft"]
        result = adapter.send(approved, destination="prospect@example.com", mode="REAL", log_path=self.log_path, now=self.now)
        self.assertFalse(result["ok"])
        self.assertEqual(result["failure_class"], "NETWORK_FAILURE")


class TestBlockedLeadNotApproved(AdapterTestCase):
    def test_draft_state_not_approved_blocks_send(self):
        adapter = oa.SMTPOutreachAdapter(env={})
        draft = oa.prepare_scoped_draft(OPPORTUNITY, LEAD, log_path=self.draft_log, now=self.now)
        result = adapter.send(draft, destination="prospect@example.com", mode="DRY_RUN", log_path=self.log_path, now=self.now)
        self.assertFalse(result["ok"])
        self.assertEqual(result["delivery_status"], "BLOCKED")


class TestCeoApprovalMissingOrWrongScope(AdapterTestCase):
    def test_missing_approval_scope_fields_refused(self):
        _, draft = self._approved_draft()
        result = oa.verify_exact_scope_approval(draft, approval={}, opportunity=OPPORTUNITY)
        self.assertFalse(result["ok"])
        self.assertIn("missing required scope fields", result["reason"])

    def test_wrong_scope_lead_id_refused(self):
        _, draft = self._approved_draft()
        approval = {
            "approved_lead_id": "LEAD-someone-else", "approved_opportunity_id": draft["opportunity_id"],
            "approved_partner_id": OPPORTUNITY["partner_id"], "approved_channel": draft["channel"],
            "approved_message_hash": draft["message_hash"], "approval_timestamp": "2026-08-08T00:00:00Z",
            "approval_scope": "REF-1",
        }
        result = oa.verify_exact_scope_approval(draft, approval, opportunity=OPPORTUNITY)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "APPROVAL_SCOPE_MISMATCH")
        self.assertIn("approved_lead_id does not match this draft's lead_id", result["mismatches"])


class TestMessageChangedAfterApproval(AdapterTestCase):
    def test_message_hash_mismatch_after_approval_is_caught(self):
        _, draft = self._approved_draft()
        good_approval = {
            "approved_lead_id": draft["lead_id"], "approved_opportunity_id": draft["opportunity_id"],
            "approved_partner_id": OPPORTUNITY["partner_id"], "approved_channel": draft["channel"],
            "approved_message_hash": draft["message_hash"], "approval_timestamp": "2026-08-08T00:00:00Z",
            "approval_scope": "REF-1",
        }
        # message changes after approval was granted
        draft["message_hash"] = "different-hash-because-message-changed"
        result = oa.verify_exact_scope_approval(draft, good_approval, opportunity=OPPORTUNITY)
        self.assertFalse(result["ok"])
        self.assertTrue(any("approved_message_hash does not match" in m for m in result["mismatches"]))

    def test_exact_scope_approval_with_real_ceo_gate_allows(self):
        _, draft = self._approved_draft()
        approval = {
            "approved_lead_id": draft["lead_id"], "approved_opportunity_id": draft["opportunity_id"],
            "approved_partner_id": OPPORTUNITY["partner_id"], "approved_channel": draft["channel"],
            "approved_message_hash": draft["message_hash"], "approval_timestamp": "2026-08-08T00:00:00Z",
            "approval_scope": "REF-1",
        }
        result = oa.verify_exact_scope_approval(draft, approval, opportunity=OPPORTUNITY)
        self.assertTrue(result["ok"])


class TestDuplicateMessage(AdapterTestCase):
    def test_same_draft_hashed_twice_produces_identical_message_hash(self):
        _, draft1 = self._approved_draft()
        _, draft2 = self._approved_draft()
        # Different draft_ids (timestamped) but identical message_text -> identical hash
        self.assertEqual(draft1["message_hash"], draft2["message_hash"])


class TestMaxRealSends(AdapterTestCase):
    def test_max_real_sends_enforced_after_one_recorded_real_send(self):
        env = {"OUTREACH_SMTP_HOST": "h", "OUTREACH_SMTP_PORT": "587", "OUTREACH_SMTP_USERNAME": "u",
               "OUTREACH_SMTP_PASSWORD": "p", "OUTREACH_FROM_ADDRESS": "noreply@example.com"}
        adapter = oa.SMTPOutreachAdapter(smtp_client_factory=_fake_factory(None), env=env)
        draft = oa.prepare_scoped_draft(OPPORTUNITY, LEAD, log_path=self.draft_log, now=self.now)
        approved = oe.approve_outreach(draft, approved_by="test-ceo", log_path=self.draft_log, now=self.now)["draft"]

        first = adapter.send(approved, destination="prospect@example.com", mode="REAL", log_path=self.log_path, now=self.now)
        self.assertTrue(first["ok"])
        self.assertEqual(oa.count_real_sends(self.log_path), 1)

        second = adapter.send(approved, destination="prospect2@example.com", mode="REAL", log_path=self.log_path, now=self.now)
        self.assertFalse(second["ok"])
        self.assertIn("MAX_REAL_SENDS=1 already reached", second["reason"])

    def test_simulation_sends_never_count_toward_max_real_sends(self):
        adapter, draft = self._approved_draft()
        for _ in range(3):
            adapter.send(draft, destination="prospect@example.com", mode="SIMULATION", log_path=self.log_path, now=self.now)
        self.assertEqual(oa.count_real_sends(self.log_path), 0)


class TestBounceReplyUnsubscribe(AdapterTestCase):
    def test_bounce_reply_unsubscribe_are_recorded(self):
        adapter, draft = self._approved_draft()
        send_result = adapter.send(draft, destination="prospect@example.com", mode="SIMULATION", log_path=self.log_path, now=self.now)
        oid = send_result["outreach_id"]

        adapter.handle_bounce(oid, bounce_info="mailbox full", log_path=self.log_path, now=self.now)
        adapter.handle_reply(oid, reply_info="interested", log_path=self.log_path, now=self.now)
        dnc_path = self.tmp / "dnc.jsonl"
        adapter.handle_unsubscribe(oid, contact_channel="https://github.com/someone", log_path=self.log_path, dnc_path=dnc_path, now=self.now)

        status = adapter.get_delivery_status(oid, log_path=self.log_path)
        events = [e.get("event") for e in status["events"]]
        self.assertIn("BOUNCE_RECEIVED", events)
        self.assertIn("REPLY_RECEIVED", events)
        self.assertIn("UNSUBSCRIBE_RECEIVED", events)

        import lead_discovery as ld
        dnc_entries = ld._read_jsonl(dnc_path)
        self.assertEqual(len(dnc_entries), 1)
        self.assertEqual(dnc_entries[0]["contact_channel"], "https://github.com/someone")


class TestDryRunEngine(AdapterTestCase):
    def test_full_dry_run_never_touches_real_counters(self):
        result = oa.run_full_dry_run(OPPORTUNITY, LEAD, log_path=self.log_path, draft_log_path=self.draft_log,
                                      dnc_path=self.tmp / "dnc.jsonl", now=self.now)
        self.assertEqual(result["REAL_OUTREACH"], 0)
        self.assertEqual(result["REAL_CUSTOMERS"], 0)
        self.assertEqual(result["REAL_DEALS"], 0)
        self.assertEqual(result["REAL_REVENUE"], 0)
        self.assertEqual(result["REAL_COMMISSION"], 0)
        self.assertEqual(result["REAL_PAYOUT"], 0)
        self.assertEqual(len(result["steps"]), 8)
        self.assertTrue(all(step.get("ok") is not False or step["step"] == "failure_case_unapproved_send" for step in result["steps"]))

    def test_dry_run_never_imports_a_real_credential_success(self):
        result = oa.run_full_dry_run(OPPORTUNITY, LEAD, log_path=self.log_path, draft_log_path=self.draft_log,
                                      dnc_path=self.tmp / "dnc.jsonl", now=self.now)
        self.assertEqual(oa.count_real_sends(self.log_path), 0)


class TestCredentialSecurity(AdapterTestCase):
    def test_credential_values_never_appear_in_validate_credentials_output(self):
        env = {"OUTREACH_SMTP_HOST": "h", "OUTREACH_SMTP_PORT": "587", "OUTREACH_SMTP_USERNAME": "secret-user",
               "OUTREACH_SMTP_PASSWORD": "super-secret-password", "OUTREACH_FROM_ADDRESS": "noreply@example.com"}
        adapter = oa.SMTPOutreachAdapter(env=env)
        result = adapter.validate_credentials()
        as_text = str(result)
        self.assertNotIn("secret-user", as_text)
        self.assertNotIn("super-secret-password", as_text)
        self.assertTrue(result["CREDENTIAL_PRESENT"])


class TestAdapterStatus(AdapterTestCase):
    def test_never_claims_real_send_capability_without_credentials(self):
        status = oa.adapter_status(adapter=oa.SMTPOutreachAdapter(env={}), log_path=self.log_path)
        self.assertFalse(status["concrete_adapter"]["real_send_capability"])
        self.assertEqual(status["concrete_adapter"]["credential_status"], "MISSING")


class TestAgentBoundaries(unittest.TestCase):
    def test_channel_documentation_names_zero_automatic_retries(self):
        self.assertIn("Zero automatic retries", oa.CHANNEL_DOCUMENTATION["RETRY_POLICY"])


if __name__ == "__main__":
    unittest.main()
