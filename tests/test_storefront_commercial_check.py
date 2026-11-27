"""Tests for scripts/storefront_commercial_check.py.

    python -X utf8 -m pytest tests/test_storefront_commercial_check.py -q

Every test builds its own HTML and catalog fixture, so no test depends on
the live storefront copy. Nothing here writes to the repository.
"""

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import scripts.storefront_commercial_check as check


def _catalog(*products):
    if not products:
        products = ({
            "gumroad_slug": "abcde",
            "name": "Test Product",
            "published": True,
            "price_usd": 19.0,
            "commercial_state": "IN_MEASUREMENT_WINDOW",
        },)
    return {"products": list(products)}


def _card(title="Test Product", price="$19", body="A useful guide.", link='<a class="buy" href="https://x.gumroad.com/l/abcde">Get it</a>'):
    price_html = '<span class="price">%s</span>' % price if price is not None else ""
    return '<div class="card"><h2>%s</h2><p>%s</p>%s%s</div>' % (
        title, body, price_html, link)


def _page(*cards, banner=""):
    notice = ""
    if banner:
        notice = ('<p><strong>%s</strong> This product is under review and '
                  'has been withdrawn from promotion.</p>' % banner)
    return "<html><body><main>%s<div class=\"wrap\">%s</div></main></body></html>" % (
        notice, "".join(cards))


def _codes(report):
    return [f["code"] for f in report["findings"]]


