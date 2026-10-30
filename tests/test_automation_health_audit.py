"""services/automation_health/audit.py: the customer-safe n8n audit judges
status and timing only, and never calls a workflow OK without evidence."""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "automation_health"))
import audit  # noqa: E402

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)


def wf(i, name, active=True):
    return {"id": i, "name": name, "active": active}


class Audit(unittest.TestCase):
    def verdict(self, executions, expected, active=True):
        out = audit.assess([wf("1", "W", active)], executions, expected, NOW)
        return out["workflows"][0]

    def test_no_runs_is_unknown_not_ok(self):
        self.assertEqual(self.verdict([], {"W": 60})["verdict"], "UNKNOWN")

    def test_latest_error_is_failing_even_after_earlier_successes(self):
        runs = [{"workflowId": "1", "status": "success", "startedAt": "2026-10-29T11:00:00Z"},
                {"workflowId": "1", "status": "error", "startedAt": "2026-10-29T11:50:00Z"}]
        self.assertEqual(self.verdict(runs, {"W": 60})["verdict"], "FAILING")

    def test_old_success_is_stale(self):
        runs = [{"workflowId": "1", "status": "success", "startedAt": "2026-10-29T08:00:00Z"}]
        self.assertEqual(self.verdict(runs, {"W": 60})["verdict"], "STALE")
        self.assertEqual(self.verdict(runs, {"W": 240})["verdict"], "OK")

    def test_undeclared_schedule_cannot_be_ok(self):
        runs = [{"workflowId": "1", "status": "success", "startedAt": "2026-10-29T11:59:00Z"}]
        self.assertEqual(self.verdict(runs, {})["verdict"], "UNKNOWN")

    def test_manual_workflow_with_a_success_is_ok(self):
        runs = [{"workflowId": "1", "status": "success", "startedAt": "2026-10-01T00:00:00Z"}]
        self.assertEqual(self.verdict(runs, {"W": None})["verdict"], "OK")

    def test_inactive_is_reported_not_judged(self):
        self.assertEqual(self.verdict([], {"W": 60}, active=False)["verdict"], "INACTIVE")

    def test_demo_input_reproduces_the_documented_result(self):
        doc = json.load(open(ROOT / "services" / "automation_health" / "demo_input.json", encoding="utf-8"))
        out = audit.assess(doc["workflows"], doc["executions"], doc["expected_minutes"],
                           audit._ts(doc["now"]))
        self.assertEqual(out["counts"], {"OK": 2, "STALE": 1, "FAILING": 1, "INACTIVE": 1, "UNKNOWN": 1})

    def test_raw_api_exports_are_read_and_payloads_dropped(self):
        wdoc = {"data": [{"id": "7", "name": "Sync", "active": True, "nodes": [{"x": 1}]}], "nextCursor": None}
        epages = [{"data": [{"id": "1", "workflowId": "7", "status": "error", "startedAt": "2026-10-29T10:00:00Z",
                             "data": {"resultData": {"customer": "secret"}}}], "nextCursor": "c"},
                  {"data": [{"id": "2", "workflowId": "7", "finished": True, "startedAt": "2026-10-29T09:00:00Z"},
                            {"id": "3", "workflowId": "7", "startedAt": "2026-10-29T08:00:00Z"}]}]
        wfs, exes, notes = audit.from_api_exports(wdoc, epages)
        self.assertEqual(wfs, [{"id": "7", "name": "Sync", "active": True}])
        self.assertEqual([e["status"] for e in exes], ["error", "success", "unknown"])
        self.assertNotIn("secret", json.dumps(exes))
        self.assertIn("1 execution(s) carried payload data", notes[0])
        out = audit.assess(wfs, exes, {"Sync": 60}, audit._ts("2026-10-29T10:05:00Z"))
        self.assertEqual(out["workflows"][0]["verdict"], "FAILING")
        self.assertEqual(audit.from_api_exports([{"id": "9", "name": "B", "active": False}], [])[0][0]["name"], "B")

    def test_the_audit_reads_no_database_and_writes_nothing(self):
        src = (ROOT / "services" / "automation_health" / "audit.py").read_text(encoding="utf-8")
        for forbidden in ("sqlite3", "database.sqlite", "requests.post", "urlopen("):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
