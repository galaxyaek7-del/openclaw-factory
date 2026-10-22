"""Tests for scripts/n8n_workflow_health.py against a synthetic n8n database.

No live n8n, no network: each test builds a throwaway SQLite file with the
three tables the tool reads and execution data in n8n's flatted encoding.

    python -m pytest tests/test_n8n_workflow_health.py -q
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import n8n_workflow_health as h  # noqa: E402

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
NODE = "Poll Sales (server.js Brain)"
TARGETS = {"02_Sales_Poll": (timedelta(hours=4), NODE),
           "01_Market_Scout": (None, "HTTP Request")}


def flatted(obj):
    arr = []

    def add(v):
        if isinstance(v, (dict, list, str)):
            idx = len(arr)
            arr.append(None)
            if isinstance(v, dict):
                arr[idx] = {k: add(x) for k, x in v.items()}
            elif isinstance(v, list):
                arr[idx] = [add(x) for x in v]
            else:
                arr[idx] = v
            return str(idx)
        return v

    add(obj)
    return json.dumps(arr)


def success_data(payload):
    return flatted({"resultData": {"runData": {NODE: [{"data": {"main": [[{"json": payload}]]}}]}}})


def error_data(message):
    return flatted({"resultData": {"error": {"message": message}, "runData": {}}})


class _DB(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.db = Path(self._dir.name) / "database.sqlite"
        con = sqlite3.connect(self.db)
        con.executescript("""
            create table workflow_entity (id text, name text, active integer);
            create table execution_entity (id integer, workflowId text, status text, startedAt text);
            create table execution_data (executionId integer, data text);
        """)
        con.execute("insert into workflow_entity values ('w1','02_Sales_Poll',1)")
        con.execute("insert into workflow_entity values ('w3','01_Market_Scout',1)")
        con.commit()
        con.close()
        self._next = 1

    def run_(self, status, hours_ago, data):
        con = sqlite3.connect(self.db)
        ts = (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S.000")
        con.execute("insert into execution_entity values (?,?,?,?)", (self._next, "w1", status, ts))
        con.execute("insert into execution_data values (?,?)", (self._next, data))
        con.commit()
        con.close()
        self._next += 1

    def sales(self, healthz=True):
        return h.assess(self.db, now=NOW, healthz=healthz, targets=TARGETS)["workflows"]["02_Sales_Poll"]


class TestVerdicts(_DB):
    def test_ok_requires_recent_success_and_business_success(self):
        self.run_("error", 9, error_data("access to env vars denied"))
        self.run_("success", 1, success_data({"success": True, "new_sales": 0}))
        r = self.sales()
        self.assertEqual(r["verdict"], "OK")
        self.assertEqual(r["business_op"], "OK")
        self.assertEqual(r["freshness"], "FRESH")

    def test_latest_error_is_failing_even_with_older_success(self):
        self.run_("success", 8, success_data({"success": True}))
        self.run_("error", 1, error_data("access to env vars denied"))
        r = self.sales()
        self.assertEqual(r["verdict"], "FAILING")
        self.assertEqual(r["last_error"], "access to env vars denied")

    def test_all_errors_is_failing_not_unknown(self):
        for i in range(3):
            self.run_("error", i + 1, error_data("access to env vars denied"))
        r = self.sales()
        self.assertEqual(r["verdict"], "FAILING")
        self.assertEqual((r["runs_total"], r["errors_total"]), (3, 3))

    def test_old_success_is_stale(self):
        self.run_("success", 30, success_data({"success": True}))
        self.assertEqual(self.sales()["verdict"], "STALE")

    def test_http_success_but_business_failure_is_not_ok(self):
        self.run_("success", 1, success_data({"success": False, "error": "gumroad 401"}))
        r = self.sales()
        self.assertNotEqual(r["verdict"], "OK")
        self.assertEqual(r["business_op"], "FAILED")

    def test_service_down_blocks_ok(self):
        self.run_("success", 1, success_data({"success": True}))
        self.assertNotEqual(self.sales(healthz=False)["verdict"], "OK")

    def test_no_runs_is_unknown_never_ok(self):
        r = h.assess(self.db, now=NOW, healthz=True, targets=TARGETS)["workflows"]
        self.assertEqual(r["02_Sales_Poll"]["verdict"], "UNKNOWN")
        self.assertEqual(r["01_Market_Scout"]["verdict"], "UNKNOWN")
        self.assertEqual(r["01_Market_Scout"]["freshness"], "MANUAL_ONLY")

    def test_db_is_opened_read_only(self):
        con = sqlite3.connect(f"file:{self.db.as_posix()}?mode=ro", uri=True)
        with self.assertRaises(sqlite3.OperationalError):
            con.execute("insert into workflow_entity values ('x','y',0)")
        con.close()


class TestRedaction(unittest.TestCase):
    def test_token_like_strings_are_masked(self):
        out = h.redact("401 for token ABCDEFGHIJKLMNOPQRSTUVWXYZ123456 at /x")
        self.assertNotIn("ABCDEFGHIJKLMNOPQRSTUVWXYZ123456", out)
        self.assertIn("<redacted>", out)

    def test_plain_error_text_is_kept(self):
        self.assertEqual(h.redact("access to env vars denied"), "access to env vars denied")


if __name__ == "__main__":
    unittest.main()
