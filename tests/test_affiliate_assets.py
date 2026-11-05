import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "drafts" / "affiliate_portfolio"
ASSET_IDS = ("AFF-DO-001", "AFF-N8N-001")


class TestAffiliateAssetPackages(unittest.TestCase):
    def test_every_package_has_required_files(self):
        for asset_id in ASSET_IDS:
            folder = ASSETS / asset_id
            for name in ("asset.md", "metadata.json", "sources.json", "qa_report.json"):
                self.assertTrue((folder / name).is_file(), "%s/%s" % (asset_id, name))

    def test_no_asset_is_authorized_or_linked(self):
        for asset_id in ASSET_IDS:
            meta = json.loads((ASSETS / asset_id / "metadata.json").read_text(encoding="utf-8"))
            self.assertFalse(meta["publication_authorized"], asset_id)
            self.assertEqual(meta["affiliate_link_state"], "BLOCKED", asset_id)
            self.assertEqual(meta["state"], "QA_HOLD", asset_id)

    def test_no_asset_contains_an_anchor_or_placeholder_link(self):
        for asset_id in ASSET_IDS:
            text = (ASSETS / asset_id / "asset.md").read_text(encoding="utf-8").lower()
            self.assertNotIn("href=", text, asset_id)
            self.assertNotIn("affiliate_link_not_configured", text, asset_id)

    def test_disclosure_is_visible_and_qa_stays_hold(self):
        for asset_id in ASSET_IDS:
            folder = ASSETS / asset_id
            text = (folder / "asset.md").read_text(encoding="utf-8")
            meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
            qa = json.loads((folder / "qa_report.json").read_text(encoding="utf-8"))
            self.assertIn("affiliate disclosure", text.lower(), asset_id)
            self.assertTrue(meta["disclosure_present"], asset_id)
            self.assertEqual(qa["status"], "HOLD", asset_id)
            self.assertIn("no CTA present", qa["failures"], asset_id)

    def test_n8n_keeps_its_paypal_conditions_explicit(self):
        meta = json.loads((ASSETS / "AFF-N8N-001" / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["payout_algeria_state"], "CONDITIONAL_PAYPAL_ALGERIA")
        self.assertTrue(any("paypal" in b.lower() for b in meta["blockers"]))
        self.assertFalse(any("blocked in algeria" in b.lower() for b in meta["blockers"]))

    def test_digitalocean_records_the_awin_conditions(self):
        meta = json.loads((ASSETS / "AFF-DO-001" / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(
            meta["payout_algeria_state"],
            "COMPATIBLE_AWIN_PAYONEER_REVALIDATED",
        )
        self.assertTrue(any("awin" in b.lower() for b in meta["blockers"]))

    def test_sources_do_not_repeat_the_unsupported_paypal_block(self):
        for asset_id in ASSET_IDS:
            text = (ASSETS / asset_id / "sources.json").read_text(encoding="utf-8").lower()
            self.assertNotIn("paypal receiving is documented as blocked", text, asset_id)
            self.assertNotIn("paypal does not support receiving", text, asset_id)

    def test_sources_are_dated_and_have_no_placeholder_urls(self):
        for asset_id in ASSET_IDS:
            data = json.loads((ASSETS / asset_id / "sources.json").read_text(encoding="utf-8"))
            for source in data["sources"]:
                self.assertTrue(source["evidence_date"], asset_id)
                url = source.get("source_url")
                if url is not None:
                    self.assertTrue(url.startswith("https://"), (asset_id, url))
                    self.assertNotIn("example.", url)


if __name__ == "__main__":
    unittest.main()
