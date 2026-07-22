"""Tests for channels/telegram_direct.py (ADR-085).

Runs with stdlib unittest. No live Telegram API call is ever made --
requests.post is patched in every test that would otherwise hit the
network.

    python -m unittest tests.test_telegram_direct -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import telegram_direct


def _fake_env(tmp_path, token="test-token", chat_id="12345"):
    env_file = tmp_path / ".env"
    lines = []
    if token is not None:
        lines.append(f"TELEGRAM_BOT_TOKEN={token}")
    if chat_id is not None:
        lines.append(f"OPENCLAW_TELEGRAM_CHAT_ID={chat_id}")
    env_file.write_text("\n".join(lines), encoding="utf-8")
    return env_file


class TestSendTelegramMessage(unittest.TestCase):
    def test_missing_config_is_reported_not_raised(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            env_file = _fake_env(Path(d), token=None, chat_id=None)
            result = telegram_direct.send_telegram_message("hello", env_path=env_file)
        self.assertFalse(result["sent"])
        self.assertIn("not configured", result["error"])

    def test_real_send_success_reports_message_id(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            env_file = _fake_env(Path(d))
            fake_response = MagicMock(ok=True, content=b'{"ok": true, "result": {"message_id": 42}}')
            fake_response.json.return_value = {"ok": True, "result": {"message_id": 42}}
            with patch.object(telegram_direct.requests, "post", return_value=fake_response) as mock_post:
                result = telegram_direct.send_telegram_message("hello", env_path=env_file)
        self.assertTrue(result["sent"])
        self.assertEqual(result["message_id"], 42)
        self.assertIsNone(result["error"])
        # chat_id and text must actually reach Telegram's real payload shape
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["chat_id"], "12345")
        self.assertEqual(kwargs["json"]["text"], "hello")

    def test_telegram_rejection_is_reported_not_raised(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            env_file = _fake_env(Path(d))
            fake_response = MagicMock(ok=False, status_code=400, content=b'{"ok": false, "description": "chat not found"}')
            fake_response.json.return_value = {"ok": False, "description": "chat not found"}
            with patch.object(telegram_direct.requests, "post", return_value=fake_response):
                result = telegram_direct.send_telegram_message("hello", env_path=env_file)
        self.assertFalse(result["sent"])
        self.assertEqual(result["error"], "chat not found")

    def test_network_failure_is_reported_not_raised(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            env_file = _fake_env(Path(d))
            with patch.object(telegram_direct.requests, "post", side_effect=telegram_direct.requests.RequestException("timeout")):
                result = telegram_direct.send_telegram_message("hello", env_path=env_file)
        self.assertFalse(result["sent"])
        self.assertIn("timeout", result["error"])


if __name__ == "__main__":
    unittest.main()
