"""Pinterest board detection (exact JSON objects only), pin text, pin images and
the queue's statuses. Fixtures only; no network, no Metricool call."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from social_distribution import metricool, pinterest_boards as pb  # noqa: E402
import pinterest_queue as pq  # noqa: E402

BOARD_ID = "1106619008379399999"
HTML = ('<script>{"a":{"id":"9999999999999999999","url":"/u1/finance/"},'           # decoy: not a board object
        '"b":{"type":"board","id":"1106619008379372704","name":"Islamic Quotes","privacy":"public","url":"/u1/islamic-quotes/"},'
        '"c":{"type":"board","id":"' + BOARD_ID + '","name":"Small  Business Finance Tools","privacy":"public",'
        '"url":"/u1/small-business-finance-tools/","owner":{"id":"1106619077096899018"}},'
        '"d":{"type":"board","id":"1106619008379300001","name":"Secret","privacy":"secret","url":"/u1/secret/"},'
        '"e":{"type":"board","id":"1106619008379300002","name":"Dup","privacy":"public","url":"/u1/dup/"},'
        '"f":{"type":"board","id":"1106619008379300003","name":"Dup","privacy":"public","url":"/u1/dup/"}}</script>')
BRAND = {"brand_id": 6965613, "connected_networks": {"pinterest": "u1"}}
NOW = datetime(2026, 10, 24, 6, 0, tzinfo=timezone.utc)
DESC = ("See every week's cash position for the next quarter, spot the tight weeks before they happen, "
        "and track forecast against actual. Monthly reports hide timing.\nWhat's included")


def offers_doc():
    return {"offers": [{"offer_id": "B14-001", "type": "digital_product", "title": "13-Week Cash Flow Forecast for Small Business",
                        "description": DESC, "problem": DESC.split(".")[0] + ".", "url": "https://aekraft.gumroad.com/l/dliccs",
                        "price_cents": 1900, "cover_url": "https://img.example/c.png", "eligibility": {"status": "ELIGIBLE", "reasons": []}},
                       {"offer_id": "B14-002", "type": "digital_product", "title": "Rental Property Deal Analyzer",
                        "description": "Compare rental deals side by side.", "problem": "Compare rental deals side by side.",
                        "url": "https://aekraft.gumroad.com/l/mfpqin", "price_cents": 2400, "cover_url": "https://img.example/d.png",
                        "eligibility": {"status": "ELIGIBLE", "reasons": []}}]}


PINS = {"pins": {k: {"public_url": f"https://site.example/pins/{k.lower()}.jpg"} for k in ("B14-002", "B14-001")}}


class TestBoards(unittest.TestCase):
    def test_only_real_board_objects_and_exact_ids(self):
        boards = pb.parse_boards(HTML, "u1")
        self.assertEqual(boards["small-business-finance-tools"]["id"], BOARD_ID)    # not the owner's id beside it
        self.assertNotIn("finance", boards)                                            # decoy object, no type board
        self.assertNotIn("dup", boards)                                                # conflicting ids dropped

    def test_find_board_by_name_public_only(self):
        boards = pb.parse_boards(HTML, "u1")
        self.assertEqual(pb.find_board(boards)["id"], BOARD_ID)                       # spacing/case insensitive
        self.assertIsNone(pb.find_board(boards, "Secret"))                            # not public
        self.assertIsNone(pb.find_board(pb.parse_boards("<html></html>", "u1")))


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, ignore_errors=True)
        p = mock.patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "false"})
        p.start()
        self.addCleanup(p.stop)

    def run_q(self, **kw):
        args = dict(start=date(2026, 10, 27), offers_doc=offers_doc(), pins_doc=PINS, brand_record=BRAND,
                    attempts_path=self.td / "a.jsonl", now=NOW, image_ok=lambda u: True, html=HTML)
        args.update(kw)
        return pq.run(**args)

    def test_pin_text_is_listing_text_plus_real_price(self):
        t = pq.pin_text(offers_doc()["offers"][0])
        self.assertTrue(t.startswith("See every week's cash position"))
        self.assertTrue(t.endswith("$19, one-time purchase."))
        self.assertNotIn("What's included", t)
        self.assertLessEqual(len(t), 500)

    def test_ready_items_one_per_day_b14_001_first(self):
        q = self.run_q()
        self.assertEqual([i["offer_id"] for i in q["items"]], ["B14-001", "B14-002"])
        self.assertEqual([i["status"] for i in q["items"]], ["READY", "READY"])
        self.assertEqual(q["items"][0]["call"]["date"], "2026-10-27T10:00:00+01:00")
        self.assertEqual(q["items"][1]["when_local"], "2026-10-28T10:00:00")
        info = json.loads(q["items"][0]["call"]["info"])
        self.assertEqual(info["pinterestData"]["boardId"], BOARD_ID)
        self.assertEqual(info["media"], ["https://site.example/pins/b14-001.jpg"])
        self.assertEqual(q["items"][0]["call"]["approvalSystem"], "any")

    def test_no_board_blocks_everything(self):
        q = self.run_q(html='<script>{"b":{"type":"board","id":"1106619008379372704","name":"Plats","privacy":"public","url":"/u1/plats/"}}</script>')
        self.assertEqual(q["summary"], {"BLOCKED_NO_BOARD": 2})
        self.assertNotIn("call", q["items"][0])

    def test_unreachable_image_blocks(self):
        q = self.run_q(image_ok=lambda u: False)
        self.assertEqual(q["summary"], {"BLOCKED_IMAGE_NOT_PUBLIC": 2})

    def test_already_created_is_not_queued_again(self):
        q = self.run_q()
        metricool.record_attempt(q["items"][0]["call"], created=True, response="ok", post_id="P9",
                                 verified_by="getScheduledPosts", attempts_path=self.td / "a.jsonl")
        q2 = self.run_q()
        self.assertEqual(q2["items"][0]["status"], "ALREADY_CREATED")
        self.assertEqual(q2["items"][1]["status"], "READY")

    def test_network_failure_is_unknown_not_a_board(self):
        with mock.patch.object(pq, "fetch_profile", side_effect=ConnectionError("timeout")):
            q = self.run_q(html=None)
        self.assertTrue(q["board_lookup"].startswith("UNKNOWN"))
        self.assertEqual(q["summary"], {"BLOCKED_NO_BOARD": 2})

    def test_past_start_is_rejected_by_the_builder(self):
        q = self.run_q(start=date(2026, 10, 1))
        self.assertEqual(q["summary"], {"REJECTED": 2})


class TestPinImage(unittest.TestCase):
    def test_render_is_2_by_3_with_price(self):
        from PIL import Image
        import build_pin_images as bpi
        o = dict(offers_doc()["offers"][0])
        img = bpi.render(o, Image.new("RGB", (1280, 720), (200, 200, 200)))
        self.assertEqual(img.size, (1000, 1500))


if __name__ == "__main__":
    unittest.main()
