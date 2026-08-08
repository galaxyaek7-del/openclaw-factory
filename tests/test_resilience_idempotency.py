"""Resilience & Stress Hardening audit (2026-08-08), Section 4 --
idempotency at repeat counts (2x/10x) the existing test suites had not
explicitly exercised. Reuses every real guard already built across
Phases 33-38b (channels/paddle_webhook.py's event_id replay rejection,
lead_discovery.py's find_duplicate_lead(), commission_ledger.py's
DuplicateCommissionError, outreach_adapter.py's MAX_REAL_SENDS) --
zero new production code, only proof that repeating a request 10
times produces at most ONE real commercial event, never more.
"""

import hashlib
import hmac
import json
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

import channels.paddle_webhook as pw
import commission_ledger as cl
import lead_discovery as ld
import outreach_adapter as oa
import outreach_engine as oe

_FAKE_SECRET = "test_only_fake_secret_never_a_real_paddle_secret"


def _sign(body_bytes, secret, ts=None):
    ts = ts or str(int(time.time()))
    signed_payload = f"{ts}:".encode("utf-8") + body_bytes
    h1 = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"ts={ts};h1={h1}"


def _valid_payload(event_id="evt_1"):
    return json.dumps({
        "event_id": event_id, "event_type": "transaction.completed",
        "data": {"id": "txn_1", "custom_data": {"request_id": "req_1"}, "items": [{"price": {"id": "pri_test1"}}],
                 "details": {"totals": {"grand_total": "10000", "currency_code": "USD"}}},
    }).encode("utf-8")


class TestWebhookIdempotencyAtScale(unittest.TestCase):
    """Uses the real channels/paddle_webhook.py::process_paddle_webhook()
    end-to-end (real HMAC signature, real event_id-keyed dedup ledger) --
    same helper convention as tests/test_paddle_webhook.py, just at a
    10x repeat count that file didn't explicitly test."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.events_path = self.tmp / "events.jsonl"
        self.catalog_path = self.tmp / "catalog.json"
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump([{"title": "Test Product", "product_id": "pro_test1", "price_id": "pri_test1", "price": 100.0}], f)

    def test_same_webhook_delivered_10x_accepted_at_most_once(self):
        body = _valid_payload(event_id="evt_resilience_dup")
        header = _sign(body, _FAKE_SECRET)
        results = [
            pw.process_paddle_webhook(body, header, secret=_FAKE_SECRET,
                                       processed_events_path=self.events_path, catalog_path=self.catalog_path)
            for _ in range(10)
        ]
        accepted = [r for r in results if r["status"] == "ACCEPTED"]
        duplicates = [r for r in results if r.get("reason") == "DUPLICATE_EVENT"]
        self.assertEqual(len(accepted), 1, "exactly one real ACCEPTED outcome across 10 identical deliveries")
        self.assertEqual(len(duplicates), 9, "the remaining 9 identical deliveries must all be rejected as DUPLICATE_EVENT")


class TestLeadDiscoveryIdempotencyAtScale(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.leads_path = self.tmp / "leads.jsonl"
        self.dnc_path = self.tmp / "dnc.jsonl"
        self.events_path = self.tmp / "events.jsonl"
        self.now = datetime(2026, 8, 8, tzinfo=timezone.utc)

    def test_same_discovery_request_executed_10x_persists_at_most_one_real_lead(self):
        hit = {"author": "dev1", "title": "manual workflow automation pain", "url": "https://example.com/p",
               "objectID": "same-id-every-time", "created_at": "2026-08-01T00:00:00.000Z", "story_text": "connecting apps by hand"}
        opportunity = {"opportunity_id": "CO-x", "verification_status": "VERIFIED", "product_or_service": "workflow tool"}
        for _ in range(10):
            ld.discover_lead_for_opportunity(
                opportunity, problem_keywords=["workflow", "manual", "connecting apps"],
                leads_path=self.leads_path, dnc_path=self.dnc_path, events_path=self.events_path,
                hn_query_fn=lambda q, limit=10: ([hit], 1), github_query_fn=lambda q, limit=10: ([], 0),
                now=self.now,
            )
        persisted = ld.load_leads(self.leads_path)
        self.assertEqual(len(persisted), 1, "10 identical real discovery requests must persist exactly one real lead")


class TestCommissionIdempotencyAtScale(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.path = self.tmp / "ledger.jsonl"

    def test_same_real_transaction_retried_10x_records_exactly_once(self):
        successes = 0
        for _ in range(10):
            try:
                cl.record_commission("p", "o", "CONFIRMED", 100.0, "REAL", evidence="real evidence",
                                      external_transaction_id="txn_retry_storm", ledger_path=self.path)
                successes += 1
            except cl.DuplicateCommissionError:
                pass
        self.assertEqual(successes, 1, "a real transaction retried 10x (e.g. after a timeout, before the caller learns the first attempt actually succeeded) must be recorded exactly once")
        self.assertEqual(len(cl.load_ledger(self.path)), 1)


class TestOutreachSendIdempotencyAtScale(unittest.TestCase):
    """Same job (an approved real send) retried after a timeout must
    never send twice -- MAX_REAL_SENDS=1 is the real, code-enforced cap
    (outreach_adapter.py), proven here at a 10x retry-storm scale."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.log_path = self.tmp / "adapter.jsonl"
        self.draft_log = self.tmp / "drafts.jsonl"
        self.now = datetime(2026, 8, 8, tzinfo=timezone.utc)

    def test_same_approved_send_retried_10x_never_exceeds_max_real_sends(self):
        opportunity = {"opportunity_id": "CO-x", "partner_id": "p"}
        lead = {"lead_id": "LEAD-x", "industry": "agency", "problem_signal": "pain"}
        env = {"OUTREACH_SMTP_HOST": "h", "OUTREACH_SMTP_PORT": "587", "OUTREACH_SMTP_USERNAME": "u",
               "OUTREACH_SMTP_PASSWORD": "p", "OUTREACH_FROM_ADDRESS": "noreply@example.com"}

        class NullSMTP:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def ehlo(self):
                pass

            def starttls(self):
                pass

            def login(self, u, p):
                pass

            def sendmail(self, f, t, m):
                pass

        adapter = oa.SMTPOutreachAdapter(smtp_client_factory=lambda: NullSMTP(), env=env)
        draft = oa.prepare_scoped_draft(opportunity, lead, log_path=self.draft_log, now=self.now)
        approved = oe.approve_outreach(draft, approved_by="test-ceo", log_path=self.draft_log, now=self.now)["draft"]

        real_sends_ok = 0
        for _ in range(10):
            result = adapter.send(approved, destination="prospect@example.com", mode="REAL", log_path=self.log_path, now=self.now)
            if result["ok"]:
                real_sends_ok += 1
        self.assertEqual(real_sends_ok, 1, "10 retries of the same approved real send must never exceed MAX_REAL_SENDS=1")


if __name__ == "__main__":
    unittest.main()
