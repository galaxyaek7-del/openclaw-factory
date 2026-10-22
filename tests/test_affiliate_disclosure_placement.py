"""Every third-party affiliate link on customer_site must come after an
affiliate disclosure, and be marked rel="sponsored" (2026-10-22).

Links to Galaxy Forge's own Gumroad store (aekraft.gumroad.com) and own site
(galaxyaek7-del.github.io), with internal ?ref= source tags, are first-party
links, not affiliate links.
Static scan only; no network.

    python -m pytest tests/test_affiliate_disclosure_placement.py -q
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "customer_site"

AFFILIATE_LINK = re.compile(
    r'<a\b[^>]*href="([^"]*(?:[?&](?:sa|tag|aff|affiliate|via|fpr|irclickid)=|[?&]ref=|/api/affiliate/click'
    r'|awin1\.com|partnerlinks|partnerstack|shareasale|amzn\.to|pxf\.io|sjv\.io)[^"]*)"[^>]*>', re.I)
FIRST_PARTY = ("aekraft.gumroad.com", "galaxyaek7-del.github.io/openclaw-factory")
DISCLOSURE = re.compile(r'class="disclosure"|<b>Disclosure:|<strong>(?:Disclosure|إفصاح):', re.I)


def third_party_links(html):
    body = html.find("<body")
    for m in AFFILIATE_LINK.finditer(html, max(body, 0)):
        if not any(d in m.group(1) for d in FIRST_PARTY):
            yield m


class TestDisclosurePlacement(unittest.TestCase):
    def test_disclosure_precedes_every_third_party_affiliate_link(self):
        problems, seen = [], 0
        for page in sorted(SITE.rglob("*.html")):
            html = page.read_text(encoding="utf-8", errors="replace")
            for m in third_party_links(html):
                seen += 1
                d = DISCLOSURE.search(html, 0, m.start())
                if not d:
                    problems.append(f"{page.relative_to(ROOT)}: no disclosure before {m.group(1)[:60]}")
                if "sponsored" not in m.group(0).lower():
                    problems.append(f"{page.relative_to(ROOT)}: link not rel=sponsored {m.group(1)[:60]}")
        self.assertGreater(seen, 0, "scan found no affiliate link at all; the pattern is stale")
        self.assertEqual(problems, [])

    def test_systeme_links_never_use_www(self):
        # help.systeme.io: on systeme.io's own domain, "www" breaks affiliate
        # tracking; the link must be https://systeme.io/?sa=<id>.
        bad = [str(p.relative_to(ROOT)) for p in SITE.rglob("*.html")
               if re.search(r"www\.systeme\.io/?\?sa=", p.read_text(encoding="utf-8", errors="replace"))]
        self.assertEqual(bad, [])

    def test_detector_catches_a_link_before_its_disclosure(self):
        bad = ('<body><a href="https://systeme.io/?sa=x" rel="sponsored">go</a>'
               '<div class="disclosure"><strong>Disclosure:</strong> ...</div></body>')
        m = next(third_party_links(bad))
        self.assertIsNone(DISCLOSURE.search(bad, 0, m.start()))

    def test_own_store_links_are_not_affiliate_links(self):
        own = '<body><a href="https://aekraft.gumroad.com/l/x?ref=galaxyforge_tool">buy</a></body>'
        self.assertEqual(list(third_party_links(own)), [])


if __name__ == "__main__":
    unittest.main()
