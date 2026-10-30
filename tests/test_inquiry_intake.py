"""inquiry_intake.py: schema, validation, spam handling, duplicates, review
queue and privacy. Temp ledgers only; the real one is never touched."""
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import inquiry_intake as ii  # noqa: E402

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)


def good(**over):
    p = {"name": "Sam", "email": "Sam@Example.com", "message": "I have a 3,000-row inventory export to clean.",
         "arm": "micro_b2b", "offer_id": "catalogue-cleanup", "source_page": "catalogue-cleanup.html",
         "consent_to_reply": True, "form_started_at": (NOW - timedelta(seconds=40)).isoformat()}
    p.update(over)
    return p


class Validation(unittest.TestCase):
    def test_a_good_inquiry_is_normalised(self):
        r = ii.validate(good(), NOW)
        self.assertEqual(r["status"], "NEW")
        self.assertEqual(r["email"], "sam@example.com")
        self.assertTrue(r["inquiry_id"].startswith("INQ-"))

    def test_missing_and_invalid_fields_are_all_reported(self):
        with self.assertRaises(ii.InvalidInquiry) as cm:
            ii.validate({"email": "not-an-address", "arm": "lottery"}, NOW)
        errs = " | ".join(cm.exception.errors)
        for part in ("name is required", "message is required", "email is not a valid address",
                     "arm is not a known business arm", "consent_to_reply"):
            self.assertIn(part, errs)

    def test_oversized_fields_are_refused(self):
        with self.assertRaises(ii.InvalidInquiry):
            ii.validate(good(message="x" * 5000), NOW)

    def test_markup_in_the_email_is_refused(self):
        with self.assertRaises(ii.InvalidInquiry):
            ii.validate(good(email="<script>@x.io"), NOW)

    def test_spam_signals_keep_the_record_but_mark_it(self):
        r = ii.validate(good(website="http://spam.example"), NOW)
        self.assertEqual(r["status"], "SPAM_SUSPECTED")
        r = ii.validate(good(message="http://a http://b http://c buy"), NOW)
        self.assertIn("more than 2 links", r["spam_signals"])
        r = ii.validate(good(form_started_at=(NOW - timedelta(seconds=1)).isoformat()), NOW)
        self.assertIn("submitted in under 3 seconds", r["spam_signals"])

    def test_no_ip_or_user_agent_is_stored(self):
        r = ii.validate(good(ip="1.2.3.4", user_agent="x"), NOW)
        self.assertNotIn("ip", r)
        self.assertNotIn("user_agent", r)


