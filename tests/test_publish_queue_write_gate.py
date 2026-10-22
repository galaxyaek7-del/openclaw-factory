"""Regression coverage for the publish queue's write-gate path.

Cycle 109 audit finding: affiliate/publish_queue.py calls only gated
Gumroad mutators, but nothing proved that. These tests fail closed:

  * the queue's live retry path is denied when FACTORY_LIVE_PUBLISH is
    unset / false / malformed, before any upload or HTTP call;
  * create_product/enable_product deny before token or payload validation,
    so a denial cannot leave a partial remote effect;
  * a static guard pins the queue to the gated Gumroad calls, so a future
    edit cannot silently add an ungated mutation.

No network, no real credential, no real queue file.
"""
import ast
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate import publish_queue as pq
from channels import gumroad_publisher as gp
from channels.write_gate import WriteNotAuthorized

_QUEUE_ITEM = {
    "slug": "gate_probe",
    "file": "does-not-need-to-exist.pdf",
    "price": 18,
    "title": "Gate Probe",
    "description": "write-gate regression",
    "tags": ["gate"],
    "status": "PENDING_CAP",
}


def _flags():
    return ("absent", "empty", "false", "malformed")


class TestGumroadMutatorsFailClosed(unittest.TestCase):
    def _assert_denied(self, mutate, **kwargs):
        with patch.object(gp, "_request_with_retry") as network, \
                patch.object(gp, "_upload_file") as upload, \
                patch.object(gp, "_find_duplicate_listing") as duplicate:
            with self.assertRaises(WriteNotAuthorized) as ctx:
                mutate(**kwargs)
        self.assertIn("FACTORY_LIVE_PUBLISH", str(ctx.exception))
        network.assert_not_called()
        upload.assert_not_called()
        duplicate.assert_not_called()

    def test_create_product_denied_before_token_or_payload_checks(self):
        for value in (None, "", "0", "definitely-not-a-bool"):
            env = {} if value is None else {"FACTORY_LIVE_PUBLISH": value}
            with self.subTest(flag=value), patch.dict(os.environ, env, clear=True):
                self._assert_denied(
                    gp.create_product, token="", product_spec={})

    def test_enable_product_denied_before_product_id_check(self):
        for value in (None, "", "0", "definitely-not-a-bool"):
            env = {} if value is None else {"FACTORY_LIVE_PUBLISH": value}
            with self.subTest(flag=value), patch.dict(os.environ, env, clear=True):
                self._assert_denied(gp.enable_product, token="t", product_id=None)


class TestPublishQueueDeniedBeforeNetwork(unittest.TestCase):
    def test_retry_queue_publishes_nothing_without_live_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue_path = Path(tmp) / "queue.json"
            queue_path.write_text(json.dumps([dict(_QUEUE_ITEM)]), encoding="utf-8")
            with patch.object(pq, "QUEUE_PATH", queue_path), \
                    patch.dict(os.environ, {}, clear=True), \
                    patch.object(gp, "load_token", return_value="fake-token"), \
                    patch.object(gp, "_request_with_retry") as network, \
                    patch.object(gp, "_upload_file") as upload, \
                    patch.object(gp, "get_product") as readback:
                result = pq.retry_queue()
            saved = json.loads(queue_path.read_text(encoding="utf-8"))

        self.assertEqual(result["published"], [])
        self.assertFalse(result["cap_blocked"])
        self.assertEqual(result["pending"], 1)
        self.assertEqual(saved[0]["status"], "PENDING_CAP")
        self.assertNotIn("product_id", saved[0])
        self.assertTrue(result["errors"])
        self.assertIn("FACTORY_LIVE_PUBLISH", result["errors"][0][1])
        network.assert_not_called()
        upload.assert_not_called()
        readback.assert_not_called()


class TestPublishQueueCallSurface(unittest.TestCase):
    def test_queue_uses_only_gated_gumroad_mutations(self):
        source = (_FACTORY_ROOT / "affiliate" / "publish_queue.py").read_text(
            encoding="utf-8")
        tree = ast.parse(source)
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "gp"
        }
        self.assertEqual(
            calls,
            {"load_token", "create_product", "enable_product",
             "update_product", "get_product"},
        )

    def test_each_queue_mutator_starts_with_the_gate(self):
        tree = ast.parse(
            (_FACTORY_ROOT / "channels" / "gumroad_publisher.py").read_text(
                encoding="utf-8"))
        functions = {
            node.name: node for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        for mutator in ("create_product", "enable_product", "update_product"):
            with self.subTest(mutator=mutator):
                body = functions[mutator].body
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    body = body[1:]
                first = body[0]
                self.assertIsInstance(first, ast.Expr)
                call = first.value
                self.assertIsInstance(call, ast.Call)
                self.assertIsInstance(call.func, ast.Name)
                self.assertEqual(call.func.id, "_require_write_authorization")
                self.assertEqual(call.args[0].value, mutator)


if __name__ == "__main__":
    unittest.main(verbosity=2)
