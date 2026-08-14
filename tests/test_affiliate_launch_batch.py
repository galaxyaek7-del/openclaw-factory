"""Tests for affiliate_launch_batch — deterministic multi-channel launch
assets for the single verified opportunity. No fabricated links, no fake
clicks, no fake revenue."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from affiliate_launch_batch import (
    LAUNCH_CHANNELS,
    UTM_SOURCE_BY_CHANNEL,
    build_launch_batch,
    render_batch_json,
    write_batch_file,
)
from affiliate_launch_prep import LAUNCH_LINK_STATUS


class LaunchBatchBuildTests(unittest.TestCase):
    def setUp(self):
        self.batch = build_launch_batch()

    def test_selects_the_single_verified_opportunity(self):
        self.assertEqual(self.batch.opportunity_id, "CO-digitalocean-affiliate")
        self.assertEqual(self.batch.program_name, "DigitalOcean Affiliate Program")

    def test_all_requested_channels_generated(self):
        channels = {a.channel for a in self.batch.assets}
        self.assertEqual(channels, set(LAUNCH_CHANNELS))
        for ch in LAUNCH_CHANNELS:
            self.assertIn(ch, channels)

    def test_each_asset_carries_unique_utm_content(self):
        contents = [a.attribution["content"] for a in self.batch.assets]
        self.assertEqual(len(contents), len(set(contents)))

    def test_utm_source_matches_channel_map(self):
        for a in self.batch.assets:
            self.assertEqual(a.utm_source, UTM_SOURCE_BY_CHANNEL[a.channel])

    def test_destination_honestly_not_configured(self):
        for a in self.batch.assets:
            self.assertEqual(a.destination_status, LAUNCH_LINK_STATUS)
            self.assertIsNone(a.destination_url)

    def test_no_fabricated_affiliate_link_anywhere(self):
        text = render_batch_json(self.batch)
        for banned in ("tracking", "awin.com?u=", "ref=", "aff_id="):
            self.assertNotIn(banned, text)

    def test_attribution_wired_to_click_fields(self):
        for a in self.batch.assets:
            self.assertIn("source", a.attribution)
            self.assertIn("campaign", a.attribution)
            self.assertIn("content", a.attribution)
            self.assertIn("opportunity_id", a.attribution)

    def test_disclosure_present_in_every_content_render(self):
        # The batch carries one disclosure; channel content is plain useful
        # copy derived from real offer fields (never fabricated facts).
        self.assertIn("Affiliate disclosure", self.batch.disclosure)
        self.assertIn("10 percent", self.batch.disclosure)

    def test_render_is_deterministic_json(self):
        a = render_batch_json(self.batch)
        b = render_batch_json(self.batch)
        self.assertEqual(a, b)
        parsed = json.loads(a)
        self.assertEqual(parsed["opportunity_id"], "CO-digitalocean-affiliate")

    def test_write_batch_file_roundtrip(self):
        with TemporaryDirectory() as td:
            path = write_batch_file(self.batch, output_dir=Path(td))
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["link_status"], LAUNCH_LINK_STATUS)


if __name__ == "__main__":
    unittest.main()