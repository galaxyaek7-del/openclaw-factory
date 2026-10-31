"""scripts/distribution_metrics_daily.py: the once-a-day gate around the
read-only distribution poller. The real poller and the real ledger are never
touched: every case uses a temp ledger and an injected poll."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import distribution_metrics_daily as dmd  # noqa: E402


def write(path, *records):
    with open(path, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


class DailyGate(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ledger = Path(self.dir.name) / "distribution_metrics.jsonl"

    def tearDown(self):
        self.dir.cleanup()

    def test_already_read_today_does_not_poll(self):
        write(self.ledger, {"timestamp": "2026-10-29T08:00:00+00:00", "views": {"a": 1}})
        called = []
        out = dmd.run_once(today="2026-10-29", ledger=self.ledger, poll=lambda: called.append(1))
        self.assertEqual(out["action"], "none")
        self.assertEqual(called, [])

    def test_new_day_polls_and_reports_platform_views_honestly(self):
        write(self.ledger, {"timestamp": "2026-10-09T15:00:00+00:00", "views": {"a": 1}})

        def poll():
            write(self.ledger, {"timestamp": "2026-10-29T16:00:00+00:00",
                                "views": {"a": 22, "b": 20}, "views_status": {"a": "ok", "b": "ok"}})
        out = dmd.run_once(today="2026-10-29", ledger=self.ledger, poll=poll)
        self.assertEqual(out["action"], "recorded")
        self.assertIn("2/2 articles", out["detail"])
        self.assertIn("42 platform-reported views", out["detail"])
        self.assertIn("not verified human visits", out["detail"])

    def test_a_reading_with_no_readable_article_is_retried_hourly(self):
        from datetime import datetime, timezone
        write(self.ledger, {"timestamp": "2026-10-31T00:04:24+00:00", "views": {},
                            "views_status": {"a": "ERROR_URLError", "b": "ERROR_URLError"}})
        called = []

        def poll():
            called.append(1)
            write(self.ledger, {"timestamp": "2026-10-31T01:10:00+00:00",
                                "views": {"a": 3, "b": 4}, "views_status": {"a": "ok", "b": "ok"}})
        soon = dmd.run_once(ledger=self.ledger, poll=poll, now=datetime(2026, 10, 31, 0, 40, tzinfo=timezone.utc))
        self.assertEqual((soon["action"], called), ("none", []))
        later = dmd.run_once(ledger=self.ledger, poll=poll, now=datetime(2026, 10, 31, 1, 10, tzinfo=timezone.utc))
        self.assertEqual(later["action"], "recorded")
        done = dmd.run_once(ledger=self.ledger, poll=poll, now=datetime(2026, 10, 31, 9, tzinfo=timezone.utc))
        self.assertEqual((done["action"], len(called)), ("none", 1))

    def test_poller_that_appends_nothing_is_a_failure(self):
        write(self.ledger, {"timestamp": "2026-10-09T15:00:00+00:00"})
        out = dmd.run_once(today="2026-10-29", ledger=self.ledger, poll=lambda: None)
        self.assertEqual(out["action"], "failed")

    def test_poller_error_is_reported_not_raised(self):
        def boom():
            raise RuntimeError("network down")
        out = dmd.run_once(today="2026-10-29", ledger=self.ledger, poll=boom)
        self.assertEqual(out["action"], "failed")
        self.assertIn("network down", out["detail"])

    def test_without_once_flag_it_does_nothing(self):
        self.assertEqual(dmd.main([]), 2)


if __name__ == "__main__":
    unittest.main()
