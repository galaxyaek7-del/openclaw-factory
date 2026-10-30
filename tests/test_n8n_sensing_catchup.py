"""scripts/n8n_sensing_catchup.py -- bounded catch-up of a lost daily run.

Injected health/DNS/trigger only; nothing touches n8n or the network.

    python -m pytest tests/test_n8n_sensing_catchup.py -q
"""
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import n8n_sensing_catchup as nc  # noqa: E402

NOW = datetime(2026, 10, 23, 7, 45, tzinfo=timezone.utc)
FAILED_TODAY = {"last_status": "error", "last_started_at": "2026-10-23 07:00:08.098",
                "last_success_at": "2026-10-22 15:46:50.427",
                "last_error": "The connection cannot be established ... getaddrinfo ENOTFOUND trends.google.com"}


def health(w):
    return {"workflows": {nc.WORKFLOW: w}}


class TestDecide(unittest.TestCase):
    def test_network_failure_today_with_network_back_triggers(self):
        self.assertTrue(nc.decide(FAILED_TODAY, "2026-10-23", 0, True, True)[0])

    def test_no_trigger_cases(self):
        cases = {
            "succeeded today": dict(FAILED_TODAY, last_success_at="2026-10-23 09:00:00"),
            "failure was yesterday": dict(FAILED_TODAY, last_started_at="2026-10-22 07:00:00"),
            "not a network error": dict(FAILED_TODAY, last_error="Cannot read properties of undefined"),
        }
        for label, w in cases.items():
            self.assertFalse(nc.decide(w, "2026-10-23", 0, True, True)[0], label)
        self.assertFalse(nc.decide(FAILED_TODAY, "2026-10-23", 0, False, True)[0], "network still down")
        self.assertFalse(nc.decide(FAILED_TODAY, "2026-10-23", 2, True, True)[0], "daily limit")
        self.assertFalse(nc.decide(FAILED_TODAY, "2026-10-23", 0, True, False)[0], "no secret")
        self.assertFalse(nc.decide(None, "2026-10-23", 0, True, True)[0], "unknown state")


class TestRunOnce(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.state = Path(d.name) / "state.json"
        self.calls = []

    def trigger(self, url, secret):
        self.calls.append((url, secret))
        return 200

    def run_(self, w=FAILED_TODAY, dns=True):
        return nc.run_once(now=NOW, state_path=self.state, health=health(w), dns_ok=dns,
                           secret="s3cret", trigger=self.trigger)

    def test_a_recorded_success_skips_the_n8n_read_for_the_rest_of_the_day(self):
        ok = {"last_status": "success", "last_started_at": "2026-10-23 07:00:01",
              "last_success_at": "2026-10-23 07:00:05"}
        self.assertEqual(self.run_(ok)["detail"], "already succeeded today")
        # same day: health must not be read again (a None report would raise)
        out = nc.run_once(now=NOW, state_path=self.state, health=None, dns_ok=True, secret="s3cret",
                          trigger=self.trigger)
        self.assertEqual(out, {"action": "none", "detail": "already succeeded today (recorded)"})
        # next day: the record no longer applies and a failed run is retried
        nxt = nc.run_once(now=NOW.replace(day=24), state_path=self.state,
                          health=health(dict(FAILED_TODAY, last_started_at="2026-10-24 07:00:01")),
                          dns_ok=True, secret="s3cret", trigger=self.trigger)
        self.assertEqual(nxt["action"], "triggered", nxt)
        self.assertEqual(len(self.calls), 1)

    def test_triggers_at_most_twice_a_day(self):
        outs = [self.run_()["action"] for _ in range(4)]
        self.assertEqual(outs, ["triggered", "triggered", "none", "none"])
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0][0], nc.WEBHOOK_URL)

    def test_secret_never_in_output(self):
        out = self.run_()
        self.assertNotIn("s3cret", str(out))

    def test_waits_while_network_is_down(self):
        self.assertEqual(self.run_(dns=False)["action"], "none")
        self.assertEqual(self.calls, [])

    def test_trigger_failure_is_reported_and_counted(self):
        def boom(url, secret):
            raise OSError("refused")
        out = nc.run_once(now=NOW, state_path=self.state, health=health(FAILED_TODAY), dns_ok=True,
                          secret="s3cret", trigger=boom)
        self.assertEqual(out["action"], "failed")
        self.assertNotIn("s3cret", str(out))


if __name__ == "__main__":
    unittest.main()


class TestMissedRun(unittest.TestCase):
    """2026-10-29: n8n was down at the scheduled hour and the day's run never started."""

    NEVER_STARTED = {"last_status": "success", "last_started_at": "2026-10-25 07:00:08.156",
                     "last_success_at": "2026-10-25 07:00:08.156"}

    def test_missed_run_triggers_after_the_grace_hour(self):
        ok, why = nc.decide(self.NEVER_STARTED, "2026-10-29", 0, True, True, now_hour=11)
        self.assertTrue(ok)
        self.assertIn("never started", why)

    def test_not_before_the_schedule_has_passed(self):
        self.assertFalse(nc.decide(self.NEVER_STARTED, "2026-10-29", 0, True, True, now_hour=7)[0])

    def test_same_limits_apply(self):
        for args, label in (((0, False, True), "network down"), ((2, True, True), "daily limit"),
                            ((0, True, False), "no secret")):
            self.assertFalse(nc.decide(self.NEVER_STARTED, "2026-10-29", *args, now_hour=11)[0], label)

    def test_already_succeeded_today_never_triggers(self):
        w = {"last_status": "success", "last_started_at": "2026-10-29 07:00:01", "last_success_at": "2026-10-29 07:00:05"}
        self.assertFalse(nc.decide(w, "2026-10-29", 0, True, True, now_hour=11)[0])

    def test_old_callers_without_now_hour_keep_the_original_rule(self):
        self.assertFalse(nc.decide(self.NEVER_STARTED, "2026-10-29", 0, True, True)[0])

    def test_run_once_uses_the_current_hour(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        calls = []
        out = nc.run_once(now=datetime(2026, 10, 29, 11, 5, tzinfo=timezone.utc), state_path=Path(d.name) / "s.json",
                          health=health(self.NEVER_STARTED), dns_ok=True, secret="s3cret",
                          trigger=lambda url, secret: calls.append(url) or 200)
        self.assertEqual("triggered", out["action"])
        self.assertEqual(1, len(calls))
