"""Tests for the five agent-facing READ-ONLY tools added 2026-11-18 to
mcp_pilot/gf_readonly_server.py: factory_status, tasks_status, test_status,
revenue_evidence, recent_logs.

Boundaries pinned here:
  * every tool is read-only and reports absence explicitly (never invents 0 as
    if it were evidence, never upgrades a missing file to PASS)
  * revenue counts only rows of data/verified_transactions.jsonl; simulation
    and test rows are excluded
  * recent_logs accepts a whitelisted source name only, never a path
  * no value from .env appears in any tool output, including a log line that
    carries a real token
"""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "mcp_pilot" / "gf_readonly_server.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load("gf_readonly_server_tools_under_test", SERVER)
S.LOG = Path(tempfile.mkdtemp()) / "calls.jsonl"     # keep test calls out of the audit log
os.environ["GF_MCP_PROBE_HEALTH"] = "0"              # no network in tests


def _iso(delta_s=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=delta_s)).isoformat()


class _Base(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        self.patches = []

        def pat(name, value):
            p = mock.patch.object(S, name, value)
            p.start()
            self.patches.append(p)

        self.pat = pat
        for name, attr in (("FACTORY_STATE", "state.json"), ("SUPERVISOR_LOG", "supervisor.log"),
                           ("TASKS_MD", "TASKS.md"), ("WORKLOG_MD", "WORKLOG.md"),
                           ("REGRESSION_STATUS", "regression.json"), ("VERIFIED_TX", "verified.jsonl"),
                           ("FINANCE_JSON", "finance.json"), ("PRODUCT_REGISTRY", "registry.json")):
            pat(name, self.d / attr)
        (self.d / "registry.json").write_text(json.dumps({"generated_at": _iso(), "products": []}), encoding="utf-8")
        (self.d / "finance.json").write_text(json.dumps({"totalSales": 0}), encoding="utf-8")

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def call(self, name, args=None):
        r = S.call_tool(name, args or {})
        text = r["content"][0]["text"]
        return r, (json.loads(text) if not r["isError"] else text)


class TestFactoryStatus(_Base):
    def _state(self, interrupted=False, age_s=0):
        (self.d / "state.json").write_text(json.dumps({
            "updated_at": _iso(-age_s),
            "current_task": {"name": "golden_hunter_tick", "step": "ceo_loop", "started_at": _iso(-age_s)},
            "last_successful_checkpoint": {"stage": "learning", "at": _iso(-3600)},
            "pending_retries": [],
            "recovery_info": {"interrupted": interrupted},
        }), encoding="utf-8")

    def test_fresh_state_is_ok_and_reports_the_step(self):
        self._state()
        r, p = self.call("factory_status")
        self.assertFalse(r["isError"])
        self.assertEqual(p["status"], "OK")
        self.assertEqual(p["loop"]["current_step"], "ceo_loop")
        self.assertFalse(p["loop"]["interrupted"])
        self.assertEqual(p["server_health"]["state"], "NOT_MEASURED")

    def test_interrupted_recovery_is_degraded_never_ok(self):
        self._state(interrupted=True)
        _, p = self.call("factory_status")
        self.assertEqual(p["status"], "DEGRADED")
        self.assertTrue(p["loop"]["interrupted"])

    def test_stale_state_is_degraded(self):
        self._state(age_s=3 * 3600)
        _, p = self.call("factory_status")
        self.assertEqual(p["status"], "DEGRADED")
        self.assertGreater(p["loop"]["state_age_seconds"], 3000)

    def test_supervisor_events_are_read_per_target(self):
        events = [{"at": _iso(-60), "event": "spawn", "target": "C:\\x\\server.js"},
                  {"at": _iso(-30), "event": "crash", "code": 1},
                  {"at": _iso(-20), "event": "spawn", "target": "C:\\x\\factory_loop.js"}]
        (self.d / "supervisor.log").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
        self._state()
        _, p = self.call("factory_status")
        self.assertEqual(p["supervisor"]["last_event_by_target"]["server.js"]["event"], "spawn")
        self.assertEqual(p["supervisor"]["last_event_by_target"]["factory_loop.js"]["event"], "spawn")
        self.assertEqual(p["supervisor"]["crashes_24h"], 1)

    def test_arguments_are_refused(self):
        r, text = self.call("factory_status", {"path": "../.env"})
        self.assertTrue(r["isError"])
        self.assertIn("takes no arguments", text)


class TestTasksStatus(_Base):
    def test_parses_boxes_sections_and_blocked_rows(self):
        (self.d / "TASKS.md").write_text(
            "# tasks\n\n## Item A\n[x] done one\n[ ] pending one\n\n## Item B\n[ ] autopilot\n"
            "**BLOCKED** needs an ADR\n[ ] other\n", encoding="utf-8")
        (self.d / "WORKLOG.md").write_text(
            "## x\n\n### 2026-11-18 older\n- first older\n\n### 2026-11-19 newer\n- first newer\n", encoding="utf-8")
        _, p = self.call("tasks_status")
        self.assertEqual((p["tasks"]["total"], p["tasks"]["done"], p["tasks"]["pending"]), (4, 1, 3))
        self.assertEqual(p["sections"], ["Item A", "Item B"])
        self.assertEqual(p["worklog_recent"][0]["heading"], "2026-11-19 newer")
        self.assertEqual(p["worklog_recent"][0]["first_item"], "first newer")
        self.assertEqual(len(p["worklog_recent"]), 2)

    def test_missing_files_are_unknown_not_ok(self):
        _, p = self.call("tasks_status")
        self.assertEqual(p["status"], "UNKNOWN")
        self.assertEqual(p["tasks"]["total"], 0)
        self.assertEqual(p["blocked_items"], [])


class TestTestStatus(_Base):
    def _write(self, doc):
        (self.d / "regression.json").write_text(json.dumps(doc), encoding="utf-8")

    def test_fresh_pass(self):
        self._write({"at": _iso(), "failed": 0, "python": {"passed": 10, "failed": 0}, "failures": []})
        _, p = self.call("test_status")
        self.assertEqual(p["status"], "PASS")
        self.assertEqual(p["failed"], 0)

    def test_failures_are_reported_verbatim(self):
        self._write({"at": _iso(), "failed": 2, "failures": ["tests/a.py::x", "tests/b.py::y"]})
        _, p = self.call("test_status")
        self.assertEqual(p["status"], "FAILED")
        self.assertEqual(p["failures"], ["tests/a.py::x", "tests/b.py::y"])

    def test_old_result_is_stale_not_pass(self):
        self._write({"at": _iso(-48 * 3600), "failed": 0})
        _, p = self.call("test_status")
        self.assertEqual(p["status"], "STALE")

    def test_missing_record_is_an_explicit_error(self):
        r, text = self.call("test_status")
        self.assertTrue(r["isError"])
        self.assertIn("not been generated yet", text)


class TestRevenueEvidence(_Base):
    def test_absent_ledger_is_zero_with_an_explicit_state(self):
        _, p = self.call("revenue_evidence")
        self.assertEqual(p["verified"]["state"], "NO_VERIFIED_TRANSACTION_RECORD")
        self.assertEqual(p["verified"]["verified_revenue_usd"], 0)
        self.assertEqual(p["verified"]["transactions"], [])

    def test_only_real_rows_count_and_simulated_or_test_rows_are_excluded(self):
        rows = [{"offer_id": "B13-001", "platform": "gumroad", "amount_cents": 1500, "at": _iso()},
                {"offer_id": "B13-002", "platform": "gumroad", "amount_cents": 2500, "at": _iso()},
                {"offer_id": "SIM-1", "platform": "gumroad", "amount_cents": 9900, "simulation": True},
                {"offer_id": "TEST-1", "platform": "gumroad", "amount_cents": 100, "test": True}]
        (self.d / "verified.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\nnot-json\n", encoding="utf-8")
        _, p = self.call("revenue_evidence")
        self.assertEqual(p["verified"]["state"], "VERIFIED_ROWS_PRESENT")
        self.assertEqual(p["verified"]["row_count"], 2)
        self.assertEqual(p["verified"]["verified_revenue_usd"], 40.0)
        self.assertEqual(p["verified"]["unparseable_lines"], 1)

    def test_registry_totals_are_labelled_separately_from_verified_revenue(self):
        (self.d / "registry.json").write_text(json.dumps({"generated_at": _iso(), "products": [
            {"primary_state": "PUBLIC_LISTING_VERIFIED", "sales_count": 0, "sales_usd_cents": 0}]}), encoding="utf-8")
        _, p = self.call("revenue_evidence")
        self.assertEqual(p["registry"]["sales_units"], 0)
        self.assertEqual(p["verified"]["verified_revenue_usd"], 0)   # registry is not the ledger


class TestRecentLogs(_Base):
    def setUp(self):
        super().setUp()
        log = self.d / "factory_loop.log"
        log.write_text("\n".join(f"line-{i}" for i in range(1, 11)) + "\n", encoding="utf-8")
        self.pat("LOG_SOURCES", {"factory_loop": log, "supervisor": self.d / "supervisor.log"})

    def test_tail_and_default_source(self):
        _, p = self.call("recent_logs", {"lines": 3})
        self.assertEqual(p["source"], "factory_loop.log")
        self.assertEqual(p["lines"], ["line-8", "line-9", "line-10"])

    def test_line_bounds_are_enforced(self):
        for bad in (0, 201, "5", 3.5, True):
            r, _ = self.call("recent_logs", {"lines": bad})
            self.assertTrue(r["isError"], bad)

    def test_unknown_source_and_caller_paths_are_refused(self):
        r, text = self.call("recent_logs", {"source": "../../.env"})
        self.assertTrue(r["isError"])
        self.assertIn("source must be one of", text)
        r, text = self.call("recent_logs", {"path": "C:/Windows/win.ini"})
        self.assertTrue(r["isError"])
        self.assertIn("unexpected argument", text)

    def test_env_style_lines_are_dropped_and_tokens_redacted(self):
        (self.d / "factory_loop.log").write_text(
            "GROQ_KEY=super-secret-value\n"
            "bot 1234567890:" + "A" * 35 + "\n"
            "normal line\n", encoding="utf-8")
        _, p = self.call("recent_logs", {"lines": 200})
        joined = "\n".join(p["lines"])
        self.assertEqual(p["dropped_env_style_lines"], 1)
        self.assertNotIn("super-secret-value", joined)
        self.assertNotIn("A" * 35, joined)
        self.assertIn("normal line", joined)

    def test_missing_log_is_reported(self):
        r, text = self.call("recent_logs", {"source": "supervisor"})
        self.assertTrue(r["isError"])
        self.assertIn("log not found", text)


class TestSecretsNeverLeave(unittest.TestCase):
    """The strong guarantee: no value from the real .env appears in any tool."""

    def test_no_env_value_appears_in_any_tool_output(self):
        env_path = ROOT / ".env"
        if not env_path.is_file():
            self.skipTest("no .env on this machine")
        values = []
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            if len(val) >= 12 and not val.isdigit():
                values.append(val)
        self.assertGreaterEqual(len(values), 3, "the .env check must not be vacuous")

        for name in ("factory_status", "tasks_status", "test_status", "revenue_evidence", "recent_logs"):
            r = S.call_tool(name, {"lines": 200} if name == "recent_logs" else {})
            text = r["content"][0]["text"]
            for v in values:
                self.assertFalse(v in text, f"a .env value leaked into {name} output")

    def test_a_real_token_echoed_into_a_log_is_redacted(self):
        env_path = ROOT / ".env"
        if not env_path.is_file():
            self.skipTest("no .env on this machine")
        token = ""
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"')
        if len(token) < 20:
            self.skipTest("no usable Telegram token in .env")
        self.assertNotIn(token, S.sanitize_text("echo " + token))


if __name__ == "__main__":
    unittest.main()
