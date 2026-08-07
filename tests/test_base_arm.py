"""Tests for channels/base_arm.py, channels/registry.py, channels/gumroad_arm.py.

Runs with stdlib unittest (no test framework is configured in this project
yet — see CLAUDE.md). No live Gumroad API call is ever made: the real
gumroad_publisher.create_product is patched out in every test that exercises
a non-dry-run path, and GUMROAD_ACCESS_TOKEN is not required to be set.

    python -m unittest tests.test_base_arm -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels.base_arm import BaseArm, ArmStatus, PublishResult
from channels import registry
from channels import gumroad_arm as gumroad_arm_module
from channels.gumroad_arm import GumroadArm
from schemas.product import Product


def make_product(**overrides):
    defaults = dict(
        title="Test Book",
        subtitle="",
        description="A test product",
        price_usd=9.99,
        file_path=str(_FACTORY_ROOT / "schemas" / "product.py"),  # any real file
        cover_path=None,
        tags=[],
        language="en",
        source_id="test-1",
        raw_price_hint=9.99,
        needs_pricing=False,
        price_source="profit_raw",
        product_type="book",
    )
    defaults.update(overrides)
    return Product(**defaults)


class TestBaseArmContract(unittest.TestCase):
    def test_base_arm_is_not_instantiable(self):
        with self.assertRaises(TypeError):
            BaseArm()

    def test_concrete_arm_satisfies_contract(self):
        class MinimalArm(BaseArm):
            name = "minimal"

            def status(self):
                return ArmStatus.READY

            def supports(self, product):
                return True

            def publish(self, product, dry_run=True):
                return PublishResult(True, self.name, None, None, None, dry_run)

        arm = MinimalArm()
        self.assertEqual(arm.status(), ArmStatus.READY)
        result = arm.publish(make_product(), dry_run=True)
        self.assertTrue(result.ok)
        self.assertTrue(result.dry_run)


class TestRegistry(unittest.TestCase):
    def tearDown(self):
        registry.clear()

    def test_register_and_get(self):
        class DummyArm(BaseArm):
            name = "dummy"

            def status(self):
                return ArmStatus.READY

            def supports(self, product):
                return True

            def publish(self, product, dry_run=True):
                return PublishResult(True, self.name, None, None, None, dry_run)

        registry.register(DummyArm())
        self.assertIsNotNone(registry.get("dummy"))
        self.assertEqual(len(registry.all_arms()), 1)

    def test_get_unknown_returns_none(self):
        self.assertIsNone(registry.get("does-not-exist"))

    def test_clear_empties_registry(self):
        class DummyArm(BaseArm):
            name = "dummy2"

            def status(self):
                return ArmStatus.READY

            def supports(self, product):
                return True

            def publish(self, product, dry_run=True):
                return PublishResult(True, self.name, None, None, None, dry_run)

        registry.register(DummyArm())
        registry.clear()
        self.assertEqual(registry.all_arms(), [])


class TestGumroadArm(unittest.TestCase):
    def setUp(self):
        self.arm = GumroadArm()

    def test_status_unavailable_without_token(self):
        with patch.object(
            gumroad_arm_module.gumroad_publisher,
            "load_token",
            side_effect=gumroad_arm_module.gumroad_publisher.ConfigError("no token"),
        ):
            self.assertEqual(self.arm.status(), ArmStatus.UNAVAILABLE)

    def test_status_ready_with_token(self):
        with patch.object(gumroad_arm_module.gumroad_publisher, "load_token", return_value="fake-token"):
            self.assertEqual(self.arm.status(), ArmStatus.READY)

    def test_supports_rejects_missing_file(self):
        p = make_product(file_path="")
        self.assertFalse(self.arm.supports(p))

    def test_supports_rejects_unresolved_price(self):
        p = make_product(price_usd=None, needs_pricing=True)
        self.assertFalse(self.arm.supports(p))

    def test_supports_accepts_valid_product(self):
        self.assertTrue(self.arm.supports(make_product()))

    def test_publish_unavailable_without_token_never_touches_network(self):
        with patch.object(
            gumroad_arm_module.gumroad_publisher,
            "load_token",
            side_effect=gumroad_arm_module.gumroad_publisher.ConfigError("no token"),
        ), patch.object(
            gumroad_arm_module.gumroad_publisher, "create_product"
        ) as mock_create:
            result = self.arm.publish(make_product(), dry_run=False)
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "arm not ready: unavailable")
            mock_create.assert_not_called()

    def test_publish_dry_run_never_calls_create_product(self):
        with patch.object(
            gumroad_arm_module.gumroad_publisher, "load_token", return_value="fake-token"
        ), patch.object(
            gumroad_arm_module.gumroad_publisher, "create_product"
        ) as mock_create:
            result = self.arm.publish(make_product(), dry_run=True)
            self.assertTrue(result.ok)
            self.assertTrue(result.dry_run)
            mock_create.assert_not_called()

    def test_publish_live_success_calls_create_product_once(self):
        with patch.object(
            gumroad_arm_module.gumroad_publisher, "load_token", return_value="fake-token"
        ), patch.object(
            gumroad_arm_module.gumroad_publisher,
            "create_product",
            return_value={"id": "prod_123", "short_url": "https://gum.co/xyz"},
        ) as mock_create:
            result = self.arm.publish(make_product(), dry_run=False)
            self.assertTrue(result.ok)
            self.assertFalse(result.dry_run)
            self.assertEqual(result.product_id, "prod_123")
            self.assertEqual(result.url, "https://gum.co/xyz")
            mock_create.assert_called_once()

    def test_circuit_breaker_opens_after_repeated_failures(self):
        with patch.object(
            gumroad_arm_module.gumroad_publisher, "load_token", return_value="fake-token"
        ), patch.object(
            gumroad_arm_module.gumroad_publisher,
            "create_product",
            side_effect=RuntimeError("Gumroad create_product failed: simulated"),
        ):
            for _ in range(3):
                result = self.arm.publish(make_product(), dry_run=False)
                self.assertFalse(result.ok)
            self.assertEqual(self.arm.status(), ArmStatus.COOLDOWN)


class TestBaseArmAdditiveMethods(unittest.TestCase):
    """ADR-202 (2026-08-07): the 6 new default-NOT_IMPLEMENTED methods
    (list_products/update_product/verify_product/retrieve_fees/
    retrieve_refunds/retrieve_affiliate_data) plus the real, generic
    health_check() -- never break an arm that doesn't override them."""

    def setUp(self):
        class MinimalArm(BaseArm):
            name = "minimal"

            def status(self):
                return ArmStatus.READY

            def publish(self, product, dry_run=True):
                return PublishResult(True, self.name, None, None, None, dry_run)

        self.arm = MinimalArm()

    def test_list_products_defaults_to_honest_not_implemented(self):
        result = self.arm.list_products()
        self.assertEqual(result["status"], "NOT_IMPLEMENTED")
        self.assertIn("reason", result)

    def test_update_product_defaults_to_honest_not_implemented(self):
        result = self.arm.update_product("some-id", {"title": "x"})
        self.assertEqual(result["status"], "NOT_IMPLEMENTED")

    def test_retrieve_fees_defaults_to_honest_not_implemented(self):
        self.assertEqual(self.arm.retrieve_fees()["status"], "NOT_IMPLEMENTED")

    def test_retrieve_refunds_defaults_to_honest_not_implemented(self):
        self.assertEqual(self.arm.retrieve_refunds()["status"], "NOT_IMPLEMENTED")

    def test_retrieve_affiliate_data_defaults_to_honest_not_implemented(self):
        self.assertEqual(self.arm.retrieve_affiliate_data()["status"], "NOT_IMPLEMENTED")

    def test_verify_product_reports_not_implemented_when_list_products_is(self):
        result = self.arm.verify_product("some-id")
        self.assertEqual(result["status"], "NOT_IMPLEMENTED")

    def test_health_check_reuses_status_never_a_second_network_call(self):
        result = self.arm.health_check()
        self.assertTrue(result["healthy"])
        self.assertEqual(result["status"], "ready")
        self.assertIn("checked_at", result)


