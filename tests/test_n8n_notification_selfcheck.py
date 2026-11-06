"""Tests for scripts/n8n_notification_selfcheck.py.

The property that matters: this diagnostic must be able to tell the founder
*why* notifications are not arriving, using only read-only evidence, without
ever sending a message or printing a secret.

No test touches the live n8n instance, the live Telegram API, or the real
`~/.n8n/database.sqlite` -- each fixture builds its own throwaway SQLite file
with n8n's real column names, and every network entrypoint is monkeypatched.
TOTAL_NEW_SPEND stays $0.
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.n8n_notification_selfcheck as sc

WEBHOOK_DDL = ("create table webhook_entity (workflowId text, webhookPath text, method text, "
               "node text, webhookId text, pathLength integer)")
EXEC_DDL = ("create table execution_entity (id integer primary key, workflowId text, finished integer, "
            "mode text, retryOf text, retrySuccessId text, startedAt text, stoppedAt text, waitTill text, "
            "status text, deletedAt text, createdAt text, storedAt text, tracingContext text, "
            "deduplicationKey text)")
EXEC_DATA_DDL = "create table execution_data (executionId text, data text)"
WF_DDL = ("create table workflow_entity (id text primary key, name text, active integer)")


class Fixture:
    """A minimal n8n-shaped database, plus a .env with whatever keys we choose."""

    def __init__(self, chat_id=True, bot_token=True):
        self.dir = tempfile.mkdtemp(prefix="n8n_sc_test_")
        self.db = os.path.join(self.dir, "database.sqlite")
        con = sqlite3.connect(self.db)
        for ddl in (WEBHOOK_DDL, EXEC_DDL, EXEC_DATA_DDL, WF_DDL):
            con.execute(ddl)
        con.execute("insert into workflow_entity values ('PN03productionNotifyX','03_Production_Notify',1)")
        con.execute("insert into workflow_entity values ('TN04telegramNotifyX','04_Telegram_Notify',1)")
        con.execute("insert into workflow_entity values ('OTHER','02_Sales_Poll',1)")
        con.execute("insert into webhook_entity values "
                    "('PN03productionNotifyX','production-notify','POST','Webhook',null,null)")
        con.execute("insert into webhook_entity values "
                    "('TN04telegramNotifyX','golden-hunter-notify','POST','Webhook',null,null)")
        con.commit()
        con.close()
        self.env = os.path.join(self.dir, ".env")
        lines = ["GROQ_KEY=SECRET_GROQ_VALUE_DO_NOT_PRINT"]
        if chat_id:
            lines.append("OPENCLAW_TELEGRAM_CHAT_ID=1234567890")
        if bot_token:
            lines.append("TELEGRAM_BOT_TOKEN=999:AAA_secret_token_value")
        Path(self.env).write_text("\n".join(lines), encoding="utf-8")

    def add_execution(self, workflow_id, status, blob):
        con = sqlite3.connect(self.db)
        cur = con.execute("insert into execution_entity (workflowId, status, startedAt) "
                          "values (?,?,?)", (workflow_id, status, "2026-10-18T00:00:00Z"))
        con.execute("insert into execution_data values (?,?)", (str(cur.lastrowid), blob))
        con.commit()
        con.close()

    def cleanup(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)


def fake_health(*_a, **_k):
    return {"status": "UP", "probe": "/healthz", "body": "ok"}


def fake_telegram(*_a, **_k):
    return {"status": "OBSERVED", "bot_username": "SomeBot", "getme_ok": True, "updates_seen": 0}


class TestEnvDenial(unittest.TestCase):
    def test_env_denial_is_classified_and_blocks(self):
        fx = Fixture()
        try:
            fx.add_execution("TN04telegramNotifyX", "error",
                             '{"error": {"message": "ExpressionError: access to env vars denied"}}')
            with patch.object(sc, "n8n_health", fake_health), \
                 patch.object(sc, "telegram_reachability", fake_telegram):
                out = sc.run(db_path=fx.db, env_path=fx.env)
            a = out["assessment"]
            self.assertEqual(a["verdict"], "BLOCKED")
            self.assertTrue(a["checks"]["last_notify_execution_env_denied"])
            self.assertTrue(any("env vars denied" in r or "N8N_BLOCK_ENV_ACCESS_IN_NODE" in r
                                for r in a["reasons"]))
        finally:
            fx.cleanup()

    def test_delivering_when_a_real_success_exists_and_config_is_present(self):
        fx = Fixture()
        try:
            fx.add_execution("PN03productionNotifyX", "success", '{"ok": true}')
            with patch.object(sc, "n8n_health", fake_health), \
                 patch.object(sc, "telegram_reachability", fake_telegram):
                out = sc.run(db_path=fx.db, env_path=fx.env)
            a = out["assessment"]
            self.assertEqual(a["verdict"], "DELIVERING")
            self.assertEqual(a["reasons"], [])
        finally:
            fx.cleanup()

    def test_missing_chat_id_is_named_as_the_reason(self):
        fx = Fixture(chat_id=False)
        try:
            with patch.object(sc, "n8n_health", fake_health), \
                 patch.object(sc, "telegram_reachability", fake_telegram):
                out = sc.run(db_path=fx.db, env_path=fx.env)
            a = out["assessment"]
            self.assertEqual(a["verdict"], "BLOCKED")
            self.assertFalse(a["checks"]["chat_id_configured"])
            self.assertTrue(any("OPENCLAW_TELEGRAM_CHAT_ID" in r for r in a["reasons"]))
        finally:
            fx.cleanup()


class TestReadOnlyShape(unittest.TestCase):
    def test_registered_webhooks_are_read_without_triggering_them(self):
        fx = Fixture()
        try:
            con = sqlite3.connect(fx.db)
            info = sc.registered_webhooks(fx.db)
            con.close()
            self.assertIn("production-notify", info["paths"])
            self.assertIn("golden-hunter-notify", info["paths"])
            self.assertNotIn("d85a9c3b/chat", info["paths"])
        finally:
            fx.cleanup()

    def test_missing_database_degrades_to_unknown_instead_of_crashing(self):
        with patch.object(sc, "n8n_health", fake_health), \
             patch.object(sc, "telegram_reachability", fake_telegram):
            out = sc.run(db_path=os.path.join(tempfile.gettempdir(), "definitely_absent_n8n.sqlite"))
        self.assertEqual(out["webhooks"]["status"], "UNKNOWN")
        self.assertIn(out["assessment"]["verdict"], ("BLOCKED", "UNKNOWN"))
        self.assertTrue(any("database not found" in r for r in out["assessment"]["reasons"]))

    def test_n8n_down_is_reported_unknown_not_blocked(self):
        fx = Fixture()
        try:
            with patch.object(sc, "n8n_health", lambda *a, **k: {"status": "DOWN", "detail": "refused"}), \
                 patch.object(sc, "telegram_reachability", fake_telegram):
                out = sc.run(db_path=fx.db, env_path=fx.env)
            self.assertEqual(out["assessment"]["verdict"], "UNKNOWN")
        finally:
            fx.cleanup()


class TestSecretHygiene(unittest.TestCase):
    def test_output_never_contains_a_secret_value(self):
        fx = Fixture()
        try:
            fx.add_execution("TN04telegramNotifyX", "error", "access to env vars denied")
            with patch.object(sc, "n8n_health", fake_health), \
                 patch.object(sc, "telegram_reachability", fake_telegram):
                out = sc.run(db_path=fx.db, env_path=fx.env)
            blob = repr(out)
            self.assertNotIn("SECRET_GROQ_VALUE_DO_NOT_PRINT", blob)
            self.assertNotIn("999:AAA_secret_token_value", blob)
            # only key NAMES may appear, never values
            self.assertEqual(out["env_keys_checked"],
                             ["OPENCLAW_TELEGRAM_CHAT_ID", "TELEGRAM_BOT_TOKEN"])
        finally:
            fx.cleanup()


class TestTelegramDiscovery(unittest.TestCase):
    def test_chat_ids_are_discovered_from_getupdates_without_sending_anything(self):
        calls = []

        class FakeResp:
            def __init__(self, payload):
                self._p = payload.encode("utf-8")

            def read(self, *_a):
                return self._p

        def fake_urlopen(req, timeout=None):
            url = req if isinstance(req, str) else req.full_url
            calls.append(url.split("/bot")[0] + "/bot<redacted>/" + url.rsplit("/", 1)[-1])
            if "getMe" in url:
                return FakeResp('{"ok": true, "result": {"username": "SomeBot"}}')
            return FakeResp('{"ok": true, "result": [{"message": {"chat": '
                            '{"id": 5551234, "type": "private", "first_name": "Owner"}}}]}')

        with patch.object(sc.urllib.request, "urlopen", fake_urlopen):
            out = sc.telegram_reachability(token="123:FAKE")
        self.assertEqual(out["bot_username"], "SomeBot")
        self.assertEqual(out["updates_seen"], 1)
        self.assertIn("5551234", out["discoverable_chat_ids"])
        # nothing was sent: every call was a GET to getMe/getUpdates only
        self.assertTrue(all("getMe" in c or "getUpdates" in c for c in calls), calls)


if __name__ == "__main__":
    unittest.main(verbosity=2)


def test_latest_execution_decides_not_any_old_denial(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import n8n_notification_selfcheck as sc
    old_denied = {"detail": "ENV_ACCESS_DENIED"}
    ok = {"detail": "DELIVERED"}
    a = sc.assess({"OPENCLAW_TELEGRAM_CHAT_ID", "TELEGRAM_BOT_TOKEN"}, {"status": "UP"},
                  {"paths": ["golden-hunter-notify", "production-notify"]}, {"executions": [ok, old_denied, old_denied]},
                  {"status": "OBSERVED"})
    assert a["checks"]["last_notify_execution_env_denied"] is False and a["verdict"] == "DELIVERING"
    b = sc.assess({"OPENCLAW_TELEGRAM_CHAT_ID", "TELEGRAM_BOT_TOKEN"}, {"status": "UP"},
                  {"paths": ["golden-hunter-notify", "production-notify"]}, {"executions": [old_denied, ok]},
                  {"status": "OBSERVED"})
    assert b["checks"]["last_notify_execution_env_denied"] is True


def test_db_copy_includes_the_wal_file(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import n8n_notification_selfcheck as sc
    src = tmp_path / "database.sqlite"
    src.write_bytes(b"main")
    (tmp_path / "database.sqlite-wal").write_bytes(b"wal")
    dest_dir = tmp_path / "out"
    dest_dir.mkdir()
    dest, err = sc._db_copy(src, dest_dir)
    assert err is None and (Path(str(dest) + "-wal")).read_bytes() == b"wal"
