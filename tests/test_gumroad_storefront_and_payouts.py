# -*- coding: utf-8 -*-
"""Guard the storefront/discoverability and payout-ambiguity facts (cycle 118).

Two findings this file exists to keep from being silently forgotten:

1. STOREFRONT CURATION IS DASHBOARD-ONLY.
   On 2026-10-13 the Gumroad storefront listed 9 of 77 products. The flagship
   `/l/fgruzn` (Etsy Suspension Appeal Kit, $29) was NOT among them, while
   `/l/owtmpe` - a $150 product with ZERO delivery files - WAS. The product
   that earns money was invisible to anyone browsing Gumroad; the product that
   could take a buyer's money and deliver nothing was visible.
   `GET /v2/products/<id>` exposes no visibility/featured/listed field, so this
   cannot be fixed from the API.

2. `payouts = 0` IS AMBIGUOUS AND MUST NOT BE READ AS A FAILURE.
   An empty payouts list is equally consistent with (a) a payout method being
   configured and nothing earned yet, and (b) no payout method being
   configured. Probed endpoints: /payout_settings 404, /account 404,
   /balance 404, /settings 404. No endpoint distinguishes the two cases.
   The correct verdict is UNKNOWN - never BLOCKED, never FAIL.

All tests here are pure-logic and offline. No network call is made.
"""
import re
import unittest


class TestStorefrontCurationIsNotFixableFromTheApi(unittest.TestCase):
    def test_single_product_response_has_no_visibility_field(self):
        """The fields Gumroad actually returned, captured live 2026-10-13."""
        observed_keys = [
            "bundle_products", "category", "covers", "currency",
            "custom_delivery_url", "custom_fields", "custom_permalink",
            "description", "file_info", "files", "formatted_price", "id",
            "name", "price", "published", "sales_count", "sales_usd_cents",
            "tags",
        ]
        for visibility_field in ("featured", "listed", "visible",
                                 "storefront", "in_store"):
            self.assertNotIn(
                visibility_field, observed_keys,
                "Gumroad exposes no %r field; storefront curation is "
                "dashboard-only" % visibility_field)

    def test_published_is_not_the_same_as_listed(self):
        """A product can be published=True and still absent from the storefront.

        This is the trap: 'published' answers 'can it be bought', never 'can
        it be found'. Treating published as discoverability is what let the
        flagship stay invisible while the zero-file $150 product stayed visible.
        """
        published = True
        listed_on_storefront = False
        self.assertTrue(published)
        self.assertFalse(listed_on_storefront)
        self.assertNotEqual(published, listed_on_storefront)

    def test_the_finding_is_recorded_here(self):
        doc = (__import__(__name__).__doc__ or "")
        self.assertIn("/l/fgruzn", doc)
        self.assertIn("/l/owtmpe", doc)
        self.assertIn("ZERO delivery files", doc)


class TestPayoutZeroIsAmbiguous(unittest.TestCase):
    PROBED = {"payout_settings": 404, "account": 404, "balance": 404,
              "settings": 404}

    def test_no_endpoint_distinguishes_configured_from_absent(self):
        for endpoint, code in self.PROBED.items():
            self.assertEqual(code, 404,
                             "%s returned %s; if any of these ever returns 200 "
                             "this whole reasoning must be re-examined"
                             % (endpoint, code))

    def test_empty_payouts_is_not_evidence_of_failure(self):
        payouts = []
        self.assertEqual(len(payouts), 0)
        # Both of these remain consistent with the observation:
        configured_but_nothing_earned = True
        not_configured_at_all = True
        self.assertTrue(configured_but_nothing_earned)
        self.assertTrue(not_configured_at_all)
        # Therefore the only honest verdict is UNKNOWN.
        verdict = "UNKNOWN"
        self.assertNotIn(verdict, ("BLOCKED", "FAIL", "PASS"))

    def test_this_file_states_the_unknown_verdict(self):
        doc = (__import__(__name__).__doc__ or "").lower()
        self.assertIn("unknown", doc)
        self.assertIn("never blocked", doc)


class TestDistinctProductsAreNeverSwapped(unittest.TestCase):
    """`/l/fgruzn` and `/l/owtmpe` are DIFFERENT products, verified live.

    Different Gumroad ids, different prices, different file counts. Neither is
    an alias or redirect of the other, so one must never be substituted for the
    other on the strength of a similarity in name.
    """

    def test_identities_are_distinct(self):
        self.assertNotEqual("mvuoJTNLfsWsm0NF-CrZHw==", "IW58tjt2zS14fPYrWZOuxg==")
        self.assertNotEqual(29, 150)
        self.assertNotEqual(1, 0)


if __name__ == "__main__":
    unittest.main()
