"""Tests for scripts/site_metadata_audit.py: temp fixture sites only."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import site_metadata_audit as audit  # noqa: E402

BASE = "https://example.test/site/"


def page(name, *, canonical=None, extra="", body="Hello"):
    canonical = BASE + name if canonical is None else canonical
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{name}</title>'
            f'<link rel="canonical" href="{canonical}">{extra}</head><body>{body}</body></html>')


class SiteAuditTest(unittest.TestCase):
    def run_site(self, pages, sitemap_names=None, unlisted=None, raw=None):
        d = tempfile.mkdtemp()
        site = os.path.join(d, "site")
        os.mkdir(site)
        for name, html in pages.items():
            with open(os.path.join(site, name), "w", encoding="utf-8") as fh:
                fh.write(html)
        for name, data in (raw or {}).items():
            with open(os.path.join(site, name), "wb") as fh:
                fh.write(data)
        names = sitemap_names if sitemap_names is not None else list(pages) + list(raw or {})
        sm = os.path.join(d, "sitemap.xml")
        with open(sm, "w", encoding="utf-8") as fh:
            fh.write("<urlset>" + "".join(f"<url><loc>{BASE}{n}</loc></url>" for n in names) + "</urlset>")
        return audit.audit_site(site, sm, BASE, unlisted or set())

    def kinds(self, report):
        return sorted(f["kind"] for f in report["findings"])

    def test_clean_site(self):
        og = (f'<meta property="og:title" content="A"><meta property="og:url" content="{BASE}a.html">'
              '<meta property="og:image" content="https://x/i.png"><meta name="twitter:card" content="summary">')
        r = self.run_site({"a.html": page("a.html", extra=og, body='<a href="a.html">self</a>')})
        self.assertEqual(r["findings"], [])
        self.assertEqual(r["pages"], 1)

    def test_canonical_pointing_elsewhere_and_empty(self):
        r = self.run_site({"a.html": page("a.html", canonical="https://shop.test/l/x"),
                           "b.html": page("b.html", canonical="")})
        self.assertEqual(self.kinds(r), ["CANONICAL", "CANONICAL"])

    def test_duplicate_og_and_og_url_mismatch(self):
        extra = ('<meta property="og:title" content="A"><meta property="og:title" content="B">'
                 '<meta property="og:url" content="https://other/"><meta name="twitter:card" content="s">')
        r = self.run_site({"a.html": page("a.html", extra=extra)})
        self.assertEqual(self.kinds(r), ["OG_DUP", "OG_URL"])

    def test_relative_og_image_and_missing_twitter(self):
        extra = '<meta property="og:title" content="A"><meta property="og:image" content="img.png">'
        r = self.run_site({"a.html": page("a.html", extra=extra)})
        self.assertEqual(self.kinds(r), ["OG_IMAGE", "TWITTER"])

    def test_broken_relative_link_but_external_and_anchor_ok(self):
        body = '<a href="missing.html">x</a><a href="https://e.test/">y</a><a href="#top">z</a><a href="mailto:a@b">m</a>'
        r = self.run_site({"a.html": page("a.html", body=body)})
        self.assertEqual([(f["kind"], f["detail"]) for f in r["findings"]], [("BROKEN_LINK", "missing.html")])

    def test_sitemap_missing_and_dead(self):
        r = self.run_site({"a.html": page("a.html"), "b.html": page("b.html")}, sitemap_names=["a.html", "gone.html"])
        self.assertEqual(self.kinds(r), ["SITEMAP_DEAD", "SITEMAP_MISSING"])

    def test_noindex_page_not_required_in_sitemap(self):
        extra = '<meta name="robots" content="noindex">'
        r = self.run_site({"a.html": page("a.html"), "d.html": page("d.html", extra=extra)}, sitemap_names=["a.html"])
        self.assertEqual(r["findings"], [])

    def test_draft_page_with_buy_link_and_unlisted_link(self):
        body = 'DRAFT — not yet listed <a href="https://shop.gumroad.com/l/abc">Buy</a>'
        r = self.run_site({"a.html": page("a.html", body=body)}, unlisted={"abc"})
        self.assertEqual(self.kinds(r), ["DRAFT_BUY_LINK", "UNLISTED_LINK"])

    def test_draft_word_only_in_script_is_ignored(self):
        body = '<script>var s="DRAFT";</script><a href="https://shop.gumroad.com/l/abc">Buy</a>'
        r = self.run_site({"a.html": page("a.html", body=body)})
        self.assertEqual(r["findings"], [])

    def test_duplicate_canonical_and_bad_encoding(self):
        r = self.run_site({"a.html": page("a.html"), "b.html": page("b.html", canonical=BASE + "a.html")},
                          raw={"c.html": b"\xff\xfe" + page("c.html").encode("utf-16-le")})
        self.assertIn("CANONICAL_DUP", self.kinds(r))
        self.assertIn("ENCODING", self.kinds(r))


if __name__ == "__main__":
    unittest.main()
