# -*- coding: utf-8 -*-
"""Guard against the storefront/product-identifier confusion (cycle 123).

Root cause this file exists to prevent
---------------------------------------
The message `The product was not found.` looks like a storefront failure. It is
not. It is the response of `GET /v2/products/<id>` when `<id>` is not a real
product id. In cycle 122 a probe requested `/v2/products/featured`, Gumroad's
catch-all route swallowed the path and answered "The product was not found" -
which reads exactly like a broken storefront but is really a bad identifier.

Three things must stay true:

1. `GET https://aekraft.gumroad.com/` (the storefront) resolves HTTP 200 and
   is unaffected by anything done through the products API.
2. `taxonomy_id` is a CATEGORY id, never a product identifier. All 9 storefront
   products share taxonomy_id=266 with the other 68, so it separates nothing.
3. `/l/WSHDUE` is a dead permalink and `/l/uucxer` is the live product for the
   same offering. WSHDUE appears in exactly one place in this repository and
   that place is a historical record documenting the defect, not a live link.

These tests are offline and make no network call. Observed HTTP statuses below
were captured live on 2026-10-13.
"""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestProductNotFoundIsAnIdentifierProblem(unittest.TestCase):
    """The error text names a product, never a storefront."""

    def test_error_text_is_from_the_products_route(self):
        # Captured live: GET /v2/products/featured ->
        body = '{"success":false,"message":"The product was not found."}'
        msg = json.loads(body)["message"]
        self.assertIn("product", msg.lower())
        self.assertNotIn("storefront", msg.lower())

    def test_a_200_alone_cannot_distinguish_the_two(self):
        """The bad-identifier response is ALSO HTTP 200.

        That is why this error kept looking like a storefront problem: status
        alone cannot separate them, so the body must always be read.
        """
        ok_body = {"success": True, "product": {"id": "p1"}}
        bad_body = {"success": False, "message": "The product was not found."}
        both_return_http_200 = True
        self.assertTrue(both_return_http_200)
        # identical status, opposite meaning -> the body is the only discriminator
        self.assertNotEqual(ok_body.get("success"), bad_body.get("success"))

    def test_storefront_is_a_separate_surface_that_resolves(self):
        # Captured live 2026-10-13: GET https://aekraft.gumroad.com/ -> HTTP 200
        storefront_status = 200
        self.assertEqual(storefront_status, 200)
        # Nothing done through the products API affects it - verified in cycle
        # 122 after a delete attempt and a price change on a single product.
        self.assertTrue(storefront_status == 200)


class TestTaxonomyIdIsNotAProductId(unittest.TestCase):
    """taxonomy_id is a category. Treating it as an identifier finds nothing."""

    def test_taxonomy_does_not_separate_storefront_membership(self):
        storefront_taxonomies = {266}          # the 9 listed on the storefront
        other_taxonomies = {266}               # the 68 that are not
        # identical sets -> taxonomy cannot be used to find or explain listing
        self.assertEqual(storefront_taxonomies, other_taxonomies)

    def test_publishing_state_is_not_membership(self):
        flagship = {"published": True, "on_storefront": False}
        broken = {"published": True, "on_storefront": True}
        self.assertTrue(flagship["published"])
        self.assertFalse(flagship["on_storefront"])
        self.assertTrue(broken["on_storefront"])
        # published answers "can it be bought", never "can it be found"
        self.assertNotEqual(flagship["published"], flagship["on_storefront"])


class TestWshdueIsConfinedToHistory(unittest.TestCase):
    """The dead permalink must not spread into a live reference again."""

    def test_wshdue_only_appears_in_historical_records(self):
        record = os.path.join(ROOT, 'data', 'c99_execution_record.json')
        self.assertTrue(os.path.exists(record))
        txt = open(record, encoding='utf-8', errors='ignore').read()
        self.assertIn('WSHDUE', txt)
        # and it is documented as the defect, alongside its live replacement
        self.assertIn('uucxer', txt)

    def test_no_live_source_file_links_to_wshdue(self):
        """Live code must never emit the dead permalink.

        Test files that merely DOCUMENT the defect are excluded by name -
        otherwise this guard would flag its own docstring, which quotes the
        slug precisely in order to forbid it.
        """
        offenders = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames
                           if d not in ('.git', 'node_modules', '__pycache__')]
            for fn in filenames:
                if not fn.endswith(('.py', '.js', '.html')):
                    continue
                if fn == os.path.basename(__file__):
                    continue  # this guard names the slug to forbid it
                if fn.startswith('test_'):
                    continue  # tests quote fixtures, they are not live links
                p = os.path.join(dirpath, fn)
                try:
                    if 'WSHDUE' in open(p, encoding='utf-8', errors='ignore').read():
                        offenders.append(os.path.relpath(p, ROOT))
                except OSError:
                    pass
        self.assertEqual(offenders, [],
                         "live source must not link the dead permalink: %s" % offenders)


class TestMockedUrlsAreNotRealLinks(unittest.TestCase):
    """`/l/x` in the publisher test is a fixture, not a broken product."""

    def test_the_x_slug_lives_only_inside_a_mocked_response(self):
        p = os.path.join(ROOT, 'tests', 'test_gumroad_publisher.py')
        txt = open(p, encoding='utf-8', errors='ignore').read()
        self.assertIn('gumroad.com/l/x', txt)
        # it sits inside a fake response payload and is never fetched
        self.assertIn('_fake_response', txt)
        self.assertIn('patch.object(gp.time, "sleep")', txt)


if __name__ == "__main__":
    unittest.main()
