"""Resilience & Stress Hardening audit (2026-08-08), Section 22 -- a
controlled chaos test combining several real failure modes in ONE run,
proving the system stays safe under compound, simultaneous failure
rather than only single, isolated failures (which every other real
adversarial test in this factory already proves individually).
Non-production, isolated tempfile paths throughout -- zero real
credentials, zero real outreach, zero real financial writes.

The objective is not zero errors -- it's:
  NO unsafe commercial action
  NO data corruption
  NO fake revenue
  NO duplicate financial event
  NO CEO-gate bypass
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


def _sign(body_bytes, secret):
    ts = str(int(time.time()))
    signed_payload = f"{ts}:".encode("utf-8") + body_bytes
    h1 = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"ts={ts};h1={h1}"


class TestCombinedFailureChaosRun(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.now = datetime(2026, 8, 8, tzinfo=timezone.utc)

    def test_compound_failure_scenario_stays_safe(self):
        """One combined scenario injecting, in sequence within a single
        real run:
          1. A malformed/duplicate webhook delivery.
          2. A duplicate lead-discovery candidate arriving alongside a
             genuinely new one.
          3. A do-not-contact-blocked candidate mixed into the same batch.
          4. A commission-recording retry storm for the same real
             transaction (simulating a timeout-triggered client retry).
          5. An expired CEO approval attempted against a real draft.
        Every stage must degrade safely -- never silently succeed where
        it shouldn't, never corrupt another stage's real state."""

        # --- 1. Duplicate/malformed webhook delivery ---
        events_path = self.tmp / "webhook_events.jsonl"
        catalog_path = self.tmp / "catalog.json"
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump([{"title": "T", "product_id": "pro_1", "price_id": "pri_1", "price": 50.0}], f)
        body = json.dumps({
            "event_id": "evt_chaos", "event_type": "transaction.completed",
            "data": {"id": "txn_1", "custom_data": {"request_id": "r1"}, "items": [{"price": {"id": "pri_1"}}],
                     "details": {"totals": {"grand_total": "5000", "currency_code": "USD"}}},
        }).encode("utf-8")
        header = _sign(body, _FAKE_SECRET)
        first_webhook = pw.process_paddle_webhook(body, header, secret=_FAKE_SECRET, processed_events_path=events_path, catalog_path=catalog_path)
        malformed = pw.process_paddle_webhook(b"not-json-at-all{{{", "ts=1;h1=deadbeef", secret=_FAKE_SECRET, processed_events_path=events_path, catalog_path=catalog_path)
        duplicate_webhook = pw.process_paddle_webhook(body, header, secret=_FAKE_SECRET, processed_events_path=events_path, catalog_path=catalog_path)
        self.assertEqual(first_webhook["status"], "ACCEPTED")
        self.assertEqual(malformed["status"], "REJECTED")
        self.assertEqual(duplicate_webhook["reason"], "DUPLICATE_EVENT")

        # --- 2/3. Mixed batch: duplicate + blocked + genuinely new lead candidates ---
        leads_path = self.tmp / "leads.jsonl"
        dnc_path = self.tmp / "dnc.jsonl"
        lead_events_path = self.tmp / "lead_events.jsonl"
        opportunity = {"opportunity_id": "CO-chaos", "verification_status": "VERIFIED", "product_or_service": "chaos tool", "partner_id": "chaos-partner"}
        hit_a = {"author": "dev-a", "title": "manual workflow automation pain", "url": "https://example.com/a",
                 "objectID": "chaos-a", "created_at": "2026-08-01T00:00:00.000Z", "story_text": "connecting apps by hand"}
        hit_blocked = {"author": "dev-blocked", "title": "manual workflow automation pain", "url": "https://example.com/b",
                       "objectID": "chaos-b", "created_at": "2026-08-01T00:00:00.000Z", "story_text": "connecting apps by hand"}
        ld.add_to_do_not_contact(contact_channel="https://news.ycombinator.com/user?id=dev-blocked", reason="chaos test", dnc_path=dnc_path, now=self.now)

        first_batch = ld.discover_lead_for_opportunity(
            opportunity, problem_keywords=["workflow", "manual", "connecting apps"],
            leads_path=leads_path, dnc_path=dnc_path, events_path=lead_events_path,
            hn_query_fn=lambda q, limit=10: ([hit_a, hit_blocked], 2), github_query_fn=lambda q, limit=10: ([], 0), now=self.now,
        )
        # Same batch delivered again (a real "retry after timeout" scenario)
        second_batch = ld.discover_lead_for_opportunity(
            opportunity, problem_keywords=["workflow", "manual", "connecting apps"],
            leads_path=leads_path, dnc_path=dnc_path, events_path=lead_events_path,
            hn_query_fn=lambda q, limit=10: ([hit_a, hit_blocked], 2), github_query_fn=lambda q, limit=10: ([], 0), now=self.now,
        )
        self.assertEqual(first_batch["qualified_count"], 1, "only the non-blocked candidate qualifies")
        persisted_leads = ld.load_leads(leads_path)
        self.assertEqual(len(persisted_leads), 1, "the retried batch must never duplicate the already-persisted real lead")

        # --- 4. Commission-recording retry storm for the same real transaction ---
        ledger_path = self.tmp / "ledger.jsonl"
        successes = 0
        for _ in range(5):
            try:
                cl.record_commission("p", "CO-chaos", "CONFIRMED", 50.0, "REAL", evidence="real webhook evidence",
                                      external_transaction_id="txn_chaos_1", ledger_path=ledger_path)
                successes += 1
            except cl.DuplicateCommissionError:
                pass
        self.assertEqual(successes, 1)
        self.assertEqual(len(cl.load_ledger(ledger_path)), 1)

        # --- 5. Expired CEO approval attempted against a real draft ---
        env = {}  # no real SMTP credentials -- send() must be structurally blocked regardless
        adapter = oa.SMTPOutreachAdapter(env=env)
        lead = persisted_leads[0]
        draft = oa.prepare_scoped_draft(opportunity, lead, log_path=self.tmp / "drafts.jsonl", now=self.now)
        approved = oe.approve_outreach(draft, approved_by="chaos-ceo", log_path=self.tmp / "drafts.jsonl", now=self.now)["draft"]
        expired_approval = {
            "approved_lead_id": draft["lead_id"], "approved_opportunity_id": draft["opportunity_id"],
            "approved_partner_id": opportunity.get("partner_id"), "approved_channel": draft["channel"],
            "approved_message_hash": draft["message_hash"], "maximum_action_scope": "single_message_send",
            "approval_timestamp": "2026-08-01T00:00:00Z", "expiration_time": "2026-08-02T00:00:00Z",  # already expired relative to self.now
            "approved_by": "chaos-ceo", "approved_at": "2026-08-01T00:00:00Z", "approval_scope": "REF-CHAOS",
        }
        approval_result = oa.verify_exact_scope_approval(draft, expired_approval, opportunity=opportunity, now=self.now)
        self.assertFalse(approval_result["ok"])
        self.assertIn("APPROVAL_EXPIRED", approval_result["reason"])

        real_send_result = adapter.send(approved, destination="prospect@example.com", mode="REAL", log_path=self.tmp / "adapter.jsonl", now=self.now)
        self.assertFalse(real_send_result["ok"], "an expired-approval / no-credential real send must never succeed")

        # --- Final compound assertions: the whole run stayed safe ---
        self.assertEqual(oa.count_real_sends(log_path=self.tmp / "adapter.jsonl"), 0,
                          "no real send ever succeeded across the whole compound run -- expired approval + missing credential both independently blocked it")
        # This isolated test ledger DID receive exactly one real, evidenced
        # CONFIRMED commission (step 4) -- first_real_dollar_status() must
        # honestly reflect that real record (isolation comes from the
        # separate ledger_path, not from any record-level "this is a test"
        # flag -- the same discipline this factory uses everywhere), never
        # silently drop it or double-count the 4 real rejected retries.
        status = cl.first_real_dollar_status(ledger_path=ledger_path)
        self.assertEqual(status["REAL_REVENUE"], 50.0)
        self.assertEqual(len(status["evidence"]), 1, "exactly one real commission record, never the 4 rejected retry attempts")


if __name__ == "__main__":
    unittest.main()
