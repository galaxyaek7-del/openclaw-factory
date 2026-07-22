"""Tests for scripts/check_paddle_checkout_status.py (ADR-085).

Runs with stdlib unittest. No live Paddle/Telegram API call is ever made
-- paddle_publisher.create_checkout_transaction and
telegram_direct.send_telegram_message are patched in every test.

    python -m unittest tests.test_check_paddle_checkout_status -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import paddle_publisher
from scripts import check_paddle_checkout_status as cpcs


def _temp_state_path():
    fd, path = tempfile.mkstemp(suffix=".json")
    import os
    os.close(fd)
    os.remove(path)  # check_and_notify must handle a not-yet-existing file
    return path


class TestCheckAndNotify(unittest.TestCase):
    def setUp(self):
        self.state_path = _temp_state_path()

    def tearDown(self):
        import os
        if os.path.exists(self.state_path):
            os.remove(self.state_path)

    def test_still_blocked_reports_honestly_no_telegram_send(self):
        # Real, live-confirmed Paddle detail text (2026-07-18/19/22) --
        # _raise_with_paddle_error() prefers `detail` over `code`, so the
        # code string "transaction_checkout_not_enabled" often never
        # appears at all; the detection logic must match this real shape.
        real_detail = (
            "Paddle create_checkout_transaction failed: HTTP 400: Checkout has not yet been "
            "enabled for this account, you may need to check with Paddle Support that the "
            "Paddle onboarding process has completed."
        )
        with patch.object(cpcs.paddle_publisher, "load_api_key", return_value="fake-key"), \
             patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                           side_effect=RuntimeError(real_detail)), \
             patch.object(cpcs.telegram_direct, "send_telegram_message") as mock_send:
            result = cpcs.check_and_notify(state_path=self.state_path)

        self.assertTrue(result["success"])
        self.assertFalse(result["checkout_ready"])
        mock_send.assert_not_called()

    def test_unrelated_paddle_error_is_reported_as_a_real_error_not_swallowed(self):
        with patch.object(cpcs.paddle_publisher, "load_api_key", return_value="fake-key"), \
             patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                           side_effect=RuntimeError("Paddle create_checkout_transaction failed: HTTP 404: price_not_found")), \
             patch.object(cpcs.telegram_direct, "send_telegram_message") as mock_send:
            result = cpcs.check_and_notify(state_path=self.state_path)

        self.assertFalse(result["success"])
        self.assertIn("price_not_found", result["error"])
        mock_send.assert_not_called()

    def test_real_checkout_url_triggers_real_telegram_send(self):
        with patch.object(cpcs.paddle_publisher, "load_api_key", return_value="fake-key"), \
             patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                           return_value=({"id": "txn_123"}, "https://checkout.paddle.com/real-link")), \
             patch.object(cpcs.telegram_direct, "send_telegram_message",
                           return_value={"sent": True, "message_id": 99, "error": None}) as mock_send:
            result = cpcs.check_and_notify(state_path=self.state_path)

        self.assertTrue(result["success"])
        self.assertTrue(result["checkout_ready"])
        self.assertTrue(result["telegram_sent"])
        self.assertEqual(result["checkout_url"], "https://checkout.paddle.com/real-link")
        mock_send.assert_called_once()
        sent_text = mock_send.call_args[0][0]
        self.assertIn("https://checkout.paddle.com/real-link", sent_text)
        self.assertIn("388", sent_text)

    def test_second_run_after_real_send_is_idempotent_never_resends(self):
        with patch.object(cpcs.paddle_publisher, "load_api_key", return_value="fake-key"), \
             patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                           return_value=({"id": "txn_123"}, "https://checkout.paddle.com/real-link")), \
             patch.object(cpcs.telegram_direct, "send_telegram_message",
                           return_value={"sent": True, "message_id": 99, "error": None}):
            cpcs.check_and_notify(state_path=self.state_path)

        with patch.object(cpcs.paddle_publisher, "create_checkout_transaction") as mock_create, \
             patch.object(cpcs.telegram_direct, "send_telegram_message") as mock_send:
            result = cpcs.check_and_notify(state_path=self.state_path)

        self.assertTrue(result["already_notified"])
        mock_create.assert_not_called()  # never even re-hits Paddle once already notified
        mock_send.assert_not_called()

    def test_missing_api_key_is_reported_not_raised(self):
        with patch.object(cpcs.paddle_publisher, "load_api_key",
                           side_effect=paddle_publisher.ConfigError("PADDLE_API_KEY not set")):
            result = cpcs.check_and_notify(state_path=self.state_path)
        self.assertFalse(result["success"])
        self.assertIn("PADDLE_API_KEY", result["error"])

    def test_telegram_send_failure_is_recorded_but_still_reported_as_checkout_ready(self):
        """The real, valuable fact (a checkout link now exists) must never
        be lost just because the Telegram send itself failed."""
        with patch.object(cpcs.paddle_publisher, "load_api_key", return_value="fake-key"), \
             patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                           return_value=({"id": "txn_123"}, "https://checkout.paddle.com/real-link")), \
             patch.object(cpcs.telegram_direct, "send_telegram_message",
                           return_value={"sent": False, "message_id": None, "error": "bot blocked"}):
            result = cpcs.check_and_notify(state_path=self.state_path)

        self.assertTrue(result["checkout_ready"])
        self.assertFalse(result["telegram_sent"])
        self.assertEqual(result["telegram_error"], "bot blocked")

        # A failed Telegram send must not be treated as "already notified" --
        # a later retry should try sending again, not silently skip forever.
        with open(self.state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.assertFalse(state[cpcs.KNOWN_PRICE_ID]["notified"])


if __name__ == "__main__":
    unittest.main()
