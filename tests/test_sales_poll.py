"""Tests for scripts/poll_sales.py + GumroadArm.get_sales() (ADR-016).

Runs with stdlib unittest (see tests/test_base_arm.py). No live Gumroad API
call is ever made — gumroad_publisher.load_token/get_sales are patched in
every test.

    python -m unittest tests.test_sales_poll -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import registry
from channels import ledger
from channels import gumroad_arm as gumroad_arm_module
from channels.gumroad_arm import GumroadArm

from scripts import poll_sales as poll_sales_module


class TestGumroadArmGetSales(unittest.TestCase):
    def setUp(self):
        self.arm = GumroadArm()

    def test_get_sales_without_token_is_safe_skip(self):
        with patch.object(
            gumroad_arm_module.gumroad_publisher, "load_token",
            side_effect=gumroad_arm_module.gumroad_publisher.ConfigError("no token"),
        ):
            sales, error = self.arm.get_sales()
            self.assertEqual(sales, [])
            self.assertEqual(error, "arm not ready: unavailable")

    def test_get_sales_with_token_returns_raw_sales(self):
        fake_sales = [{"id": "sale_abc", "price": "999"}]
        with patch.object(
            gumroad_arm_module.gumroad_publisher, "load_token", return_value="fake-token"
        ), patch.object(
            gumroad_arm_module.gumroad_publisher, "get_sales", return_value=fake_sales
        ):
            sales, error = self.arm.get_sales()
            self.assertEqual(sales, fake_sales)
            self.assertIsNone(error)


class TestPollSales(unittest.TestCase):
    def setUp(self):
        registry.clear()
        self.arm = GumroadArm()
        registry.register(self.arm)
        tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        tmp.close()
        self.ledger_path = tmp.name

    def tearDown(self):
        registry.clear()
        Path(self.ledger_path).unlink(missing_ok=True)

    def test_new_sale_is_recorded_to_ledger(self):
        sale = {"id": "sale_1", "product_name": "Test Book", "price": "999"}
        with patch.object(
            gumroad_arm_module.gumroad_publisher, "load_token", return_value="fake-token"
        ), patch.object(
            gumroad_arm_module.gumroad_publisher, "get_sales", return_value=[sale]
        ):
            outcomes, new_sale_details = poll_sales_module.poll_sales(ledger_path=self.ledger_path)

        self.assertEqual(outcomes[0]["arm"], "gumroad")
        self.assertEqual(outcomes[0]["new_sales"], 1)
        events = list(ledger.read_events(event_type="sale", ledger_path=self.ledger_path))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["platform"], "gumroad")
        self.assertEqual(events[0]["raw"]["id"], "sale_1")

    def test_new_sale_details_carries_a_real_extracted_amount(self):
        """ADR-085: new_sale_details is additive -- lets a caller (e.g. a
        direct Telegram notify) report a real dollar figure, not just a
        count. Must never fabricate an amount for an unrecognized shape."""
        sale = {"id": "sale_3", "product_name": "Test Book", "price": "19.99"}
        with patch.object(
            gumroad_arm_module.gumroad_publisher, "load_token", return_value="fake-token"
        ), patch.object(
            gumroad_arm_module.gumroad_publisher, "get_sales", return_value=[sale]
        ):
            outcomes, new_sale_details = poll_sales_module.poll_sales(ledger_path=self.ledger_path)

        self.assertEqual(len(new_sale_details), 1)
        self.assertEqual(new_sale_details[0], {"platform": "gumroad", "amount": 19.99})

    def test_new_sale_details_is_empty_when_nothing_new(self):
        sale = {"id": "sale_4", "product_name": "Test Book", "price": "999"}
        ledger.record_sale("gumroad", sale, ledger_path=self.ledger_path)
        with patch.object(
            gumroad_arm_module.gumroad_publisher, "load_token", return_value="fake-token"
        ), patch.object(
            gumroad_arm_module.gumroad_publisher, "get_sales", return_value=[sale]
        ):
            outcomes, new_sale_details = poll_sales_module.poll_sales(ledger_path=self.ledger_path)

        self.assertEqual(new_sale_details, [])

    def test_already_recorded_sale_is_not_duplicated(self):
        sale = {"id": "sale_2", "product_name": "Test Book", "price": "999"}
        ledger.record_sale("gumroad", sale, ledger_path=self.ledger_path)

        with patch.object(
            gumroad_arm_module.gumroad_publisher, "load_token", return_value="fake-token"
        ), patch.object(
            gumroad_arm_module.gumroad_publisher, "get_sales", return_value=[sale]
        ):
            outcomes, new_sale_details = poll_sales_module.poll_sales(ledger_path=self.ledger_path)

        self.assertEqual(outcomes[0]["new_sales"], 0)
        events = list(ledger.read_events(event_type="sale", ledger_path=self.ledger_path))
        self.assertEqual(len(events), 1)  # still just the one pre-existing event

    def test_missing_token_skips_safely_without_crashing(self):
        with patch.object(
            gumroad_arm_module.gumroad_publisher, "load_token",
            side_effect=gumroad_arm_module.gumroad_publisher.ConfigError("no token"),
        ):
            outcomes, new_sale_details = poll_sales_module.poll_sales(ledger_path=self.ledger_path)

        self.assertEqual(outcomes[0]["new_sales"], 0)
        self.assertEqual(outcomes[0]["error"], "arm not ready: unavailable")
        events = list(ledger.read_events(event_type="sale", ledger_path=self.ledger_path))
        self.assertEqual(events, [])

    def test_arm_without_get_sales_is_reported_as_unsupported(self):
        from channels.base_arm import BaseArm, ArmStatus, PublishResult

        class NoSalesArm(BaseArm):
            name = "no-sales"

            def status(self):
                return ArmStatus.READY

            def supports(self, product):
                return True

            def publish(self, product, dry_run=True):
                return PublishResult(True, self.name, None, None, None, dry_run)

        registry.register(NoSalesArm())
        outcomes, new_sale_details = poll_sales_module.poll_sales(arm_names=["no-sales"], ledger_path=self.ledger_path)
        self.assertEqual(outcomes[0]["skip_reason"], "no get_sales() support")
        self.assertEqual(outcomes[0]["new_sales"], 0)


if __name__ == "__main__":
    unittest.main()
