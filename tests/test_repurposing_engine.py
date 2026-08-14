"""Tests for content_generation/repurposing_engine.py (ONE ASSET -> MANY
CHANNELS, directive 2026-08-14).

The engine must be deterministic, zero-cost, never fabricate facts, and
never post externally. Every test asserts on real output derived from a
real asset's own fields.

    python -m unittest tests.test_repurposing_engine -v
"""

import os
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from content_generation import repurposing_engine as re

EU_AI_ASSET = {
    "title": "EU AI Act Compliance Toolkit",
    "description": "Everything a small AI-deploying business needs to get audit-ready. 31-page practical guide: risk classification decision-tree, Annex IV technical documentation mapping, 90-day SME implementation roadmap.",
    "price_usd": 155.0,
    "kind": "asset",
    "tags": ["EU AI Act", "compliance", "SME", "templates"],
}


class TestAssetValidation(unittest.TestCase):
    def test_missing_title_raises(self):
        with self.assertRaises(re.RepurposingError):
            re.Asset(title="", description="some").validate()

    def test_missing_description_raises(self):
        with self.assertRaises(re.RepurposingError):
            re.Asset(title="t", description="").validate()


class TestProductPage(unittest.TestCase):
    def test_real_fields_passthrough(self):
        a = re.Asset(**EU_AI_ASSET)
        out = re.product_page(a)
        self.assertEqual(out["title"], "EU AI Act Compliance Toolkit")
        self.assertIn("31-page practical guide", out["description"])
        self.assertEqual(out["price"], "$155")
        self.assertIn("$155", out["call_to_action"])


class TestShortVideoScript(unittest.TestCase):
    def test_hook_and_hashtags_derived_from_real_fields(self):
        a = re.Asset(**EU_AI_ASSET)
        out = re.short_video_script(a)
        self.assertEqual(out["duration_seconds"], 25)
        self.assertIn("#EUAIAct", out["hashtags"])
        self.assertTrue(out["hook"])
        self.assertIn("$155", out["cta"])

    def test_hook_uses_explicit_pain_marker_when_present(self):
        a = re.Asset(
            title="T", description="Get audit-ready without hiring a compliance consultancy.",
            price_usd=10.0, kind="asset", tags=[],
        )
        out = re.short_video_script(a)
        self.assertIn("Stop hiring a compliance consultancy", out["hook"])
        self.assertNotIn(" by hand", out["hook"])

    def test_hook_falls_back_to_need_question_when_no_pain_marker(self):
        a = re.Asset(
            title="T", description="A real narrative about building a solo AI company.",
            price_usd=10.0, kind="book", tags=[],
        )
        out = re.short_video_script(a)
        self.assertTrue(out["hook"].startswith("Need "))


class TestLinkedInPost(unittest.TestCase):
    def test_body_contains_real_description_and_honest_disclaimer(self):
        a = re.Asset(**EU_AI_ASSET)
        out = re.linkedin_post(a)
        self.assertIn("get audit-ready", out["body"])
        self.assertIn("validation concept", out["body"])
        self.assertIn("$155", out["body"])
        self.assertGreater(out["post_length_chars"], 0)
        self.assertEqual(out["post_length_chars"], len(out["body"]))


class TestXPost(unittest.TestCase):
    def test_stays_within_280_chars(self):
        a = re.Asset(**EU_AI_ASSET)
        out = re.x_post(a)
        self.assertLessEqual(len(out["text"]), out["max_chars"])
        self.assertIn("EU AI Act Compliance Toolkit", out["text"])


class TestFacebookPost(unittest.TestCase):
    def test_contains_real_description_and_price(self):
        a = re.Asset(**EU_AI_ASSET)
        out = re.facebook_post(a)
        self.assertIn("audit-ready", out["text"])
        self.assertIn("$155", out["text"])