class TestStorefrontChecks(unittest.TestCase):
    def test_clean_page_passes(self):
        report = check.analyze(_page(_card()), _catalog())
        self.assertEqual(report["status"], "PASS", report["findings"])
        self.assertEqual(report["counts"][check.ERROR], 0)
        self.assertEqual(report["summary"]["active_buy_links"], 1)

    def test_global_hold_banner_with_active_checkout_is_error(self):
        report = check.analyze(
            _page(_card(), banner="Currently on hold &mdash; not for sale."),
            _catalog())
        self.assertIn("STOREFRONT_GLOBAL_HOLD_BANNER", _codes(report))
        self.assertEqual(report["status"], "ERROR")

    def test_global_hold_banner_with_no_active_checkout_is_allowed(self):
        held = _card(
            link='<a class="buy held" data-held-product="abcde">On hold</a>')
        report = check.analyze(
            _page(held, banner="Currently on hold &mdash; not for sale."),
            _catalog())
        self.assertNotIn("STOREFRONT_GLOBAL_HOLD_BANNER", _codes(report))

    def test_dead_buy_button_is_error(self):
        report = check.analyze(_page(_card(link='<a class="buy">Get it</a>')), _catalog())
        self.assertIn("STOREFRONT_BUY_BUTTON_DEAD", _codes(report))

    def test_held_marker_with_live_href_is_error(self):
        report = check.analyze(
            _page(_card(link='<a class="buy" data-held-product="abcde" href="https://x.gumroad.com/l/abcde">Get it</a>')),
            _catalog())
        self.assertIn("STOREFRONT_HELD_LINK_ACTIVE", _codes(report))

    def test_unknown_slug_is_error(self):
        report = check.analyze(
            _page(_card(link='<a class="buy" href="https://x.gumroad.com/l/zzzzz">Get it</a>')),
            _catalog())
        self.assertIn("STOREFRONT_UNKNOWN_PRODUCT", _codes(report))

    def test_unpublished_product_is_error(self):
        report = check.analyze(
            _page(_card()),
            _catalog({"gumroad_slug": "abcde", "published": False, "price_usd": 19.0}))
        self.assertIn("STOREFRONT_UNPUBLISHED_PRODUCT", _codes(report))

    def test_withdrawn_product_is_error(self):
        report = check.analyze(
            _page(_card()),
            _catalog({"gumroad_slug": "abcde", "published": True, "price_usd": 0,
                      "commercial_state": "WITHDRAWN_NOT_FOR_SALE"}))
        self.assertIn("STOREFRONT_WITHDRAWN_PRODUCT", _codes(report))

    def test_price_mismatch_is_error(self):
        report = check.analyze(_page(_card(price="$29")), _catalog())
        self.assertIn("STOREFRONT_PRICE_MISMATCH", _codes(report))

    def test_missing_price_is_warning(self):
        report = check.analyze(_page(_card(price=None)), _catalog())
        self.assertIn("STOREFRONT_PRICE_UNVERIFIED", _codes(report))
        self.assertEqual(report["status"], "PASS")

    def test_held_card_without_notice_is_warning(self):
        report = check.analyze(
            _page(_card(
                body="A useful guide.",
                link='<a class="buy" data-held-product="abcde">Get it</a>')),
            _catalog())
        self.assertIn("STOREFRONT_HELD_CARD_UNEXPLAINED", _codes(report))
        self.assertEqual(report["status"], "PASS")

    def test_held_card_with_active_free_offer_is_error(self):
        report = check.analyze(
            _page(_card(
                body="On hold. Not ready to buy? Email us and get it free.",
                link='<a class="buy" data-held-product="abcde">On hold</a>')),
            _catalog())
        self.assertIn("STOREFRONT_HELD_CARD_ACTIVE_OFFER", _codes(report))
        self.assertEqual(report["status"], "ERROR")

    def test_held_card_with_delivery_claim_is_error(self):
        report = check.analyze(
            _page(_card(
                body="On hold. The PDF downloads instantly after purchase.",
                link='<a class="buy" data-held-product="abcde">On hold</a>')),
            _catalog())
        self.assertIn("STOREFRONT_HELD_CARD_DELIVERY_CLAIM", _codes(report))
        self.assertEqual(report["status"], "ERROR")

    def test_page_free_offer_that_does_not_exclude_held_is_warning(self):
        held = _card(
            body="On hold. Not for sale while under review.",
            link='<a class="buy" data-held-product="abcde">On hold</a>')
        report = check.analyze(
            _page(held, banner="") +
            '<div class="card"><p>First buyer of each kit gets it free.</p></div>',
            _catalog())
        self.assertIn("STOREFRONT_FREE_OFFER_MAY_COVER_HELD", _codes(report))
        self.assertEqual(report["status"], "PASS")

    def test_two_live_links_in_one_duplicate_group_is_warning(self):
        catalog = _catalog(
            {"gumroad_slug": "abcde", "published": True, "price_usd": 15.0,
             "commercial_state": "DUPLICATE_LISTING_CANDIDATE", "duplicate_group": "g"},
            {"gumroad_slug": "fghij", "published": True, "price_usd": 15.0,
             "commercial_state": "DUPLICATE_LISTING_CANDIDATE", "duplicate_group": "g"})
        report = check.analyze(_page(
            _card(price="$15"),
            _card(price="$15", link='<a class="buy" href="https://x.gumroad.com/l/fghij">Get it</a>')),
            catalog)
        self.assertIn("STOREFRONT_DUPLICATE_LISTING_LINKS", _codes(report))
        self.assertEqual(report["status"], "PASS")

    def test_missing_sources_are_errors_not_crashes(self):
        report = check.build_report(Path("C:/definitely-not-a-real-root"))
        self.assertEqual(report["status"], "ERROR")
        self.assertIn("STOREFRONT_SOURCE_UNREADABLE", _codes(report))


class TestCli(unittest.TestCase):
    def test_exit_code_follows_errors(self):
        from unittest import mock
        bad = {"status": "ERROR", "counts": {check.ERROR: 1, check.WARNING: 0, check.NOTE: 0},
               "findings": [{"severity": check.ERROR, "code": "X", "subject": "s",
                             "detail": "d"}]}
        good = {"status": "PASS", "counts": {check.ERROR: 0, check.WARNING: 0, check.NOTE: 0},
                "findings": []}
        with mock.patch.object(check, "build_report", return_value=bad):
            self.assertEqual(check.main([]), 1)
        with mock.patch.object(check, "build_report", return_value=good):
            self.assertEqual(check.main([]), 0)


if __name__ == "__main__":
    unittest.main()
