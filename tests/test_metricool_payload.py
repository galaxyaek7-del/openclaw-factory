"""Metricool review-post payloads: built only from the fields Metricool itself
required (2026-10-24 validation errors), refused when anything is missing,
deduplicated, and never auto-publishing while the write gate is closed.
No connector call is made here."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from social_distribution import metricool as mc  # noqa: E402

BRAND = {"brand_id": 6965613, "connected_networks": {"pinterest": "galaxyaek7", "tiktok": "aekgalaxy8"}}
NOW = datetime(2026, 10, 24, 6, 0, tzinfo=timezone.utc)
OFFER = {"offer_id": "B14-001", "title": "13-Week Cash Flow Forecast for Small Business (Excel)",
         "pin_text": "See every week's cash position for the next quarter. $19, one-time purchase.",
         "url": "https://aekraft.gumroad.com/l/dliccs", "price_cents": 1900,
         "cover_url": "https://public-files.gumroad.com/0yng60jkax93wb9qqi54jfvvbwxa",
         "eligibility": {"status": "ELIGIBLE", "reasons": []}}
GOOD = dict(offer=OFFER, board_id="1234567890123456789", when_local="2026-10-27T10:00:00", tz="Europe/Paris",
            reviewers="founder@example.com", brand_record=BRAND, now=NOW)


def build(**kw):
    return mc.build_pinterest_review_post(**dict(GOOD, **kw))


class TestPayload(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "false"})
        p.start()
        self.addCleanup(p.stop)

    def test_valid_payload_has_every_field_metricool_required(self):
        call = build()
        info = json.loads(call["info"])
        self.assertEqual(info["publicationDate"], {"dateTime": "2026-10-27T10:00:00", "timezone": "Europe/Paris"})
        self.assertEqual(set(info["pinterestData"]), {"boardId", "pinTitle", "pinLink"})
        self.assertEqual(call["date"], "2026-10-27T10:00:00+01:00")      # DST ended on 25 October
        self.assertEqual(call["blogId"], "6965613")
        self.assertEqual(call["approvalSystem"], "any")
        self.assertIn("utm_source=pinterest", info["pinterestData"]["pinLink"])

    def test_the_two_recorded_failures_cannot_recur(self):
        info = json.loads(build()["info"])
        self.assertIn("publicationDate", info)                         # failure 1, 2026-10-24
        self.assertTrue(info["pinterestData"]["boardId"])               # failure 2, 2026-10-24

    def test_missing_or_invalid_board_id(self):
        for bad in (None, "", "family-home-cooking", "123", "12345678901234567890123"):
            with self.assertRaises(mc.PostRejected) as c:
                build(board_id=bad)
            self.assertIn("boardId", str(c.exception))

    def test_publication_time_must_be_future_and_local(self):
        with self.assertRaises(mc.PostRejected):
            build(when_local="2026-10-23T10:00:00")
        with self.assertRaises(mc.PostRejected):
            build(when_local="2026-10-27T10:00:00+01:00")              # offset belongs in the zone, not the time
        with self.assertRaises(mc.PostRejected):
            build(tz="Mars/Base")

    def test_wrong_account_identifiers(self):
        with self.assertRaises(mc.PostRejected):
            build(expected_brand_id=1111111)
        with self.assertRaises(mc.PostRejected):
            build(brand_record={"brand_id": 6965613, "connected_networks": {"tiktok": "x"}})
        with self.assertRaises(mc.PostRejected):
            build(brand_record={"brand_id": None, "connected_networks": BRAND["connected_networks"]})
        self.assertEqual(build(expected_brand_id=6965613)["blogId"], "6965613")

    def test_auto_publishing_mode_blocked_while_gate_closed(self):
        with self.assertRaises(mc.PostRejected) as c:
            build(approval_system="optional", allow_auto_approval=True)
        self.assertIn("write gate", str(c.exception))
        with self.assertRaises(mc.PostRejected):
            build(approval_system="optional")                          # gate state irrelevant without the flag
        with mock.patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"}):
            self.assertEqual(build(approval_system="optional", allow_auto_approval=True)["approvalSystem"], "optional")
            with self.assertRaises(mc.PostRejected):
                build(approval_system="optional")

    def test_offer_facts_checked(self):
        with self.assertRaises(mc.PostRejected):
            build(offer=dict(OFFER, pin_text="Only $9 today."))
        with self.assertRaises(mc.PostRejected):
            build(offer=dict(OFFER, cover_url=None))
        with self.assertRaises(mc.PostRejected):
            build(offer=dict(OFFER, eligibility={"status": "NOT_ELIGIBLE", "reasons": ["not live"]}))
        with self.assertRaises(mc.PostRejected):
            build(offer=dict(OFFER, title="x" * 101))


class TestDuplicates(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, ignore_errors=True)
        self.ledger = self.td / "attempts.jsonl"

    def test_metricool_list_and_local_record_both_prevent_duplicates(self):
        call = build()
        self.assertIsNone(mc.duplicate_of(call, [], self.ledger))
        listed = [{"providers": [{"network": "PINTEREST"}], "pinterestData": {"pinLink": "https://aekraft.gumroad.com/l/dliccs?x=1"}}]
        self.assertIn("already has", mc.duplicate_of(call, listed, self.ledger))
        mc.record_attempt(call, created=False, response="Field 'publicationDate' is required", verified_by="list empty",
                          attempts_path=self.ledger)
        self.assertIsNone(mc.duplicate_of(call, [], self.ledger))       # a failed attempt is not a duplicate
        mc.record_attempt(call, created=True, response="ok", post_id="P1", verified_by="getScheduledPosts",
                          attempts_path=self.ledger)
        self.assertIn("P1", mc.duplicate_of(call, [], self.ledger))

    def test_fingerprint_stable_and_specific(self):
        self.assertEqual(mc.fingerprint(build()), mc.fingerprint(build()))
        self.assertNotEqual(mc.fingerprint(build()), mc.fingerprint(build(when_local="2026-10-28T10:00:00")))


if __name__ == "__main__":
    unittest.main()
