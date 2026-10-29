"""Generated affiliate guide pages: no internal UNKNOWN markers, share tags kept (2026-10-24/29).

Two observed defects in seo_distribution._page_html:
  * 13 public guides printed "for UNKNOWN -- not captured at this granularity
    in the source registry" in the title area, meta description and steps;
  * every regeneration dropped the og:/canonical tags that
    scripts/add_share_cards.py had added, so 17 guides lost them in the
    working copy.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import seo_distribution as sd  # noqa: E402

UNKNOWN_OPP = {
    "opportunity_id": "op-canva",
    "program_name": "Canva affiliate",
    "target_customer": "UNKNOWN -- not captured at this granularity in the source registry",
    "customer_problem": "UNKNOWN -- requires a separate real customer-discovery pass",
    "product_or_service": "Canva",
    "commission_value": "~$36 per annual Pro conversion",
    "commission_duration": "UNKNOWN",
    "payout_terms": "UNKNOWN",
    "minimum_conditions": "UNKNOWN -- see terms link",
    "terms_url": "https://www.canva.com/affiliates/terms/",
}


class GuideQuality(unittest.TestCase):
    def setUp(self):
        self.html = sd._page_html(UNKNOWN_OPP, "canva-affiliate")

    def test_no_unknown_marker_reaches_the_page(self):
        visible = re.sub(r"<script>.*?</script>", "", self.html, flags=re.S)
        self.assertNotIn("UNKNOWN", visible)
        self.assertNotIn("not captured at this granularity", visible)

    def test_description_reads_without_an_audience(self):
        desc = re.search(r'name="description" content="([^"]*)"', self.html).group(1)
        self.assertTrue(desc.startswith("A real, evidence-based guide to Canva affiliate:"), desc)
        self.assertNotIn(" for .", desc)

    def test_known_values_still_shown(self):
        self.assertIn("~$36 per annual Pro conversion", self.html)
        self.assertIn('href="https://www.canva.com/affiliates/terms/"', self.html)

    def test_omitted_terms_are_explained_not_hidden(self):
        self.assertIn("left out rather than guessed", self.html)

    def test_share_and_canonical_tags_present_once_inside_head(self):
        head = self.html.split("</head>")[0]
        for tag in ('property="og:image"', 'property="og:title"', 'property="og:description"',
                    'name="twitter:card"', 'rel="canonical"', 'property="og:url"'):
            self.assertEqual(1, head.count(tag), tag)
        self.assertIn('href="https://galaxyaek7-del.github.io/openclaw-factory/customer_site/guide-canva-affiliate.html"', head)

    def test_og_description_matches_meta_description(self):
        desc = re.search(r'name="description" content="([^"]*)"', self.html).group(1)
        og = re.search(r'property="og:description" content="([^"]*)"', self.html).group(1)
        self.assertEqual(desc, og)

    def test_terms_link_only_for_http_urls(self):
        bad = dict(UNKNOWN_OPP, terms_url="javascript:alert(1)")
        self.assertNotIn("javascript:", sd._page_html(bad, "x"))

    def test_known_helper(self):
        for v in ("UNKNOWN", "UNKNOWN -- x", "COMMISSION_UNKNOWN", "TERMS_UNKNOWN", "", None):
            self.assertEqual("", sd._known(v), v)
        self.assertEqual("Small businesses", sd._known("Small businesses"))
        self.assertEqual("Mostly unknown buyers", sd._known("Mostly unknown buyers"))


if __name__ == "__main__":
    unittest.main()
