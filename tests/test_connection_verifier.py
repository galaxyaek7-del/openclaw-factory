"""connection_verifier.py -- "connected" only with evidence (2026-10-23).

Fixtures and injected probes only; nothing here calls the network.

    python -m pytest tests/test_connection_verifier.py -q
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import connection_verifier as cv  # noqa: E402

NOW = datetime(2026, 10, 23, 8, 0, tzinfo=timezone.utc)


def tick(ts, *steps):
    acts = ",".join('{"step":"%s","action":"%s","detail":"x"}' % s for s in steps)
    return '{"timestamp":"%s","actions":[%s]}' % (ts, acts)


class TestLoopSteps(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.log = Path(d.name) / "loop.log"

    def write(self, *lines):
        self.log.write_text("header\n" + "\n".join(lines) + "\n", encoding="utf-8")

    def test_classification_from_real_records(self):
        self.write(tick("2026-10-23T07:40:00Z", ("sales_poll", "none"), ("diagnose", "failed"), ("hunt", "failed")),
                   tick("2026-10-23T07:50:00Z", ("sales_poll", "none"), ("diagnose", "failed"), ("hunt", "none")))
        rows = {r["name"]: r for r in cv.loop_steps(NOW, log_path=self.log)}
        self.assertEqual(rows["loop:sales_poll"]["status"], cv.VERIFIED)
        self.assertEqual(rows["loop:diagnose"]["status"], cv.FAILED)
        self.assertEqual(rows["loop:hunt"]["status"], cv.DEGRADED)
        self.assertEqual(rows["factory_loop"]["status"], cv.VERIFIED)

    def test_failure_only_step_that_stopped_failing_is_recovered_not_failed(self):
        self.write(tick("2026-10-23T04:00:00Z", ("diagnose", "failed")),
                   tick("2026-10-23T07:50:00Z", ("sales_poll", "none")))
        rows = {r["name"]: r for r in cv.loop_steps(NOW, log_path=self.log)}
        self.assertEqual(rows["loop:diagnose"]["status"], cv.DEGRADED)
        self.assertIn("no failure logged", rows["loop:diagnose"]["evidence"])

    def test_stale_loop_and_old_records_are_not_verified(self):
        self.write(tick("2026-10-23T06:00:00Z", ("sales_poll", "none")),
                   tick("2026-10-21T06:00:00Z", ("ancient", "none")))
        rows = {r["name"]: r for r in cv.loop_steps(NOW, log_path=self.log)}
        self.assertEqual(rows["factory_loop"]["status"], cv.FAILED)  # last tick 2 h ago
        self.assertNotIn("loop:ancient", rows)                      # outside the 24 h window

    def test_no_log_is_unknown(self):
        rows = cv.loop_steps(NOW, log_path=self.log)
        self.assertEqual(rows[0]["status"], cv.UNKNOWN)


class TestProbes(unittest.TestCase):
    def test_server_status_maps_from_health_body(self):
        ok = cv.server(probe=lambda u: (200, {"status": "ok", "checks": {}}))[0]
        warn = cv.server(probe=lambda u: (200, {"status": "warning", "checks": {"sensing_engine": {"ok": False}}}))[0]
        down = cv.server(probe=lambda u: (_ for _ in ()).throw(OSError("refused")))[0]
        self.assertEqual((ok["status"], warn["status"], down["status"]), (cv.VERIFIED, cv.DEGRADED, cv.FAILED))
        self.assertIn("sensing_engine", warn["evidence"])

    def test_telegram_valid_token_without_chat_id_is_degraded(self):
        with patch("channels.env_config.read_env_value", side_effect=lambda k, p: "SECRET-TOKEN-VALUE" if k == "TELEGRAM_BOT_TOKEN" else None):
            r = cv.telegram(probe=lambda u: (200, {"ok": True}))[0]
        self.assertEqual(r["status"], cv.DEGRADED)
        self.assertNotIn("SECRET-TOKEN-VALUE", r["evidence"])

    def test_telegram_rejected_token_fails(self):
        with patch("channels.env_config.read_env_value", side_effect=lambda k, p: "tok" if k == "TELEGRAM_BOT_TOKEN" else "1"):
            r = cv.telegram(probe=lambda u: (200, {"ok": False}))[0]
        self.assertEqual(r["status"], cv.FAILED)

    def test_n8n_verdicts_map(self):
        report = {"service_up": True, "workflows": {
            "A": {"verdict": "OK", "runs_total": 3, "errors_total": 0},
            "B": {"verdict": "FAILING", "last_error": "ENOTFOUND trends.google.com"},
            "C": {"verdict": "UNKNOWN"}}}

        class Out:
            stdout = json.dumps(report)
        rows = {r["name"]: r for r in cv.n8n(run=lambda *a, **k: Out())}
        self.assertEqual(rows["n8n"]["status"], cv.VERIFIED)
        self.assertEqual(rows["n8n:A"]["status"], cv.VERIFIED)
        self.assertEqual(rows["n8n:B"]["status"], cv.FAILED)
        self.assertIn("ENOTFOUND", rows["n8n:B"]["evidence"])
        self.assertEqual(rows["n8n:C"]["status"], cv.UNKNOWN)


class TestRules(unittest.TestCase):
    def test_agent_statuses_follow_execution_records(self):
        d = Path(tempfile.mkdtemp())
        log = d / "agents.jsonl"
        recs = [
            {"agent": "scout", "outcome": "ok", "source": "scout_pipeline", "started_at": "2026-10-20T08:00:00Z"},
            {"agent": "builder", "outcome": "ok", "source": "probe", "started_at": "2026-10-23T07:00:00Z"},
            {"agent": "qa", "outcome": "error", "source": "api", "started_at": "2026-10-23T07:00:00Z"},
            {"agent": "design", "outcome": "ok", "source": "scout_pipeline", "started_at": "2026-07-09T08:00:00Z"},
        ]
        log.write_text("".join(json.dumps(r) + chr(10) for r in recs), encoding="utf-8")
        rows = {r["name"]: r["status"] for r in cv.ai_agents(NOW, log_path=log)}
        self.assertEqual(rows["agent:scout"], "VERIFIED_CONNECTED")
        self.assertEqual(rows["agent:builder"], "VERIFIED_EXECUTABLE_NOT_CONNECTED")
        self.assertEqual(rows["agent:qa"], cv.FAILED)
        self.assertEqual(rows["agent:design"], "VERIFIED_EXECUTABLE_NOT_CONNECTED")  # factory run too old
        self.assertEqual(rows["agent:finance"], cv.UNKNOWN)

    def test_ai_provider_needs_a_recent_record(self):
        d = Path(tempfile.mkdtemp())
        log = d / "ai.jsonl"
        no_agents = d / "agents.jsonl"   # isolate from the live agent log
        log.write_text(json.dumps({"timestamp": "2026-10-20T08:00:00", "model": "m"}) + "\n", encoding="utf-8")
        self.assertEqual(cv.ai_provider(NOW, log_path=log, agent_log_path=no_agents)[0]["status"], cv.DEGRADED)
        log.write_text(json.dumps({"timestamp": "2026-10-23T07:00:00", "model": "m"}) + "\n", encoding="utf-8")
        self.assertEqual(cv.ai_provider(NOW, log_path=log, agent_log_path=no_agents)[0]["status"], cv.VERIFIED)

    def test_ai_provider_counts_successful_agent_calls(self):
        # 2026-10-29: Groq showed DEGRADED ("135 h ago") while the server.js agents,
        # which call Groq but do not write ai_cost_log.jsonl, had succeeded that morning.
        d = Path(tempfile.mkdtemp())
        log, agents = d / "ai.jsonl", d / "agents.jsonl"
        log.write_text(json.dumps({"timestamp": "2026-10-18T08:00:00", "model": "m"}) + "\n", encoding="utf-8")
        agents.write_text(json.dumps({"agent": "scout", "source": "sensing_trends", "outcome": "ok", "model": "g",
                                      "started_at": "2026-10-23T07:30:00Z", "duration_ms": 600}) + "\n"
                          + json.dumps({"agent": "qa", "outcome": "error", "model": "g",
                                        "started_at": "2026-10-23T07:50:00Z"}) + "\n", encoding="utf-8")
        row = cv.ai_provider(NOW, log_path=log, agent_log_path=agents)[0]
        self.assertEqual(row["status"], cv.VERIFIED)
        self.assertIn("agent scout via sensing_trends", row["evidence"])
        agents.write_text(json.dumps({"agent": "qa", "outcome": "error", "model": "g",
                                      "started_at": "2026-10-23T07:50:00Z"}) + "\n", encoding="utf-8")
        self.assertEqual(cv.ai_provider(NOW, log_path=log, agent_log_path=agents)[0]["status"], cv.DEGRADED)

    def test_offline_run_has_no_probes(self):
        out = cv.verify(live=False, now=NOW)
        self.assertFalse(any(r["method"] == "probe" for r in out["rows"]))


if __name__ == "__main__":
    unittest.main()
