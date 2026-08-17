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
    resolve_product_profile,
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


class TestProductLaunchKitProductionIdKeyed(unittest.TestCase):
    """Production OS (ADR-203, 2026-08-17): the launch kit is keyed by
    production_id instead of hardcoded to the one EU AI Act product.
    A real generation-log record provides the profile for any other
    production_id; unknown ids honestly raise instead of fabricating."""

    def _genlog(self, tmp, records):
        path = Path(tmp) / "generation_log.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        return str(path)

    def test_default_remains_the_real_eu_ai_act_product(self):
        kit = prepare_product_launch_kit()
        self.assertEqual(kit.price_usd, 155.0)
        self.assertEqual(kit.gumroad_url, "https://aekraft.gumroad.com/l/iaiyt")
        self.assertEqual(kit.product_id, "pzTmMb4v8cih3nbWTj5TeA==")

    def test_explicit_production_id_resolves_real_generation_log_profile(self):
        record = {
            "production_id": "PROD-e137f7d5506996b2",
            "topic": "automated compliance workflow system for mid-size logistics firms",
            "price": 327, "success": True, "timestamp": "2026-07-18T23:44:00",
        }
        with tempfile.TemporaryDirectory() as tmp:
            genlog = self._genlog(tmp, [record])
            kit = prepare_product_launch_kit(production_id="PROD-e137f7d5506996b2", generation_log_path=genlog)
            self.assertEqual(kit.product_id, "PROD-e137f7d5506996b2")
            self.assertEqual(kit.title, "automated compliance workflow system for mid-size logistics firms")
            self.assertEqual(kit.price_usd, 327)
            # no real storefront page exists for this product -- never fabricated
            self.assertIsNone(kit.gumroad_url)
            self.assertIsNone(kit.landing_page)
            self.assertEqual(kit.tracking["campaign"], "launch-PROD-e137f7d5506996b2")
            self.assertEqual(len(kit.channel_assets), 8)

    def test_gumroad_url_only_for_the_real_default_product(self):
        self.assertEqual(resolve_product_profile()["gumroad_url"], "https://aekraft.gumroad.com/l/iaiyt")
        self.assertEqual(resolve_product_profile(PRODUCT_ID)["gumroad_url"], "https://aekraft.gumroad.com/l/iaiyt")
        record = {"production_id": "PROD-other", "topic": "some other real product", "price": 50,
                  "success": True, "timestamp": "2026-07-18T23:44:00"}
        with tempfile.TemporaryDirectory() as tmp:
            genlog = self._genlog(tmp, [record])
            self.assertIsNone(resolve_product_profile("PROD-other", generation_log_path=genlog)["gumroad_url"])

    def test_unknown_production_id_raises_never_fabricates(self):
        with tempfile.TemporaryDirectory() as tmp:
            genlog = self._genlog(tmp, [])
            with self.assertRaises(ValueError):
                prepare_product_launch_kit(production_id="PROD-unknown-xyz", generation_log_path=genlog)
            with self.assertRaises(ValueError):
                record_launch_click(production_id="PROD-unknown-xyz", generation_log_path=genlog, ledger_path=Path(tmp) / "clicks.jsonl")
            # nothing was written to the ledger for the unknown product
            self.assertFalse((Path(tmp) / "clicks.jsonl").exists())

    def test_record_launch_click_is_keyed_to_the_product(self):
        record = {
            "production_id": "PROD-e137f7d5506996b2",
            "topic": "automated compliance workflow system", "price": 327,
            "success": True, "timestamp": "2026-07-18T23:44:00",
        }
        with tempfile.TemporaryDirectory() as tmp:
            genlog = self._genlog(tmp, [record])
            ledger = Path(tmp) / "clicks.jsonl"
            rec = record_launch_click(production_id="PROD-e137f7d5506996b2", generation_log_path=genlog, ledger_path=ledger)
            self.assertEqual(rec["product_id"], "PROD-e137f7d5506996b2")
            self.assertEqual(rec["campaign"], "launch-PROD-e137f7d5506996b2")
            self.assertIsNone(rec["referrer"])


if __name__ == "__main__":
    unittest.main()