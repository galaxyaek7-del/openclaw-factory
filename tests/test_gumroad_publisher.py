"""Tests for channels/gumroad_publisher.py (ADR-030, Gumroad-first arm
completion). No live Gumroad API call is ever made — requests.request is
patched in every test.

    python -m unittest tests.test_gumroad_publisher -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import gumroad_publisher as gp


def _fake_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {"success": True}
    if status_code >= 400:
        resp.raise_for_status.side_effect = gp.requests.HTTPError(f"HTTP {status_code}")
    else:
        resp.raise_for_status.side_effect = None
    return resp


class TestRetryOnTransientFailure(unittest.TestCase):
    def test_get_sales_retries_after_one_5xx_then_succeeds(self):
        responses = [
            _fake_response(status_code=503),
            _fake_response(status_code=200, json_data={"success": True, "sales": [{"id": "s1"}]}),
        ]
        with patch.object(gp.requests, "request", side_effect=responses) as mock_req, \
             patch.object(gp.time, "sleep") as mock_sleep:
            sales = gp.get_sales("fake-token")
        self.assertEqual(sales, [{"id": "s1"}])
        self.assertEqual(mock_req.call_count, 2)
        mock_sleep.assert_called_once()

    def test_get_sales_gives_up_after_max_attempts(self):
        responses = [_fake_response(status_code=503)] * gp._RETRY_ATTEMPTS
        with patch.object(gp.requests, "request", side_effect=responses), \
             patch.object(gp.time, "sleep"):
            with self.assertRaises(RuntimeError):
                gp.get_sales("fake-token")

    def test_4xx_is_never_retried(self):
        responses = [_fake_response(status_code=401)]
        with patch.object(gp.requests, "request", side_effect=responses) as mock_req, \
             patch.object(gp.time, "sleep") as mock_sleep:
            with self.assertRaises(RuntimeError):
                gp.get_sales("fake-token")
        self.assertEqual(mock_req.call_count, 1)
        mock_sleep.assert_not_called()

    def test_create_product_is_never_retried_even_on_5xx(self):
        """create_product is a POST — never idempotent-safe to retry. A 5xx
        on the final product create must surface immediately as a single
        failed attempt, not be retried (a lost-response retry could otherwise
        double-create a paid listing on Gumroad's side). The presign flow that
        precedes it (presign -> S3 PUT -> complete) is mocked out; only the
        final create POST is exercised."""
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(b"%PDF-1.4 fake")
        tmp.close()

        presign = _fake_response(status_code=200, json_data={
            "success": True,
            "upload_id": "u1",
            "key": "k1",
            "parts": [{"part_number": 1, "presigned_url": "https://s3/part1"}],
        })
        put_resp = _fake_response(status_code=200)
        put_resp.headers = {"ETag": '"etag-1"'}
        complete_ok = _fake_response(status_code=200, json_data={
            "success": True,
            "file_url": "https://s3/final.pdf",
        })

        try:
            with patch.object(gp.requests, "request", side_effect=[presign, put_resp]) as mock_req, \
                 patch.object(gp.time, "sleep"), \
                 patch.object(gp.requests, "post",
                              side_effect=[complete_ok, _fake_response(status_code=503)]) as mock_post:
                with self.assertRaises(RuntimeError):
                    gp.create_product("fake-token", {
                        "title": "Test",
                        "price_cents": 999,
                        "file_path": tmp.name,
                    })
            # complete (1) + the single, un-retried create POST (1) = 2.
            self.assertEqual(mock_post.call_count, 2)
            self.assertEqual(mock_req.call_count, 2)
        finally:
            os.unlink(tmp.name)


class TestTokenNeverLeaksInErrors(unittest.TestCase):
    def test_safe_err_redacts_token_from_exception_text(self):
        import os
        with patch.dict(os.environ, {"GUMROAD_ACCESS_TOKEN": "secret123"}):
            exc = Exception("request to https://api.gumroad.com/v2/sales?access_token=secret123 failed")
            text = gp._safe_err(exc)
        self.assertNotIn("secret123", text)
        self.assertIn("REDACTED", text)


class TestEnableProduct(unittest.TestCase):
    def test_enable_hits_the_real_enable_endpoint(self):
        ok = _fake_response(status_code=200, json_data={
            "success": True,
            "product": {"id": "p1", "published": True, "url": "https://aekraft.gumroad.com/l/x",
                        "formatted_price": "$155"},
        })
        with patch.object(gp.requests, "request", return_value=ok) as mock_req, \
             patch.object(gp.time, "sleep"):
            product = gp.enable_product("fake-token", "p1")
        self.assertTrue(product["published"])
        self.assertEqual(product["url"], "https://aekraft.gumroad.com/l/x")
        # Must hit /products/{id}/enable -- the real publish endpoint, not a
        # 'publish' field on the generic PUT.
        args, kwargs = mock_req.call_args
        self.assertTrue(args[1].endswith("/products/p1/enable"))
        self.assertEqual(kwargs["data"], {"access_token": "fake-token"})

    def test_enable_surfaces_payment_method_blocker_honestly(self):
        blocked = _fake_response(status_code=200, json_data={
            "success": False,
            "message": "You must connect at least one payment method before you can publish this product for sale.",
        })
        with patch.object(gp.requests, "request", return_value=blocked):
            with self.assertRaisesRegex(RuntimeError, "payment method"):
                gp.enable_product("fake-token", "p1")


class TestGetProduct(unittest.TestCase):
    def test_get_product_returns_real_state(self):
        ok = _fake_response(status_code=200, json_data={
            "success": True,
            "product": {"id": "p1", "published": False, "price": 15500, "short_url": "https://aekraft.gumroad.com/l/iaiyt"},
        })
        with patch.object(gp.requests, "request", return_value=ok):
            product = gp.get_product("fake-token", "p1")
        self.assertEqual(product["price"], 15500)
        self.assertFalse(product["published"])
        self.assertEqual(product["short_url"], "https://aekraft.gumroad.com/l/iaiyt")


if __name__ == "__main__":
    unittest.main()
