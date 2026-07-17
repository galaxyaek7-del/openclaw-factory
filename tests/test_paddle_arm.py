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


def _fake_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
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
        self.assertEqual(body["tax_category"], "digital-goods")

    def test_create_product_requires_title(self):
        with self.assertRaises(pp.ConfigError):
            pp.create_product("k", {"description": "no title"})

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
    def test_publish_creates_product_then_price(self):
        arm = PaddleArm()
        with patch.object(pp, "load_api_key", return_value="fake-key"), \
             patch.object(pp, "create_product", return_value={"id": "pro_1"}) as mock_product, \
             patch.object(pp, "create_price", return_value={"id": "pri_1"}) as mock_price:
            result = arm.publish(_product(price_usd=197.0), dry_run=False)
        self.assertTrue(result.ok)
        self.assertEqual(result.product_id, "pro_1")
        mock_price.assert_called_once_with("fake-key", "pro_1", {"unit_price_cents": 19700})

    def test_publish_failure_is_recorded_never_raises(self):
        arm = PaddleArm()
        with patch.object(pp, "load_api_key", return_value="fake-key"), \
             patch.object(pp, "create_product", side_effect=RuntimeError("Paddle API down")):
            result = arm.publish(_product(), dry_run=False)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Paddle API down")


if __name__ == "__main__":
    unittest.main()
