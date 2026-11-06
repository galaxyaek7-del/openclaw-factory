import json, os, sys, tempfile, unittest
from datetime import datetime, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import research_chain_daily as r

NOW = datetime(2026, 11, 6, 10, tzinfo=timezone.utc)
OK = json.dumps({"status": "completed", "trends_used": 3, "brief": {"title": "Break-Even Calculator", "price": 29}, "qa": {"verdict": "PASS"}})


class T(unittest.TestCase):
    def setUp(self):
        self.p = os.path.join(tempfile.mkdtemp(), "s.json")

    def test_success_runs_once_a_day(self):
        calls = []
        a = r.run_once(NOW, self.p, runner=lambda: calls.append(1) or OK)
        b = r.run_once(NOW, self.p, runner=lambda: calls.append(1) or OK)
        self.assertEqual(a["action"], "ran")
        self.assertEqual(b["action"], "none")
        self.assertEqual(len(calls), 1)

    def test_failure_retries_then_stops(self):
        n = []
        for _ in range(5):
            r.run_once(NOW, self.p, runner=lambda: n.append(1) or "garbage")
        self.assertEqual(len(n), r.MAX_ATTEMPTS)

    def test_runner_exception_is_reported_not_thrown(self):
        def boom():
            raise RuntimeError("x")
        self.assertEqual(r.run_once(NOW, self.p, runner=boom)["action"], "failed")

    def test_new_day_runs_again(self):
        r.run_once(NOW, self.p, runner=lambda: OK)
        nxt = datetime(2026, 11, 7, 1, tzinfo=timezone.utc)
        self.assertEqual(r.run_once(nxt, self.p, runner=lambda: OK)["action"], "ran")


if __name__ == "__main__":
    unittest.main()
