"""Tests for channels/paddle_publisher.py + channels/paddle_arm.py
(ADR-065/MASTER_CHARTER.md §2, Step 4). No live Paddle API call is ever
made — requests.request/post is patched in every test, same discipline as
tests/test_gumroad_publisher.py.

    python -m unittest tests.test_paddle_arm -v
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import paddle_publisher as pp
from channels.paddle_arm import PaddleArm
from channels.base_arm import ArmStatus
from schemas.product import Product


def _fake_response(status_code=200, json_data=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.text = text
    resp.json.return_value = json_data if json_data is not None else {"data": {}}
    resp.raise_for_status.side_effect = (
        pp.requests.HTTPError(f"HTTP {status_code}") if status_code >= 400 else None
    )
    return resp


def _product(price_usd=197.0, file_path="x.pdf"):
    return Product(
        title="AI Compliance Automation Subscription", subtitle="", description="test",
        price_usd=price_usd, file_path=file_path, cover_path=None, tags=[], language="en",
        source_id="t1", raw_price_hint=price_usd, needs_pricing=False, price_source="profit_raw",
        product_type="book",
    )


class TestLoadApiKey(unittest.TestCase):
    def test_missing_key_raises_config_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(pp.ConfigError):
                pp.load_api_key(env_path="/no/such/.env")

    def test_env_var_takes_priority(self):
        with patch.dict(os.environ, {"PADDLE_API_KEY": "from-env"}):
            self.assertEqual(pp.load_api_key(env_path="/no/such/.env"), "from-env")


class TestKeyNeverLeaksInErrors(unittest.TestCase):
    def test_safe_err_redacts_key_from_exception_text(self):
        exc = Exception("request with Authorization: Bearer secret-paddle-key failed")
        text = pp._safe_err(exc, api_key="secret-paddle-key")
        self.assertNotIn("secret-paddle-key", text)
        self.assertIn("REDACTED", text)


class TestCreateProductAndPrice(unittest.TestCase):
    def test_create_product_posts_expected_fields(self):
        with patch.object(pp.requests, "post", return_value=_fake_response(json_data={"data": {"id": "pro_123"}})) as mock_post:
            result = pp.create_product("k", {"title": "Test Product", "description": "d"})
        self.assertEqual(result["id"], "pro_123")
        body = mock_post.call_args.kwargs["json"]
        self.assertEqual(body["name"], "Test Product")
        # ADR-074: "standard" confirmed live (2026-07-18) as the tax
        # category actually approved on a real Paddle account —
        # "digital-goods" was rejected (product_tax_category_not_approved).
        self.assertEqual(body["tax_category"], "standard")

    def test_create_product_tax_category_overridable(self):
        with patch.object(pp.requests, "post", return_value=_fake_response(json_data={"data": {"id": "pro_123"}})) as mock_post:
            pp.create_product("k", {"title": "Test Product", "tax_category": "saas"})
        self.assertEqual(mock_post.call_args.kwargs["json"]["tax_category"], "saas")

    def test_create_product_surfaces_real_paddle_error_detail(self):
        """The exact real case this was built for: a bare 'HTTP 400
        Client Error' told nothing; Paddle's own error body has the real
        reason (product_tax_category_not_approved)."""
        error_body = {"error": {"code": "product_tax_category_not_approved", "detail": "tax category not approved"}}
        with patch.object(pp.requests, "post", return_value=_fake_response(status_code=400, json_data=error_body)):
            with self.assertRaises(RuntimeError) as ctx:
                pp.create_product("k", {"title": "Test Product"})
        self.assertIn("tax category not approved", str(ctx.exception))

    def test_create_product_requires_title(self):
        with self.assertRaises(pp.ConfigError):
            pp.create_product("k", {"description": "no title"})

    def test_update_product_requires_product_id(self):
        with self.assertRaises(pp.ConfigError):
            pp.update_product("k", None, {"name": "x"})

    def test_update_product_patches_expected_fields(self):
        with patch.object(pp.requests, "patch", return_value=_fake_response(json_data={"data": {"id": "pro_123", "name": "New Name"}})) as mock_patch:
            result = pp.update_product("k", "pro_123", {"name": "New Name"})
        self.assertEqual(result["name"], "New Name")
        self.assertEqual(mock_patch.call_args.kwargs["json"], {"name": "New Name"})

    def test_create_price_requires_product_id(self):
        with self.assertRaises(pp.ConfigError):
            pp.create_price("k", None, {"unit_price_cents": 1000})

    def test_create_price_requires_unit_price(self):
        with self.assertRaises(pp.ConfigError):
            pp.create_price("k", "pro_123", {})

    def test_create_price_posts_expected_fields(self):
        with patch.object(pp.requests, "post", return_value=_fake_response(json_data={"data": {"id": "pri_1"}})) as mock_post:
            pp.create_price("k", "pro_123", {"unit_price_cents": 19700})
        body = mock_post.call_args.kwargs["json"]
        self.assertEqual(body["product_id"], "pro_123")
        self.assertEqual(body["unit_price"]["amount"], "19700")


class TestCreateCheckoutTransaction(unittest.TestCase):
    def test_requires_price_id(self):
        with self.assertRaises(pp.ConfigError):
            pp.create_checkout_transaction("k", None)

    def test_posts_expected_items_and_returns_checkout_url(self):
        checkout_data = {"data": {"id": "txn_1", "checkout": {"url": "https://checkout.paddle.com/xyz"}}}
        with patch.object(pp.requests, "post", return_value=_fake_response(json_data=checkout_data)) as mock_post:
            data, checkout_url = pp.create_checkout_transaction("k", "pri_1", quantity=2)
        self.assertEqual(mock_post.call_args.kwargs["json"], {"items": [{"price_id": "pri_1", "quantity": 2}]})
        self.assertEqual(checkout_url, "https://checkout.paddle.com/xyz")
        self.assertEqual(data["id"], "txn_1")

    def test_no_checkout_object_returns_none_url_never_throws(self):
        with patch.object(pp.requests, "post", return_value=_fake_response(json_data={"data": {"id": "txn_1"}})):
            data, checkout_url = pp.create_checkout_transaction("k", "pri_1")
        self.assertIsNone(checkout_url)

    def test_surfaces_real_checkout_not_enabled_error(self):
        """The exact real case this was built for: a fresh Paddle account
        can accept product/price creation while still blocking checkout
        creation until onboarding is fully complete."""
        error_body = {"error": {"code": "transaction_checkout_not_enabled", "detail": "Checkouts aren't enabled for this account."}}
        with patch.object(pp.requests, "post", return_value=_fake_response(status_code=400, json_data=error_body)):
            with self.assertRaises(RuntimeError) as ctx:
                pp.create_checkout_transaction("fake-paddle-key", "pri_1")
        self.assertIn("Checkouts aren't enabled", str(ctx.exception))


class TestPaddleArmGracefulNotConfigured(unittest.TestCase):
    """Mission requirement: 'graceful not configured state' — never a
    crash, always ArmStatus.UNAVAILABLE, same as every other arm."""

    def test_status_unavailable_without_api_key(self):
        arm = PaddleArm()
        with patch.object(pp, "load_api_key", side_effect=pp.ConfigError("missing")):
            self.assertEqual(arm.status(), ArmStatus.UNAVAILABLE)

    def test_publish_without_api_key_never_raises(self):
        arm = PaddleArm()
        with patch.object(pp, "load_api_key", side_effect=pp.ConfigError("missing")):
            result = arm.publish(_product(), dry_run=False)
        self.assertFalse(result.ok)
        self.assertIn("not ready", result.error)

    def test_get_sales_without_api_key_never_raises(self):
        arm = PaddleArm()
        with patch.object(pp, "load_api_key", side_effect=pp.ConfigError("missing")):
            sales, error = arm.get_sales()
        self.assertEqual(sales, [])
        self.assertIn("not ready", error)


class TestPaddleArmDryRun(unittest.TestCase):
    def test_dry_run_never_calls_real_api(self):
        arm = PaddleArm()
        with patch.object(pp, "load_api_key", return_value="fake-key"), \
             patch.object(pp, "create_product") as mock_create:
            result = arm.publish(_product(), dry_run=True)
        self.assertTrue(result.ok)
        self.assertTrue(result.dry_run)
        mock_create.assert_not_called()


class TestPaddleArmLivePublish(unittest.TestCase):
    def test_publish_creates_product_price_and_checkout_link(self):
        arm = PaddleArm()
        with patch.object(pp, "load_api_key", return_value="fake-key"), \
             patch.object(pp, "create_product", return_value={"id": "pro_1"}) as mock_product, \
             patch.object(pp, "create_price", return_value={"id": "pri_1"}) as mock_price, \
             patch.object(pp, "create_checkout_transaction", return_value=({"id": "txn_1"}, "https://checkout.paddle.com/xyz")) as mock_txn:
            result = arm.publish(_product(price_usd=197.0), dry_run=False)
        self.assertTrue(result.ok)
        self.assertEqual(result.product_id, "pro_1")
        self.assertEqual(result.url, "https://checkout.paddle.com/xyz")
        mock_price.assert_called_once_with("fake-key", "pro_1", {"unit_price_cents": 19700})
        mock_txn.assert_called_once_with("fake-key", "pri_1")

    def test_publish_still_succeeds_when_checkout_creation_fails(self):
        """Real case (2026-07-18): product+price creation can succeed
        while checkout creation is blocked by account onboarding status —
        publish() must still report the real product as created, not
        discard it over a separate, account-level gate."""
        arm = PaddleArm()
        with patch.object(pp, "load_api_key", return_value="fake-key"), \
             patch.object(pp, "create_product", return_value={"id": "pro_1"}), \
             patch.object(pp, "create_price", return_value={"id": "pri_1"}), \
             patch.object(pp, "create_checkout_transaction", side_effect=RuntimeError("transaction_checkout_not_enabled")):
            result = arm.publish(_product(price_usd=197.0), dry_run=False)
        self.assertTrue(result.ok)
        self.assertEqual(result.product_id, "pro_1")
        self.assertIsNone(result.url)

    def test_publish_failure_is_recorded_never_raises(self):
        arm = PaddleArm()
        with patch.object(pp, "load_api_key", return_value="fake-key"), \
             patch.object(pp, "create_product", side_effect=RuntimeError("Paddle API down")):
            result = arm.publish(_product(), dry_run=False)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Paddle API down")


if __name__ == "__main__":
    unittest.main()
