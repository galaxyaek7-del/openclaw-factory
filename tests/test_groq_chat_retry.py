"""Tests for book_generator.py::groq_chat()'s real retry/backoff logic
(the one, shared, load-bearing entrypoint every real AI-generation call
in this factory ultimately depends on, directly or via ai_capability.
orchestrator.generate()) -- specifically _retry_delay_seconds(), the
real Retry-After-aware backoff fix (2026-08-06) added after a real HTTP
429 was observed live this session. No prior test exercised groq_chat()'s
own retry mechanics at all before this file (confirmed by direct repo
search) -- a real, previously-uncovered gap in a critical shared path.

    python -m unittest tests.test_groq_chat_retry -v
"""

import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import book_generator as bg


def _http_error(code, headers=None):
    return urllib.error.HTTPError(
        url="https://api.groq.com/x", code=code, msg="test",
        hdrs=headers or {}, fp=None,
    )


class TestRetryDelaySeconds(unittest.TestCase):
    def test_default_exponential_backoff_when_no_retry_after_header(self):
        err = _http_error(429)
        self.assertEqual(bg._retry_delay_seconds(1, err), 1)
        self.assertEqual(bg._retry_delay_seconds(2, err), 2)
        self.assertEqual(bg._retry_delay_seconds(3, err), 4)

    def test_respects_a_real_numeric_retry_after_header_on_429(self):
        err = _http_error(429, headers={"Retry-After": "7"})
        self.assertEqual(bg._retry_delay_seconds(1, err), 7.0)

    def test_respects_retry_after_on_503_too(self):
        err = _http_error(503, headers={"Retry-After": "3"})
        self.assertEqual(bg._retry_delay_seconds(1, err), 3.0)

    def test_retry_after_is_capped_never_hangs_indefinitely(self):
        err = _http_error(429, headers={"Retry-After": "99999"})
        self.assertEqual(bg._retry_delay_seconds(1, err), bg._MAX_RETRY_AFTER_SECONDS)

    def test_non_numeric_retry_after_falls_back_to_exponential(self):
        """An HTTP-date-style Retry-After (a real, valid alternative per
        RFC 7231) is honestly not parsed here -- falls back safely
        rather than crashing or misbehaving."""
        err = _http_error(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"})
        self.assertEqual(bg._retry_delay_seconds(2, err), 2)

    def test_non_rate_limit_http_error_ignores_retry_after_header(self):
        """A 500 with a stray Retry-After header still uses exponential
        backoff -- the header is only meaningful for 429/503."""
        err = _http_error(500, headers={"Retry-After": "7"})
        self.assertEqual(bg._retry_delay_seconds(1, err), 1)

    def test_non_http_error_falls_back_to_exponential(self):
        self.assertEqual(bg._retry_delay_seconds(1, TimeoutError("x")), 1)
        self.assertEqual(bg._retry_delay_seconds(1, None), 1)


class TestGroqChatReasoningFallback(unittest.TestCase):
    """openai/gpt-oss-20b is a reasoning model: when max_tokens is tight
    it fills message.reasoning and leaves message.content empty
    (finish_reason="length"). Fix found live 2026-08-14 (revenue cycle):
    groq_chat() returns the real reasoning text instead of silently
    returning "" -- never fabricated, strictly better than the broken
    empty state that degraded pain-query reformulation factory-wide."""

    @patch("book_generator.get_groq_key", return_value="fake-key")
    @patch("book_generator.urllib.request.urlopen")
    def test_empty_content_returns_real_reasoning_text(self, mock_urlopen, mock_key):
        resp = MagicMock()
        resp.read.return_value = b'{"choices":[{"message":{"content":"","reasoning":"manual cloud ops lead to frequent errors and downtime"}}],"usage":{}}'
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        mock_urlopen.return_value = resp

        result = bg.groq_chat("sys", "user")
        self.assertEqual(result, "manual cloud ops lead to frequent errors and downtime")

    @patch("book_generator.get_groq_key", return_value="fake-key")
    @patch("book_generator.urllib.request.urlopen")
    def test_content_present_wins_over_reasoning(self, mock_urlopen, mock_key):
        resp = MagicMock()
        resp.read.return_value = b'{"choices":[{"message":{"content":"SOC 2 paperwork overwhelms small teams","reasoning":"thinking text"}}],"usage":{}}'
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        mock_urlopen.return_value = resp

        result = bg.groq_chat("sys", "user")
        self.assertEqual(result, "SOC 2 paperwork overwhelms small teams")

    @patch("book_generator.get_groq_key", return_value="fake-key")
    @patch("book_generator.urllib.request.urlopen")
    def test_empty_content_and_no_reasoning_still_returns_empty_string(self, mock_urlopen, mock_key):
        resp = MagicMock()
        resp.read.return_value = b'{"choices":[{"message":{"content":""}}],"usage":{}}'
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        mock_urlopen.return_value = resp

        self.assertEqual(bg.groq_chat("sys", "user"), "")


class TestGroqChatRetryIntegration(unittest.TestCase):
    """Confirms groq_chat() itself actually calls the real delay
    function during its retry loop -- not just that the helper computes
    the right number in isolation."""

    @patch("book_generator.get_groq_key", return_value="fake-key")
    @patch("book_generator.time.sleep")
    @patch("book_generator.urllib.request.urlopen")
    def test_real_429_with_retry_after_uses_the_real_header_value(self, mock_urlopen, mock_sleep, mock_key):
        err = _http_error(429, headers={"Retry-After": "5"})
        success_response = MagicMock()
        success_response.read.return_value = b'{"choices":[{"message":{"content":"ok"}}],"usage":{}}'
        success_response.__enter__ = lambda s: s
        success_response.__exit__ = lambda s, *a: None
        mock_urlopen.side_effect = [err, success_response]

        result = bg.groq_chat("sys", "user", retries=3)
        self.assertEqual(result, "ok")
        mock_sleep.assert_called_once_with(5.0)

    @patch("book_generator.get_groq_key", return_value="fake-key")
    @patch("book_generator.time.sleep")
    @patch("book_generator.urllib.request.urlopen")
    def test_auth_error_never_retries_never_sleeps(self, mock_urlopen, mock_sleep, mock_key):
        mock_urlopen.side_effect = _http_error(401)
        with self.assertRaises(RuntimeError):
            bg.groq_chat("sys", "user", retries=3)
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
