# -*- coding: utf-8 -*-
"""Tests for affiliate_guard (Phase 4 §11). No external calls, no real links."""

import unittest
import affiliate_guard as ag


class TestPlaceholderDetection(unittest.TestCase):
    def test_placeholder_url_rejected(self):
        r = ag.check_link("https://amazon.com/?tag=YOUR_AMAZON_TAG")
        self.assertFalse(r["allowed"])
        self.assertTrue(r["placeholder"])

    def test_empty_url_rejected(self):
        self.assertFalse(ag.check_link("")["allowed"])
        self.assertFalse(ag.check_link(None)["allowed"])

    def test_example_placeholder_rejected(self):
        self.assertFalse(ag.check_link("https://amazon.com/dp/PLACEHOLDER")["allowed"])


class TestDomainControl(unittest.TestCase):
    def test_approved_domain_with_disclosure_allowed(self):
        r = ag.check_link("https://amazon.com/dp/B0TEST123?tag=abc",
                          disclosure_text="This is an affiliate link.")
        self.assertTrue(r["allowed"])
        self.assertEqual(r["domain"], "amazon.com")

    def test_unapproved_domain_rejected(self):
        r = ag.check_link("https://some-random-site.example/ref",
                          disclosure_text="affiliate link")
        self.assertFalse(r["allowed"])
        self.assertEqual(r["reason"], "domain_not_approved")

    def test_fiverr_blocked(self):
        r = ag.check_link("https://fiverr.com/some-affiliate",
                          disclosure_text="affiliate link")
        self.assertFalse(r["allowed"])
        self.assertEqual(r["reason"], "blocked_domain")


class TestDisclosureEnforcement(unittest.TestCase):
    def test_missing_disclosure_rejected(self):
        r = ag.check_link("https://amazon.com/dp/B0TEST123?tag=abc",
                          disclosure_text="check this out")
        self.assertFalse(r["allowed"])
        self.assertEqual(r["reason"], "disclosure_missing")


class TestLinkIntegrity(unittest.TestCase):
    def test_javascript_scheme_rejected(self):
        r = ag.check_link("javascript:alert(1)")
        self.assertFalse(r["allowed"])
        self.assertEqual(r["reason"], "unsafe_scheme")

    def test_unparseable_rejected(self):
        r = ag.check_link("not a url ::::")
        self.assertFalse(r["allowed"])


class TestBatchGuard(unittest.TestCase):
    def test_all_good_pass(self):
        res = ag.guard_affiliate_links(
            ["https://amazon.com/x?tag=a", "https://gumroad.com/y"],
            disclosure_text="affiliate disclosure present")
        self.assertTrue(res["passed"])

    def test_mixed_rejected(self):
        res = ag.guard_affiliate_links(
            ["https://amazon.com/x?tag=a", "https://fiverr.com/z"],
            disclosure_text="affiliate disclosure present")
        self.assertFalse(res["passed"])
        self.assertGreaterEqual(res["rejected_count"], 1)


if __name__ == "__main__":
    unittest.main()
