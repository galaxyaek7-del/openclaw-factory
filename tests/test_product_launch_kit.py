"""Tests for product_launch_kit.py -- deterministic, honest distribution +
attribution prep for a real live digital product (PROFIT FIRST directive).

    python -m unittest tests.test_product_launch_kit -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from product_launch_kit import (
    LAUNCH_TRACKING,
    PRODUCT_ID,
    PRODUCT_TITLE,
    prepare_product_launch_kit,
    record_launch_click,
    render_kit_json,
)


class TestProductLaunchKit(unittest.TestCase):
    def test_all_8_channels_prepared(self):
        kit = prepare_product_launch_kit()
        expected = {"product_page", "short_video_script", "linkedin_post", "x_post",
                    "facebook_post", "pinterest_asset", "email_newsletter", "seo_content"}
        self.assertEqual(set(kit.channel_assets.keys()), expected)

    def test_price_and_url_are_the_real_values(self):
        kit = prepare_product_launch_kit()
        self.assertEqual(kit.price_usd, 155.0)
        self.assertEqual(kit.gumroad_url, "https://aekraft.gumroad.com/l/iaiyt")
        self.assertEqual(kit.product_id, "pzTmMb4v8cih3nbWTj5TeA==")

    def test_tracking_identifiers_are_prepared_static_values(self):
        kit = prepare_product_launch_kit()
        for k in ("channel", "campaign", "content", "utm_medium", "utm_source"):
            self.assertEqual(kit.tracking[k], LAUNCH_TRACKING[k])

    def test_status_honestly_reflects_draft_until_payment_method(self):
        kit = prepare_product_launch_kit()
        self.assertEqual(kit.gumroad_status, "DRAFT_PENDING_PAYMENT_METHOD")

    def test_no_fabricated_sales_or_reviews_in_any_channel(self):
        kit = prepare_product_launch_kit()
        for ch, asset in kit.channel_assets.items():
            blob = json.dumps(asset, ensure_ascii=False).lower()
            self.assertNotIn("5-star", blob)
            self.assertNotIn("reviewed by", blob)

    def test_deterministic_same_input_same_output(self):
        a = json.loads(render_kit_json(prepare_product_launch_kit()))
        b = json.loads(render_kit_json(prepare_product_launch_kit()))
        a.pop("prepared_at", None)
        b.pop("prepared_at", None)
        self.assertEqual(a, b)

    def test_record_launch_click_writes_attributed_click_to_real_ledger_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "clicks.jsonl"
            rec = record_launch_click(ledger_path=ledger)
            self.assertEqual(rec["product_id"], PRODUCT_ID)
            self.assertEqual(rec["channel"], LAUNCH_TRACKING["channel"])
            self.assertEqual(rec["campaign"], LAUNCH_TRACKING["campaign"])
            self.assertEqual(rec["content"], LAUNCH_TRACKING["content"])
            from affiliate_commerce import click_tracking
            summary = click_tracking.attributed_click_summary(ledger)
            self.assertEqual(summary["total_real_clicks"], 1)
            self.assertEqual(summary["clicks_by_channel"].get(LAUNCH_TRACKING["channel"]), 1)


if __name__ == "__main__":
    unittest.main()