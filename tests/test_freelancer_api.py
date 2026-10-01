"""Regression guard for the delegation safety property:
- place_bid without a token MUST raise FounderAuthorizationRequired (never submit, never prompt).
- is_open() classification logic on synthetic summaries (no network).
"""
import unittest

from freelancer_api import (
    FounderAuthorizationRequired,
    is_open,
    place_bid,
)


class TestFailClosed(unittest.TestCase):
    def test_place_bid_without_token_raises(self):
        with self.assertRaises(FounderAuthorizationRequired):
            place_bid(40742370, 100, "test proposal")

    def test_place_bid_empty_token_raises(self):
        with self.assertRaises(FounderAuthorizationRequired):
            place_bid(40742370, 100, "test proposal", token="")

    def test_error_mentions_onetime_grant_and_no_plaintext(self):
        try:
            place_bid(40742370, 100, "test")
        except FounderAuthorizationRequired as e:
            msg = str(e).lower()
            self.assertIn("one-time", msg)
            self.assertIn(".env", msg)
            self.assertIn("never", msg)
        else:
            self.fail("did not raise")


class TestIsOpen(unittest.TestCase):
    def test_active_open(self):
        self.assertTrue(is_open({"status": "active", "frontend_status": "open"}))

    def test_closed_awarded_is_not_open(self):
        self.assertFalse(
            is_open({"status": "closed", "frontend_status": "work_in_progress"})
        )

    def test_active_unknown_frontend_defaults_open(self):
        self.assertTrue(is_open({"status": "active", "frontend_status": None}))


if __name__ == "__main__":
    unittest.main()
