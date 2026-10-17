"""Tests for scripts/n8n_exposure_audit.py: fixtures only, never the live n8n DB."""

import json
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import n8n_exposure_audit as audit  # noqa: E402


def _webhook(auth=None, path="x"):
    params = {"path": path, "httpMethod": "POST"}
    if auth:
        params["authentication"] = auth
    return {"name": "Webhook", "type": "n8n-nodes-base.webhook", "parameters": params}


class AuditNodesTest(unittest.TestCase):
    def kinds(self, nodes):
        return [f["kind"] for f in audit.audit_nodes(nodes, workflow="w", source="t", active=True)]

    def test_unauthenticated_webhook_flagged(self):
        self.assertEqual(self.kinds([_webhook()]), ["UNAUTH_WEBHOOK"])

    def test_header_auth_webhook_clean(self):
        self.assertEqual(self.kinds([_webhook(auth="headerAuth")]), [])

    def test_public_chat_without_auth_flagged(self):
        node = {"name": "Chat", "type": "@n8n/n8n-nodes-langchain.chatTrigger",
                "parameters": {"public": True, "mode": "hostedChat"}}
        self.assertEqual(self.kinds([node]), ["PUBLIC_CHAT"])
        node["parameters"]["authentication"] = "basicAuth"
        self.assertEqual(self.kinds([node]), [])

    def test_private_chat_clean(self):
        node = {"name": "Chat", "type": "@n8n/n8n-nodes-langchain.chatTrigger",
                "parameters": {"public": False}}
        self.assertEqual(self.kinds([node]), [])

    def test_env_expression_and_execute_command(self):
        nodes = [
            {"name": "H", "type": "n8n-nodes-base.httpRequest",
             "parameters": {"headerParameters": {"value": "={{ $env.INTERNAL_SERVICE_TOKEN }}"}}},
            {"name": "C", "type": "n8n-nodes-base.executeCommand", "parameters": {"command": "echo"}},
        ]
        self.assertEqual(sorted(self.kinds(nodes)), ["ENV_EXPRESSION", "EXECUTE_COMMAND"])

    def test_inline_secret_flagged_and_redacted(self):
        token = "bot1234567:" + "A" * 35
        node = {"name": "T", "type": "n8n-nodes-base.httpRequest",
                "parameters": {"url": f"https://api.telegram.org/{token}/sendMessage"}}
        found = audit.audit_nodes([node], workflow="w", source="t", active=False)
        self.assertEqual([f["kind"] for f in found], ["INLINE_SECRET"])
        self.assertNotIn(token, json.dumps(found))

    def test_env_word_in_plain_text_not_flagged(self):
        node = {"name": "N", "type": "n8n-nodes-base.set",
                "parameters": {"note": "environment notes"}}
        self.assertEqual(self.kinds([node]), [])


class SourcesTest(unittest.TestCase):
    def test_definitions_dir(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.json"), "w", encoding="utf-8") as fh:
                json.dump({"name": "A", "nodes": [_webhook()], "connections": {}}, fh)
            with open(os.path.join(d, "broken.json"), "w", encoding="utf-8") as fh:
                fh.write("{not json")
            found = audit.audit_definitions(d)
        self.assertEqual([(f["workflow"], f["kind"], f["active"]) for f in found],
                         [("A", "UNAUTH_WEBHOOK", None)])

    def test_database_copy_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "n8n.sqlite")
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE workflow_entity (name TEXT, active INTEGER, nodes TEXT)")
            con.execute("INSERT INTO workflow_entity VALUES (?,?,?)", ("Live", 1, json.dumps([_webhook()])))
            con.execute("INSERT INTO workflow_entity VALUES (?,?,?)", ("Off", 0, json.dumps([_webhook()])))
            con.commit()
            con.close()
            found = audit.audit_database(db)
            summary = audit.summarize(found)
            # immutable read-only open must not create a journal or change the file
            self.assertEqual(sorted(os.listdir(d)), ["n8n.sqlite"])
        self.assertEqual(summary["active_high"], 1)
        self.assertEqual({f["workflow"]: f["active"] for f in found}, {"Live": True, "Off": False})

    def test_alert_path_status_reports_presence_only(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w", encoding="utf-8") as fh:
                fh.write("TELEGRAM_BOT_TOKEN=secret-value\nOPENCLAW_TELEGRAM_CHAT_ID=\n# N8N_TELEGRAM_WEBHOOK_URL=x\n")
            saved = {k: os.environ.pop(k, None) for k in ("TELEGRAM_BOT_TOKEN", "OPENCLAW_TELEGRAM_CHAT_ID")}
            try:
                status = audit.alert_path_status(env)
            finally:
                for k, v in saved.items():
                    if v is not None:
                        os.environ[k] = v
        self.assertFalse(status["direct_telegram_ready"])
        self.assertEqual(status["missing_for_direct"], ["OPENCLAW_TELEGRAM_CHAT_ID"])
        self.assertEqual(status["n8n_relay_configured"], [])
        self.assertNotIn("secret-value", json.dumps(status))


if __name__ == "__main__":
    unittest.main()
