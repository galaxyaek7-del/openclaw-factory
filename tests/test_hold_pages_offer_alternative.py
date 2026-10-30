"""A page that says "not for sale" must still lead somewhere honest.

Cycle 89: `eu-ai-act-compliance-toolkit.html` is one of the three pages Bing
actually indexes, and until now it ended in "cannot be bought at any amount"
with no next step -- a visitor who arrived from search had nothing to click.
The fix was to name the two companion checklists that are published, priced,
and were each checked against the same corrected enforcement timeline.

Two ways that fix can rot, and both are silent:

1. someone links a held or unpublished listing as an alternative, so the
   "available now" box offers something nobody can buy;
2. the catalog price moves and the page keeps quoting the old number.

So the rule is mechanical: every Gumroad link on a hold page must resolve to
a catalog product that is priced and not on hold, the price printed next to
it must be that product's price, and the held listing itself must never be
linked as buyable from anywhere on the site. The negative fixtures below
prove the check fails when either condition breaks.
"""

from __future__ import annotations

import glob
import json
import os
import re
import tempfile
import unittest

SITE = "customer_site"
CATALOG = os.path.join(SITE, "catalog.json")
HOLD_PAGES = (
    os.path.join(SITE, "eu-ai-act-compliance-toolkit.html"),
    os.path.join(SITE, "offer-eu-ai-act-toolkit.html"),
)
GUMROAD = re.compile(r"https://[a-z0-9.-]*gumroad\.com/l/[A-Za-z0-9_-]+")
OFFER = re.compile(
    r'<li><a href="(https://[a-z0-9.-]*gumroad\.com/l/[A-Za-z0-9_-]+)">'
    r"(.*?)</a>\s*(?:&mdash;|—)\s*\$(\d+(?:\.\d+)?)</li>",
    re.S,
)


def normalize_url(url):
    return url.split("?")[0].rstrip("/")


def load_catalog(path=CATALOG):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)["data"]
    return {normalize_url(p["url"]): p for p in data["products"]}


def held_slugs():
    import hold_policy

    return set(hold_policy.hold_slugs())


def slug_of(url):
    return url.rstrip("/").split("/")[-1].lower()


def links(html):
    return [normalize_url(u) for u in GUMROAD.findall(html)]


def offers(html):
    return [(url, title.strip(), price) for url, title, price in OFFER.findall(html)]


def check_hold_page(html, catalog, held):
    """Every link buyable and not held, every printed price the real one."""
    problems = []
    urls = links(html)
    if not urls:
        problems.append("hold page offers no alternative at all")
    for url in urls:
        slug = slug_of(url)
        if slug in held:
            problems.append("offers a held listing as buyable: %s" % slug)
            continue
        product = catalog.get(url)
        if product is None:
            problems.append("links a listing the catalog does not carry: %s" % url)
            continue
        if int(product.get("price_cents") or 0) <= 0:
            problems.append("offers an unpriced listing as buyable: %s" % url)
    for url, title, price in offers(html):
        product = catalog.get(url)
        if product is None:
            continue
        expected = float(product.get("price_cents") or 0) / 100.0
        if abs(float(price) - expected) > 0.001:
            problems.append(
                "prints $%s for %s but the catalog price is $%.2f" % (price, title[:50], expected)
            )
    return problems


class TestHoldPagesOfferAnHonestAlternative(unittest.TestCase):
    def test_every_gumroad_link_on_a_hold_page_is_buyable_and_not_held(self):
        catalog = load_catalog()
        held = held_slugs()
        for path in HOLD_PAGES:
            self.assertTrue(os.path.exists(path), path)
            with open(path, encoding="utf-8") as fh:
                problems = check_hold_page(fh.read(), catalog, held)
            self.assertEqual(problems, [], "%s: %s" % (path, problems))

    def test_the_alternative_is_named_with_its_real_price(self):
        catalog = load_catalog()
        for path in HOLD_PAGES:
            with open(path, encoding="utf-8") as fh:
                found = offers(fh.read())
            self.assertTrue(found, "%s names no alternative with a price" % path)
            for url, title, price in found:
                product = catalog[url]
                self.assertEqual(
                    float(price), int(product["price_cents"]) / 100.0, "%s: %s" % (path, title)
                )

    def test_the_held_listing_is_never_linked_from_the_site(self):
        held = held_slugs()
        self.assertIn("iaiyt", held)
        offenders = []
        for path in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
            with open(path, encoding="utf-8") as fh:
                slugs = {slug_of(u) for u in links(fh.read())}
            if slugs & held:
                offenders.append((path, sorted(slugs & held)))
        self.assertEqual(offenders, [])

    def test_check_fails_when_a_held_listing_is_offered(self):
        catalog = load_catalog()
        held = {"iaiyt"}
        html = '<li><a href="https://aekraft.gumroad.com/l/iaiyt">Toolkit</a> &mdash; $19</li>'
        problems = check_hold_page(html, catalog, held)
        self.assertTrue(any("held listing" in p for p in problems), problems)

    def test_check_fails_when_the_printed_price_is_wrong(self):
        catalog = load_catalog()
        url = next(
            u for u, p in catalog.items() if int(p.get("price_cents") or 0) > 0
        )
        html = '<li><a href="%s">Something</a> &mdash; $1</li>' % url
        problems = check_hold_page(html, catalog, set())
        self.assertTrue(any("catalog price is" in p for p in problems), problems)

    def test_check_fails_on_a_hold_page_with_no_alternative(self):
        problems = check_hold_page("<p>On hold.</p>", load_catalog(), set())
        self.assertTrue(any("no alternative" in p for p in problems), problems)

    def test_check_fails_on_a_listing_the_catalog_does_not_carry(self):
        html = '<li><a href="https://aekraft.gumroad.com/l/zzzzzz">Ghost</a> &mdash; $5</li>'
        problems = check_hold_page(html, load_catalog(), set())
        self.assertTrue(any("does not carry" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
