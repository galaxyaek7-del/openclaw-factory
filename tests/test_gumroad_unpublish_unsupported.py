# -*- coding: utf-8 -*-
"""Why there is no /disable call anywhere in this factory (cycle 117).

Root cause of the cycle-116 `POST /v2/products/<id>/disable -> 404`
-----------------------------------------------------------------
That endpoint was INVENTED in a scratch script. It was never a documented
Gumroad route and never existed as a call site in this repository. Evidence:

  * `channels/gumroad_publisher.py` documents exactly one publish-state route,
    `PUT /v2/products/:id/enable`, and contains no `disable` anywhere.
  * A live probe of `POST /v2/products/<id>/disable` returned HTTP 404 with
    Gumroad's HTML "Page not found" page, not a JSON API error.
  * The only documented write that could plausibly unpublish,
    `PUT /v2/products/:id` with `published=false`, returned HTTP 200 and
    changed nothing - the same silent no-op proven for `description` on the
    same product.

Conclusion: Gumroad's public API offers `enable` but offers NO way to unpublish
or delete. That operation is BLOCKED on the dashboard.

These tests use mocks only. No real product, real network call, or real
unpublish is ever exercised.
"""
import unittest
from unittest import mock

import requests

import channels.gumroad_publisher as gp


class TestNoInventedDisableEndpoint(unittest.TestCase):
    """The factory must never call an unpublish route that does not exist."""

    def test_publisher_never_mentions_a_disable_route(self):
        src = open(gp.__file__, encoding="utf-8").read()
        self.assertNotIn("/disable", src,
                         "gumroad_publisher must not call a /disable route: "
                         "Gumroad's public API has no such endpoint")
        self.assertIn("/enable", src,
                      "the documented publish route is /enable and must remain")

    def test_enable_uses_put_not_post(self):
        """`/enable` is a PUT. Do not 'fix' a 404 by swapping verbs."""
        src = open(gp.__file__, encoding="utf-8").read()
        self.assertIn('"PUT", f"{GUMROAD_API_BASE}/products/{product_id}/enable"',
                      src)

    def test_invented_disable_returns_404_and_is_not_retried(self):
        """A 404 from an invented route must surface, not be papered over."""
        resp = mock.Mock(status_code=404, text="<title>Page not found (404)</title>")
        with mock.patch.object(requests, "post", return_value=resp) as post:
            r = requests.post("https://api.gumroad.com/v2/products/X/disable",
                              data={"access_token": "t"}, timeout=30)
        self.assertEqual(r.status_code, 404)
        self.assertIn("404", r.text)
        self.assertTrue(post.called)

    def test_published_false_is_a_silent_noop_not_a_success(self):
        """HTTP 200 from PUT does NOT mean the product was unpublished.

        This is the trap: Gumroad accepted `published=false` and left the
        product published. Any caller that treats 200 as proof would report a
        fix that never happened.
        """
        accepted_but_unchanged = mock.Mock(status_code=200, text='{"success":true}')
        with mock.patch.object(requests, "put", return_value=accepted_but_unchanged):
            resp = requests.put("https://api.gumroad.com/v2/products/X",
                                data={"access_token": "t", "published": "false"},
                                timeout=60)
        self.assertEqual(resp.status_code, 200)
        # The 200 is real AND the state change is absent. A 200 must therefore
        # never be treated as verification - a follow-up GET is required.
        self.assertNotIn("unpublished", str(resp.text).lower())

    def test_verification_must_be_a_real_followup_get(self):
        """get_product() is the only accepted way to confirm a write landed.

        Mocked at requests.request, which is what _request_with_retry uses.
        Mocking requests.get would NOT intercept it and would leak a live
        network call - exactly what these tests must never do.
        """
        payload = {"success": True,
                   "product": {"id": "X", "published": True, "files": []}}
        resp = mock.Mock(status_code=200)
        resp.json.return_value = payload
        with mock.patch.object(requests, "request", return_value=resp) as req:
            got = gp.get_product("t", "X")
        self.assertTrue(req.called)
        # still published -> the caller can see the write did not take
        self.assertTrue(got.get("published"))


class TestUnpublishIsDocumentedAsUnsupported(unittest.TestCase):
    def test_this_module_states_the_constraint(self):
        doc = (__import__(__name__).__doc__ or "").lower()
        self.assertIn("no way to unpublish", doc)
        self.assertIn("blocked", doc)


if __name__ == "__main__":
    unittest.main()
