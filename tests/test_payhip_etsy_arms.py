"""Tests for channels/payhip_arm.py, channels/etsy_arm.py (ADR-025).

Runs with stdlib unittest (see tests/test_base_arm.py). No live Payhip/Etsy
API call is ever made: create_product()/load_token()/load_credentials()
are patched in every test that exercises a non-dry-run path.

    python -m unittest tests.test_payhip_etsy_arms -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels.base_arm import ArmStatus
from channels import payhip_arm as payhip_arm_module
from channels import etsy_arm as etsy_arm_module
from channels.payhip_arm import PayhipArm
from channels.etsy_arm import EtsyArm
from schemas.product import Product


def make_product(**overrides):
    defaults = dict(
        title="Test Product",
        subtitle="",
        description="A test product",
        price_usd=97.0,
        file_path=str(_FACTORY_ROOT / "schemas" / "product.py"),  # any real file
        cover_path=None,
        tags=[],
        language="en",
        source_id="test-1",
        raw_price_hint=97.0,
        needs_pricing=False,
        price_source="profit_raw",
        product_type="premium",
    )
    defaults.update(overrides)
    return Product(**defaults)


class TestPayhipArm(unittest.TestCase):
    def setUp(self):
        self.arm = PayhipArm()

    def test_status_unavailable_without_token(self):
        with patch.object(
            payhip_arm_module.payhip_publisher, "load_token",
            side_effect=payhip_arm_module.payhip_publisher.ConfigError("no token"),
        ):
            self.assertEqual(self.arm.status(), ArmStatus.UNAVAILABLE)

    def test_status_ready_with_token(self):
        with patch.object(payhip_arm_module.payhip_publisher, "load_token", return_value="fake-key"):
            self.assertEqual(self.arm.status(), ArmStatus.READY)

    def test_supports_rejects_missing_file(self):
        self.assertFalse(self.arm.supports(make_product(file_path="")))

    def test_supports_rejects_unresolved_price(self):
        self.assertFalse(self.arm.supports(make_product(price_usd=None, needs_pricing=True)))

    def test_supports_accepts_valid_product(self):
        self.assertTrue(self.arm.supports(make_product()))

    def test_publish_dry_run_never_calls_create_product(self):
        with patch.object(
            payhip_arm_module.payhip_publisher, "load_token", return_value="fake-key"
        ), patch.object(
            payhip_arm_module.payhip_publisher, "create_product"
        ) as mock_create:
            result = self.arm.publish(make_product(), dry_run=True)
            self.assertTrue(result.ok)
            self.assertTrue(result.dry_run)
            mock_create.assert_not_called()

    def test_publish_live_fails_safe_with_honest_unsupported_error(self):
        """The real behavior today (ADR-025): Payhip's public API has no
        product-creation endpoint, so a live attempt must fail with a clear
        message, never crash, never silently claim success."""
        with patch.object(payhip_arm_module.payhip_publisher, "load_token", return_value="fake-key"):
            result = self.arm.publish(make_product(), dry_run=False)
            self.assertFalse(result.ok)
            self.assertFalse(result.dry_run)
            self.assertIn("does not support creating products", result.error)

    def test_publish_unavailable_without_token_never_touches_create_product(self):
        with patch.object(
            payhip_arm_module.payhip_publisher, "load_token",
            side_effect=payhip_arm_module.payhip_publisher.ConfigError("no token"),
        ), patch.object(
            payhip_arm_module.payhip_publisher, "create_product"
        ) as mock_create:
            result = self.arm.publish(make_product(), dry_run=False)
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "arm not ready: unavailable")
            mock_create.assert_not_called()


class TestEtsyArm(unittest.TestCase):
    def setUp(self):
        self.arm = EtsyArm()

    def test_status_unavailable_without_credentials(self):
        with patch.object(
            etsy_arm_module.etsy_publisher, "load_credentials",
            side_effect=etsy_arm_module.etsy_publisher.ConfigError("missing"),
        ):
            self.assertEqual(self.arm.status(), ArmStatus.UNAVAILABLE)

    def test_status_ready_with_credentials(self):
        with patch.object(
            etsy_arm_module.etsy_publisher, "load_credentials",
            return_value=("fake-key", "fake-token", "12345"),
        ):
            self.assertEqual(self.arm.status(), ArmStatus.READY)

    def test_supports_rejects_missing_file(self):
        self.assertFalse(self.arm.supports(make_product(file_path="")))

    def test_supports_accepts_valid_product(self):
        self.assertTrue(self.arm.supports(make_product()))

    def test_publish_dry_run_never_calls_create_product(self):
        with patch.object(
            etsy_arm_module.etsy_publisher, "load_credentials",
            return_value=("fake-key", "fake-token", "12345"),
        ), patch.object(
            etsy_arm_module.etsy_publisher, "create_product"
        ) as mock_create:
            result = self.arm.publish(make_product(), dry_run=True)
            self.assertTrue(result.ok)
            self.assertTrue(result.dry_run)
            mock_create.assert_not_called()

    def test_publish_unavailable_without_credentials_never_touches_network(self):
        with patch.object(
            etsy_arm_module.etsy_publisher, "load_credentials",
            side_effect=etsy_arm_module.etsy_publisher.ConfigError("missing"),
        ), patch.object(
            etsy_arm_module.etsy_publisher, "create_product"
        ) as mock_create:
            result = self.arm.publish(make_product(), dry_run=False)
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "arm not ready: unavailable")
            mock_create.assert_not_called()

    def test_publish_live_success_calls_create_product_once(self):
        with patch.object(
            etsy_arm_module.etsy_publisher, "load_credentials",
            return_value=("fake-key", "fake-token", "12345"),
        ), patch.object(
            etsy_arm_module.etsy_publisher, "create_product",
            return_value={"listing_id": 999, "url": "https://etsy.com/listing/999"},
        ) as mock_create:
            result = self.arm.publish(make_product(), dry_run=False)
            self.assertTrue(result.ok)
            self.assertFalse(result.dry_run)
            self.assertEqual(result.product_id, 999)
            mock_create.assert_called_once()

    def test_circuit_breaker_opens_after_repeated_failures(self):
        with patch.object(
            etsy_arm_module.etsy_publisher, "load_credentials",
            return_value=("fake-key", "fake-token", "12345"),
        ), patch.object(
            etsy_arm_module.etsy_publisher, "create_product",
            side_effect=RuntimeError("simulated failure"),
        ):
            for _ in range(3):
                result = self.arm.publish(make_product(), dry_run=False)
                self.assertFalse(result.ok)
            self.assertEqual(self.arm.status(), ArmStatus.COOLDOWN)


if __name__ == "__main__":
    unittest.main()