class TestGumroadArmAdditiveOverrides(unittest.TestCase):
    def setUp(self):
        self.arm = GumroadArm()

    def test_list_products_not_ready_without_token(self):
        with patch.object(
            gumroad_arm_module.gumroad_publisher,
            "load_token",
            side_effect=gumroad_arm_module.gumroad_publisher.ConfigError("no token"),
        ):
            result = self.arm.list_products()
            self.assertEqual(result["status"], "NOT_READY")

    def test_list_products_real_call_when_ready(self):
        with patch.object(
            gumroad_arm_module.gumroad_publisher, "load_token", return_value="fake-token"
        ), patch.object(
            gumroad_arm_module.gumroad_publisher, "list_products", return_value=[{"id": "p1"}],
        ) as mock_list:
            result = self.arm.list_products()
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["products"], [{"id": "p1"}])
            mock_list.assert_called_once()

    def test_update_product_real_call_when_ready(self):
        with patch.object(
            gumroad_arm_module.gumroad_publisher, "load_token", return_value="fake-token"
        ), patch.object(
            gumroad_arm_module.gumroad_publisher, "update_product", return_value={"id": "p1", "name": "x"},
        ) as mock_update:
            result = self.arm.update_product("p1", {"name": "x"})
            self.assertEqual(result["status"], "OK")
            mock_update.assert_called_once_with("fake-token", "p1", {"name": "x"})


if __name__ == "__main__":
    unittest.main()
