"""freelancer_monitor.py: no false churn, bounded run time (2026-10-22).

The loop killed this script after 60 s 150 times (network outages), and 315
of 325 logged "changes" were UNTRACKED/NEW_TRACKED churn from failed fetches.
Network calls are mocked; files go to a temp dir.

    python -m pytest tests/test_freelancer_monitor_budget.py -q
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import freelancer_api  # noqa: E402
import freelancer_monitor as fm  # noqa: E402

OPEN = {"status": "active", "sub_status": None, "frontend_project_status": "open", "bid_stats": {"bid_count": 3}}


class TestMerge(unittest.TestCase):
    def test_failed_fetch_is_neither_untracked_nor_new(self):
        old = {"1": {"status": "active", "sub_status": None, "frontend_status": "open"}}
        obs, kept = fm.merge_observations(old, {"1": {"error": "ConnectionError"}}, [1])
        self.assertEqual(fm.detect_changes(obs["old"], obs["new"]), [])
        self.assertEqual(kept["1"], old["1"])

    def test_project_removed_from_pipeline_is_untracked(self):
        old = {"1": {"status": "active"}, "2": {"status": "active"}}
        obs, kept = fm.merge_observations(old, {"1": {"status": "active"}}, [1])
        events = fm.detect_changes(obs["old"], obs["new"])
        self.assertEqual([e["event"] for e in events], ["UNTRACKED"])
        self.assertNotIn("2", kept)

    def test_real_status_change_still_reported(self):
        old = {"1": {"status": "active", "sub_status": None, "frontend_status": "open"}}
        new = {"1": {"status": "closed", "sub_status": "awarded", "frontend_status": "closed"}}
        obs, _ = fm.merge_observations(old, new, [1])
        kinds = {e["event"] for e in fm.detect_changes(obs["old"], obs["new"])}
        self.assertEqual(kinds, {"STATUS_CHANGE", "FRONTEND_CHANGE"})


class TestRun(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.d = Path(d.name)
        pipe = self.d / "pipe.json"
        pipe.write_text(json.dumps({"active": [{"id": i} for i in range(1, 10)], "held": []}), encoding="utf-8")
        self.base = self.d / "base.json"
        self.base.write_text(json.dumps({"projects": {str(i): {"status": "active", "sub_status": None,
                                                               "frontend_status": "open", "bid_count": 3}
                                                      for i in range(1, 10)}}), encoding="utf-8")
        for k, v in (("PIPELINE_PATH", str(pipe)), ("BASELINE_PATH", str(self.base))):
            p = patch.object(fm, k, v)
            p.start()
            self.addCleanup(p.stop)

    def run_main(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            fm.main()
        return json.loads(buf.getvalue().strip().splitlines()[-1])

    def test_outage_stops_after_first_failure_and_reports_nothing_false(self):
        with patch.object(freelancer_api, "get_project", side_effect=ConnectionError("dns")) as gp:
            out = self.run_main()
        self.assertEqual(gp.call_count, 1)
        self.assertEqual(out["changes"], [])
        self.assertEqual(out["checked"], 0)
        self.assertEqual(out["not_checked"], 9)
        self.assertEqual(len(json.loads(self.base.read_text(encoding="utf-8"))["projects"]), 9)

    def test_each_call_uses_the_short_timeout(self):
        with patch.object(freelancer_api, "get_project", return_value=OPEN) as gp:
            out = self.run_main()
        self.assertEqual(out["checked"], 9)
        self.assertTrue(all(c.kwargs.get("timeout") == fm.PER_CALL_TIMEOUT for c in gp.call_args_list))

    def test_time_budget_skips_the_rest(self):
        clock = iter([0, 0] + [fm.BUDGET_SECONDS + 1] * 50)  # start, first check, then over budget
        with patch.object(fm.time, "monotonic", side_effect=lambda: next(clock)), \
             patch.object(freelancer_api, "get_project", return_value=OPEN) as gp:
            out = self.run_main()
        self.assertEqual(gp.call_count, 1)
        self.assertEqual(out["changes"], [])

    def test_api_level_error_does_not_stop_the_pass(self):
        err = freelancer_api.FreelancerAPIError("GET -> HTTP 404")
        with patch.object(freelancer_api, "get_project", side_effect=[err] + [OPEN] * 8):
            out = self.run_main()
        self.assertEqual(out["checked"], 8)
        self.assertEqual(out["changes"], [])


if __name__ == "__main__":
    unittest.main()
