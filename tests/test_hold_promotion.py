"""Cycle 81 Phase 3: HOLD products must not be promoted, and the guard must
actually hold.

Covers the cases the directive named: identity before action, no promotion via
any surface (anchor, og:url, canonical, JSON-LD), listing data preserved, and
no collateral change to other products.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import hold_policy  # noqa: E402

HOLD = tuple(hold_policy.HOLD_PRODUCTS)
ANY_REF = re.compile(r'/l/(?:' + "|".join(HOLD) + r')', re.I)


class TestIdentityIsVerified(unittest.TestCase):
    def test_registry_keys_are_slugs_not_urls(self):
        for slug, entry in hold_policy.HOLD_PRODUCTS.items():
            self.assertRegex(slug, r"^[a-z0-9]+$")
            self.assertIn("product_id", entry)

    def test_product_ids_are_distinct_and_present(self):
        ids = [v["product_id"] for v in hold_policy.HOLD_PRODUCTS.values()]
        self.assertEqual(len(ids), len(set(ids)))
        for i in ids:
            self.assertTrue(i)

    def test_unknown_slug_is_not_held(self):
        # The report named /l/iaiyi, which does not exist. Treating a
        # non-existent slug as a real product is how the wrong listing gets
        # edited.
        self.assertFalse(hold_policy.is_on_hold("iaiyi"))
        self.assertFalse(hold_policy.is_on_hold(""))
        self.assertFalse(hold_policy.is_on_hold(None))

    def test_real_slugs_are_held(self):
        self.assertTrue(hold_policy.is_on_hold("iaiyt"))
        self.assertTrue(hold_policy.is_on_hold("wteork"))
        self.assertTrue(hold_policy.is_on_hold("IAIYT"))  # case-insensitive


class TestNoPromotionThroughAnySurface(unittest.TestCase):
    HTML = (
        '<a href="https://aekraft.gumroad.com/l/iaiyt?ref=x">Buy</a>'
        '<meta property="og:url" content="https://aekraft.gumroad.com/l/iaiyt">'
        '<link rel="canonical" href="https://aekraft.gumroad.com/l/wteork">'
        '{"url": "https://aekraft.gumroad.com/l/wteork"}'
    )

    def test_all_reference_kinds_are_scrubbed(self):
        out = hold_policy.scrub_hold_links(self.HTML)
        self.assertIsNone(ANY_REF.search(out),
                          f"a held listing is still referenced:\n{out}")

    def test_scrub_is_idempotent(self):
        once = hold_policy.scrub_hold_links(self.HTML)
        self.assertEqual(hold_policy.scrub_hold_links(once), once)


class TestNoCollateralDamage(unittest.TestCase):
    def test_other_products_are_untouched(self):
        html = ('<a href="https://aekraft.gumroad.com/l/bfhpzl?ref=x">Bundle</a>'
                '<a href="https://aekraft.gumroad.com/l/fgruzn">Kit</a>')
        out = hold_policy.scrub_hold_links(html)
        self.assertIn("/l/bfhpzl", out)
        self.assertIn("/l/fgruzn", out)

    def test_text_content_is_preserved(self):
        html = '<a href="https://aekraft.gumroad.com/l/iaiyt">Get the Toolkit</a>'
        out = hold_policy.scrub_hold_links(html)
        self.assertIn("Get the Toolkit", out)

    def test_empty_and_none_are_safe(self):
        self.assertEqual(hold_policy.scrub_hold_links(""), "")
        self.assertIsNone(hold_policy.scrub_hold_links(None))

    def test_scrubbing_does_not_change_prices(self):
        html = ('<a href="https://aekraft.gumroad.com/l/iaiyt">EU AI $155</a>'
                '<a href="https://aekraft.gumroad.com/l/bfhpzl">Bundle $79</a>')
        out = hold_policy.scrub_hold_links(html)
        self.assertIn("$155", out)
        self.assertIn("$79", out)


class TestRepositorySurfacesAreClean(unittest.TestCase):
    """The real guard: no tracked promotional page may link a held listing."""

    SURFACES = ("customer_site/products.html",
                "customer_site/eu-ai-act-compliance-toolkit.html",
                "customer_site/blog-eu-ai-act-compliance-sme-guide.html",
                "customer_site/index.html")

    def test_no_held_listing_is_promoted(self):
        bad = []
        for path in self.SURFACES:
            if not os.path.isfile(path):
                continue
            html = open(path, encoding="utf-8", errors="replace").read()
            # only promotional references count: a link or metadata that
            # points a reader or a social preview at the listing
            for m in re.finditer(
                    r'(?:href|content)="[^"]*/l/(?:' + "|".join(HOLD) + r')[^"]*"'
                    r'|"url"\s*:\s*"[^"]*/l/(?:' + "|".join(HOLD) + r')[^"]*"',
                    html, re.I):
                bad.append((path, m.group(0)[:70]))
        self.assertEqual(bad, [], f"held products still promoted: {bad}")


if __name__ == "__main__":
    unittest.main(verbosity=2)