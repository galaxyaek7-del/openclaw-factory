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


class TestBiddability(unittest.TestCase):
    def test_kdp_closed_awarded_rejected(self):
        from freelancer_api import biddability

        ok, reason = biddability(
            {"status": "closed", "sub_status": "closed_awarded",
             "frontend_status": "work_in_progress"}
        )
        self.assertFalse(ok)
        self.assertIn("closed_awarded", reason)

    def test_active_open_accepted(self):
        from freelancer_api import biddability

        ok, _ = biddability(
            {"status": "active", "sub_status": None, "frontend_status": "open"}
        )
        self.assertTrue(ok)


class TestSelectPrice(unittest.TestCase):
    def test_market_average_parity(self):
        from freelancer_api import select_price

        price, basis = select_price(
            {"bid_avg": 124.89, "budget_min": 30.0, "budget_max": 250.0}
        )
        self.assertEqual(price, 124.89)
        self.assertIn("parity", basis)

    def test_midpoint_fallback_out_of_bounds(self):
        from freelancer_api import select_price

        price, _ = select_price(
            {"bid_avg": 9999.0, "budget_min": 30.0, "budget_max": 250.0}
        )
        self.assertGreaterEqual(price, 30.0)
        self.assertLessEqual(price, 250.0)


if __name__ == "__main__":
    unittest.main()