class Queue(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ledger = Path(self.dir.name) / "inquiries.jsonl"
        self.interest = Path(self.dir.name) / "customer_interest.jsonl"

    def tearDown(self):
        self.dir.cleanup()

    def test_store_review_and_queue(self):
        a = ii.submit(good(), self.ledger, NOW)
        ii.submit(good(email="b@example.com", arm="research_data_services"), self.ledger, NOW)
        self.assertTrue(a["stored"])
        q = ii.queue(self.ledger, self.interest)
        self.assertEqual((q["total"], q["pending"]), (2, 2))
        ii.review(a["inquiry_id"], "QUALIFIED", "in scope", self.ledger, NOW, self.interest)
        q = ii.queue(self.ledger, self.interest)
        self.assertEqual(q["pending"], 1)
        self.assertEqual(q["by_arm"]["micro_b2b"]["qualified"], 1)
        self.assertNotIn("email", str(q["pending_items"]))

    def test_a_repeat_within_24_hours_is_not_stored_twice(self):
        first = ii.submit(good(), self.ledger, NOW)
        again = ii.submit(good(), self.ledger, NOW + timedelta(hours=2))
        self.assertEqual(again, {"stored": False, "duplicate_of": first["inquiry_id"]})
        later = ii.submit(good(), self.ledger, NOW + timedelta(hours=30))
        self.assertTrue(later["stored"])

    def test_review_needs_a_known_inquiry_and_outcome(self):
        a = ii.submit(good(), self.ledger, NOW)
        with self.assertRaises(ValueError):
            ii.review(a["inquiry_id"], "MAYBE", ledger=self.ledger, interest_ledger=self.interest)
        with self.assertRaises(KeyError):
            ii.review("INQ-000000000000", "REPLIED", ledger=self.ledger, interest_ledger=self.interest)

    def test_an_emailed_inquiry_is_recorded_with_its_own_time(self):
        out = ii.record_email("micro_b2b", "Owner@Shop.example", "Can you check my Merchant Center feed?",
                              offer_id="feed-preflight", received_at="2026-10-30T09:15:00Z", ledger=self.ledger)
        self.assertTrue(out["stored"])
        self.assertNotIn("received_at_note", out)
        rows = [json.loads(l) for l in self.ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[0]["channel"], "email")
        self.assertEqual(rows[0]["received_at"], "2026-10-30T09:15:00+00:00")
        self.assertEqual(rows[0]["email"], "owner@shop.example")
        q = ii.queue(self.ledger, self.interest)
        self.assertEqual(q["by_arm"]["micro_b2b"]["pending"], 1)
        self.assertNotIn("owner@shop.example", json.dumps(q))
        late = ii.record_email("micro_b2b", "b@shop.example", "Second question about feeds", ledger=self.ledger)
        self.assertIn("UNKNOWN", late["received_at_note"])
        with self.assertRaises(ii.InvalidInquiry):
            ii.record_email("lottery", "c@shop.example", "x", ledger=self.ledger)

    def test_the_command_line_records_and_lists_without_addresses(self):
        import contextlib, io
        orig = ii.LEDGER, ii.INTEREST_LEDGER
        ii.LEDGER, ii.INTEREST_LEDGER = self.ledger, self.interest
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = ii.main(["record-email", "--arm", "research_data_services", "--email", "adv@firm.example",
                              "--message", "Do you cover Italy in the EAA register?", "--offer", "eaa-penalties",
                              "--received-at", "2026-10-30T10:00:00+00:00"])
            self.assertEqual(rc, 0)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ii.main(["queue"])
            self.assertIn("research_data_services", buf.getvalue())
            self.assertNotIn("adv@firm.example", buf.getvalue())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ii.main(["record-email", "--arm", "micro_b2b", "--email", "bad",
                                          "--message", "hello there"]), 1)
        finally:
            ii.LEDGER, ii.INTEREST_LEDGER = orig

    def test_site_form_signals_join_the_queue_without_copying_them(self):
        import json
        sig = {"signal_id": "int_0123456789abcdef", "received_at": "2026-10-29T10:00:00+00:00",
               "classification": "CUSTOMER", "email": "buyer@example.org", "message": "Do you clean Shopify exports?",
               "product_interest": "catalogue-cleanup", "dedup_hash": "x"}
        self.interest.write_text(json.dumps(sig) + "\n" + json.dumps({"reason": "duplicate"}) + "\n", encoding="utf-8")
        q = ii.queue(self.ledger, self.interest)
        self.assertEqual((q["total"], q["pending"]), (1, 1))
        self.assertEqual(q["by_arm"]["unassigned"]["pending"], 1)
        self.assertNotIn("buyer@example.org", json.dumps(q))
        ii.review("int_0123456789abcdef", "REPLIED", ledger=self.ledger, now=NOW, interest_ledger=self.interest)
        self.assertEqual(ii.queue(self.ledger, self.interest)["pending"], 0)
        # the interest ledger itself is never written by this module
        self.assertEqual(self.interest.read_text(encoding="utf-8").count("\n"), 2)
        self.assertNotIn("buyer@example.org", self.ledger.read_text(encoding="utf-8"))


class Privacy(unittest.TestCase):
    def test_the_inquiry_ledger_is_git_ignored(self):
        r = subprocess.run(["git", "check-ignore", "-q", "data/inquiries.jsonl"], cwd=ROOT)
        self.assertEqual(r.returncode, 0, "data/inquiries.jsonl holds personal data and must stay out of the public repo")

    def test_the_site_form_ledgers_are_git_ignored_and_untracked(self):
        for f in ("data/customer_interest.jsonl", "data/customer_interest_rejected.jsonl"):
            r = subprocess.run(["git", "check-ignore", "-q", "--no-index", f], cwd=ROOT)
            self.assertEqual(r.returncode, 0, f + " holds e-mail addresses and must stay out of the public repo")
            tracked = subprocess.run(["git", "ls-files", "--error-unmatch", f], cwd=ROOT, capture_output=True)
            self.assertNotEqual(tracked.returncode, 0, f + " is still tracked")

    def test_readiness_does_not_claim_a_public_channel(self):
        r = ii.readiness()
        self.assertTrue(r["public_receiver"].startswith("NOT CONNECTED"))


if __name__ == "__main__":
    unittest.main()
