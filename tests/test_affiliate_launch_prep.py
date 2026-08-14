"""Tests for affiliate_launch_prep.py -- honest, deterministic, zero-fabrication
launch preparation for the single internally-decided launch opportunity
(First Revenue directive 2026-08-14).

    python -m unittest tests.test_affiliate_launch_prep -v
"""

import os
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate_launch_prep import (
    LAUNCH_OPPORTUNITY_ID,
    LAUNCH_TRACKING,
    prepare_launch,
    render_launch_prep_json,
)


class TestLaunchPrep(unittest.TestCase):
    def test_picks_the_single_internally_decided_opportunity(self):
        prep = prepare_launch()
        self.assertEqual(prep.opportunity_id, LAUNCH_OPPORTUNITY_ID)
        self.assertEqual(prep.opportunity_id, "CO-digitalocean-affiliate")

    def test_offer_is_a_real_verified_recurring_opportunity(self):
        prep = prepare_launch()
        self.assertEqual(prep.offer["verification_status"], "VERIFIED")
        self.assertTrue(prep.offer["recurring_commission"])
        self.assertTrue(prep.offer.get("payout_algeria_compatible"))

    def test_full_content_chain_all_five_formats(self):
        prep = prepare_launch()
        formats = [p["format"] for p in prep.content_pieces]
        self.assertEqual(formats, ["educational", "comparison", "usecase", "tutorial", "recommendation"])

    def test_content_never_claims_unverified_usage(self):
        prep = prepare_launch()
        all_text = " ".join(p["title"] + " " + p["body"] for p in prep.content_pieces)
        self.assertNotIn("استخدمنا", all_text)
        self.assertIn("لا ندّعي تجربة", all_text)

    def test_every_piece_has_disclosure(self):
        prep = prepare_launch()
        for p in prep.content_pieces:
            self.assertIn("إفصاح", p["disclosure"])
            self.assertIn("Affiliate", p["disclosure"])

    def test_tracking_identifiers_are_the_prepared_static_values(self):
        prep = prepare_launch()
        for k in ("channel", "campaign", "content", "utm_medium", "utm_source"):
            self.assertEqual(prep.tracking[k], LAUNCH_TRACKING[k])

    def test_link_honestly_not_configured_until_founder_action(self):
        prep = prepare_launch()
        self.assertEqual(prep.affiliate_link_status, "NOT_CONFIGURED")
        self.assertIsNone(prep.affiliate_link_url)

    def test_exactly_one_founder_action_defined(self):
        prep = prepare_launch()
        self.assertEqual(prep.founder_action["action"], "APPLY_CJ_DIGITALOCEAN")
        self.assertIn("CJ Affiliate", prep.founder_action["what"])
        self.assertIn("Payoneer", prep.founder_action["what"])

    def test_measurement_is_honest_zero_never_fabricated(self):
        prep = prepare_launch()
        self.assertEqual(prep.measurement["REVENUE_COMMISSION_USD"], 0.0)
        # CONVERSION_RATE may be "N/A" (0 clicks) or 0.0 -- never a made-up number.
        rate = prep.measurement["CONVERSION_RATE"]
        self.assertTrue(rate == 0.0 or str(rate).startswith("N/A"))

    def test_unknown_opportunity_is_rejected_not_fabricated(self):
        with self.assertRaises(ValueError):
            prepare_launch(opportunity_id="CO-does-not-exist")

    def test_click_wired_to_launch_tracking_identifiers_end_to_end(self):
        """A real click on the prepared launch records exactly the prepared
        tracking identifiers and is visible in the dashboard (real ledgers,
        temp paths -- no pollution of production data)."""
        import json as _json
        import tempfile
        from affiliate_commerce import click_tracking

        prep = prepare_launch()
        with tempfile.TemporaryDirectory() as tmp:
            clicks_path = Path(tmp) / "clicks.jsonl"
            click_tracking.record_attributed_click(
                product_id=prep.opportunity_id,
                channel=prep.tracking["channel"],
                campaign=prep.tracking["campaign"],
                content=prep.tracking["content"],
                referrer="https://galaxyforge.test/guides/digitalocean",
                utm_medium=prep.tracking["utm_medium"],
                utm_source=prep.tracking["utm_source"],
                ledger_path=clicks_path,
            )
            records = click_tracking.read_clicks(clicks_path)
            self.assertEqual(len(records), 1)
            rec = records[0]
            self.assertEqual(rec["product_id"], prep.opportunity_id)
            self.assertEqual(rec["channel"], LAUNCH_TRACKING["channel"])
            self.assertEqual(rec["campaign"], LAUNCH_TRACKING["campaign"])
            self.assertEqual(rec["content"], LAUNCH_TRACKING["content"])
            self.assertEqual(rec["utm_medium"], LAUNCH_TRACKING["utm_medium"])
            self.assertEqual(rec["utm_source"], LAUNCH_TRACKING["utm_source"])
            summary = click_tracking.attributed_click_summary(clicks_path)
            self.assertEqual(summary["total_real_clicks"], 1)
            self.assertEqual(summary["clicks_by_channel"].get(LAUNCH_TRACKING["channel"]), 1)

    def test_deterministic_same_input_same_output(self):
        import json as _json
        a = _json.loads(render_launch_prep_json(prepare_launch()))
        b = _json.loads(render_launch_prep_json(prepare_launch()))
        a.pop("prepared_at", None)
        b.pop("prepared_at", None)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()