class TestPinterestAsset(unittest.TestCase):
    def test_alt_text_derived(self):
        a = re.Asset(**EU_AI_ASSET)
        out = re.pinterest_asset(a)
        self.assertIn("EU AI Act Compliance Toolkit", out["pin_title"])
        self.assertIn("audit-ready", out["pin_description"])
        self.assertLessEqual(len(out["pin_description"]), 200)


class TestEmailNewsletter(unittest.TestCase):
    def test_subject_and_body_real(self):
        a = re.Asset(**EU_AI_ASSET)
        out = re.email_newsletter(a)
        self.assertEqual(out["subject"], "EU AI Act Compliance Toolkit")
        self.assertIn("$155", out["body"])
        self.assertLessEqual(len(out["preview_text"]), 90)


class TestSeoContent(unittest.TestCase):
    def test_meta_description_truncated_to_155(self):
        a = re.Asset(**EU_AI_ASSET)
        out = re.seo_content(a)
        self.assertLessEqual(len(out["meta_description"]), 155)
        self.assertEqual(out["h1"], "EU AI Act Compliance Toolkit")
        self.assertIn("eu ai act", out["keywords"].lower())


class TestRepurposeEngine(unittest.TestCase):
    def test_repurpose_all_channel_defaults(self):
        a = re.Asset(**EU_AI_ASSET)
        out = re.repurpose_all(a)
        self.assertEqual(
            set(out.keys()),
            set(re.CHANNEL_BUILDERS.keys()),
        )
        for name, block in out.items():
            self.assertIsInstance(block, dict)
            self.assertTrue(block, f"channel {name} returned empty dict")

    def test_repurpose_unknown_channel_skipped_honestly(self):
        a = re.Asset(**EU_AI_ASSET)
        out = re.repurpose(a, channels=["linkedin_post", "does_not_exist"])
        self.assertEqual(list(out.keys()), ["linkedin_post"])

    def test_repurpose_is_deterministic(self):
        a1 = re.Asset(**EU_AI_ASSET)
        a2 = re.Asset(**EU_AI_ASSET)
        self.assertEqual(re.repurpose_all(a1), re.repurpose_all(a2))

    def test_every_channel_derives_only_from_real_fields(self):
        a = re.Asset(**EU_AI_ASSET)
        out = re.repurpose_all(a)
        # A strict guard: none of the generated text may contain fabricated
        # claims like "5 star", "1000 customers", "guaranteed", "best".
        forbidden = ("5 star", "5-star", "1000 customers", "guaranteed", "best-selling", "trusted by")
        for name, block in out.items():
            for value in block.values():
                text = str(value)
                for token in forbidden:
                    self.assertNotIn(token.lower(), text.lower(),
                                      f"channel {name} fabricated '{token}'")

    def test_product_page_price_with_decimals(self):
        a = re.Asset(title="t", description="d", price_usd=19.95)
        self.assertEqual(re.product_page(a)["price"], "$19.95")

    def test_missing_price_is_honest_not_fabricated(self):
        a = re.Asset(title="t", description="d")
        out = re.product_page(a)
        self.assertIn("see product page", out["price"])


class TestFromProductAdapter(unittest.TestCase):
    def test_adapts_schema_product(self):
        try:
            from schemas.product import Product
        except Exception:
            self.skipTest("schemas.product not importable in this environment")
        p = Product(
            title="How I Built an Autonomous AI Company Solo",
            subtitle="",
            description="A real narrative about building a solo AI company.",
            price_usd=97.0,
            file_path="books/how_i_built_an_autonomous_ai_company_solo.pdf",
            cover_path=None,
            tags=["autonomous", "ai"],
            language="en",
            source_id="test",
            raw_price_hint=97.0,
            needs_pricing=False,
            price_source="existing",
            product_type="book",
        )
        asset = re.Asset.from_product(p)
        self.assertEqual(asset.title, p.title)
        self.assertEqual(asset.kind, "book")
        out = re.repurpose_all(asset)
        self.assertIn("linkedin_post", out)
        self.assertIn("How I Built", out["linkedin_post"]["headline"])


if __name__ == "__main__":
    unittest.main()
