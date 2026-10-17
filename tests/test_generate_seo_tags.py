"""scripts/generate_seo_tags.py: every suggested tag is grounded in the listing."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("generate_seo_tags", ROOT / "scripts" / "generate_seo_tags.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

LISTING = {
    "id": "1", "name": "Restaurant Food Cost Control Kit", "published": True, "tags": ["restaurant"],
    "description": "<p>Track food cost weekly. Food cost drift hides in waste. Recipe costing sheet, "
                   "food cost alerts and a supplier log. This is not legal advice, not legal advice, "
                   "not legal advice. Waste, inventory counts.</p>",
}


class TestSeoTags(unittest.TestCase):
    def test_tags_are_grounded_and_skip_disclaimers_and_existing(self):
        r = T.suggest(LISTING)
        tags = [t["tag"] for t in r["suggested"]]
        text = (LISTING["name"] + " " + T.text_of(LISTING["description"])).lower()
        for t in tags:
            self.assertIn(t, text)
        self.assertIn("food cost", tags)
        self.assertNotIn("legal advice", tags)          # disclaimer text is never a tag
        self.assertNotIn("restaurant", tags)            # already on the listing
        self.assertNotIn("control", tags)               # too generic alone
        self.assertNotIn("waste inventory", tags)       # never joined across punctuation

    def test_tags_respect_gumroad_length_rule(self):
        """Gumroad source (app/models/tag.rb): 2-20 characters."""
        listing = dict(LISTING, name="Commercial Kitchen Refrigeration Logbook",
                       description="<p>commercial kitchen refrigeration temperature logbook. " * 4 + "</p>")
        for t in T.suggest(listing)["suggested"]:
            self.assertTrue(2 <= len(t["tag"]) <= 20, t["tag"])

    def test_report_skips_unavailable_and_unpublished(self):
        rep = T.run([LISTING, dict(LISTING, id="2", name="[Unavailable] Old"), dict(LISTING, id="3", published=False)])
        self.assertEqual(rep["listings"], 1)


if __name__ == "__main__":
    unittest.main()
