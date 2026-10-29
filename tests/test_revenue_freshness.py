"""Revenue freshness: a successful zero-sale poll keeps the revenue figure current.

finance_data.json is only rewritten when a sale arrives, so with no sales it
aged past the 24 h budget and revenue_truth reported STALE every day even though
the factory loop polled Gumroad every cycle (observed 2026-10-29: 5.6 days old).
These tests pin the repair and its limits: only an arm read without error
inside the budget confirms the figure; errors, backoff and old polls never do.
"""
import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import revenue_truth  # noqa: E402
import poll_sales  # noqa: E402

NOW = datetime.datetime(2026, 10, 29, 12, 0, tzinfo=datetime.timezone.utc)
OLD = (NOW - datetime.timedelta(days=5)).isoformat()


class RevenueFreshness(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.finance = self.dir / "finance_data.json"
        self.finance.write_text(json.dumps({"sales": [], "lastUpdated": OLD}), encoding="utf-8")
        self.poll = self.dir / "poll.json"

    def read(self):
        return revenue_truth.read_revenue_state(finance_path=self.finance, now=NOW,
                                                poll_state_path=self.poll)

    def write_poll(self, arms, not_checked=()):
        self.poll.write_text(json.dumps({"arms": arms, "not_checked_last_poll": list(not_checked)}),
                             encoding="utf-8")

    def test_old_record_without_poll_record_is_stale(self):
        r = self.read()
        self.assertEqual("STALE", r["status"])
        self.assertIsNone(r["confirmed_by_poll"])

    def test_recent_successful_poll_confirms_the_zero(self):
        self.write_poll({"gumroad": {"last_ok_at": (NOW - datetime.timedelta(minutes=9)).isoformat()}},
                        not_checked=["paddle"])
        r = self.read()
        self.assertEqual("PASS", r["status"])
        self.assertEqual(0.0, r["gross_usd"])
        self.assertEqual(["gumroad"], r["confirmed_by_poll"]["arms_ok"])
        self.assertIn("not checked on the last poll: paddle", r["note"])

    def test_poll_older_than_budget_does_not_confirm(self):
        self.write_poll({"gumroad": {"last_ok_at": (NOW - datetime.timedelta(days=2)).isoformat()}})
        self.assertEqual("STALE", self.read()["status"])

    def test_unreadable_poll_record_does_not_confirm(self):
        self.poll.write_text("{not json", encoding="utf-8")
        self.assertEqual("STALE", self.read()["status"])

    def test_poll_never_changes_the_amount(self):
        self.finance.write_text(json.dumps({"sales": [{"amount": 12.5}], "lastUpdated": OLD}), encoding="utf-8")
        self.write_poll({"gumroad": {"last_ok_at": NOW.isoformat()}})
        self.assertEqual(12.5, self.read()["gross_usd"])


class PollWritesCheckState(unittest.TestCase):
    def test_only_arms_read_without_error_are_recorded_ok(self):
        d = Path(tempfile.mkdtemp())
        ledger = d / "ledger.jsonl"
        outcomes = [
            {"arm": "gumroad", "checked": True, "error": None, "new_sales": 0},
            {"arm": "paddle", "checked": False, "error": None, "skip_reason": "auth backoff", "new_sales": 0},
            {"arm": "etsy", "checked": True, "error": "HTTP 500", "new_sales": 0},
        ]
        poll_sales._write_check_state(outcomes, NOW.timestamp(), ledger)
        state = json.loads((d / "ledger.jsonl.last_check.json").read_text(encoding="utf-8"))
        self.assertEqual(["gumroad"], sorted(state["arms"]))
        self.assertEqual(["etsy", "paddle"], state["not_checked_last_poll"])

    def test_a_later_failed_poll_keeps_the_earlier_success_time(self):
        d = Path(tempfile.mkdtemp())
        ledger = d / "ledger.jsonl"
        poll_sales._write_check_state([{"arm": "gumroad", "checked": True, "error": None}], NOW.timestamp(), ledger)
        later = NOW.timestamp() + 600
        poll_sales._write_check_state([{"arm": "gumroad", "checked": True, "error": "timeout"}], later, ledger)
        state = json.loads((d / "ledger.jsonl.last_check.json").read_text(encoding="utf-8"))
        self.assertEqual(NOW.isoformat(), datetime.datetime.fromisoformat(state["arms"]["gumroad"]["last_ok_at"]).isoformat())
        self.assertEqual(["gumroad"], state["not_checked_last_poll"])

    def test_poll_with_custom_ledger_never_touches_the_real_state_file(self):
        real = ROOT / "data" / "sales_poll_last_check.json"
        before = real.read_bytes() if real.exists() else None
        d = Path(tempfile.mkdtemp())
        with mock.patch.object(poll_sales.registry, "all_arms", return_value=[]):
            poll_sales.poll_sales(ledger_path=d / "ledger.jsonl", now=NOW.timestamp())
        after = real.read_bytes() if real.exists() else None
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
