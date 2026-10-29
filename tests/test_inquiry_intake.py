"""inquiry_intake.py: schema, validation, spam handling, duplicates, review
queue and privacy. Temp ledgers only; the real one is never touched."""
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

    def tearDown(self):
        self.dir.cleanup()

    def test_store_review_and_queue(self):
        a = ii.submit(good(), self.ledger, NOW)
        ii.submit(good(email="b@example.com", arm="research_data_services"), self.ledger, NOW)
        self.assertTrue(a["stored"])
        q = ii.queue(self.ledger)
        self.assertEqual((q["total"], q["pending"]), (2, 2))
        ii.review(a["inquiry_id"], "QUALIFIED", "in scope", self.ledger, NOW)
        q = ii.queue(self.ledger)
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
            ii.review(a["inquiry_id"], "MAYBE", ledger=self.ledger)
        with self.assertRaises(KeyError):
            ii.review("INQ-000000000000", "REPLIED", ledger=self.ledger)


class Privacy(unittest.TestCase):
    def test_the_inquiry_ledger_is_git_ignored(self):
        r = subprocess.run(["git", "check-ignore", "-q", "data/inquiries.jsonl"], cwd=ROOT)
        self.assertEqual(r.returncode, 0, "data/inquiries.jsonl holds personal data and must stay out of the public repo")

    def test_readiness_does_not_claim_a_public_channel(self):
        r = ii.readiness()
        self.assertTrue(r["public_receiver"].startswith("NOT CONNECTED"))


if __name__ == "__main__":
    unittest.main()
