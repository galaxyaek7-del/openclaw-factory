"""Tests for founder_next_action.py — the ONE-NEXT-ACTION engine.

Validates: real-state-only gates, single prioritized action, consolidation
of affiliate approvals into one grouped action, and deterministic output.
Uses a temp directory with fabricated data files (never touches the real
data/ directory)."""

import json
import os
import tempfile
import unittest
from pathlib import Path

import founder_next_action as fna


class FounderNextActionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)
        self._orig_root = fna._FACTORY_ROOT
        fna._FACTORY_ROOT = self._root
        (self._root / "data").mkdir()

    def tearDown(self):
        fna._FACTORY_ROOT = self._orig_root
        self._tmp.cleanup()

    def _write(self, rel, content):
        p = self._root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _default_env(self):
        self._write(".env", "PADDLE_WEBHOOK_SECRET=secret\n")

    def _publish_state(self, approved=False, ever=False):
        self._write("data/publish_protection_state.json", json.dumps({
            "arms": {"gumroad": {
                "first_publish_approved": approved,
                "has_ever_published_successfully": ever,
                "cooldown_until": None,
                "consecutive_failures": 0,
            }},
            "global": {"emergency_stopped": False},
        }))

    def test_one_next_action_is_gumroad_when_draft(self):
        self._default_env()
        self._publish_state(approved=False)
        self._write("data/paddle_products.json", json.dumps([{"product_id": "p1"}]))
        r = fna.build_founder_next_action()
        self.assertEqual(r["one_next_action"]["arm"], "gumroad")
        self.assertIn("payment method", r["one_next_action"]["action"])

    def test_no_paddle_gate_when_checkout_notifications_exist(self):
        self._default_env()
        self._publish_state(approved=True, ever=True)
        self._write("data/paddle_products.json", json.dumps([{"product_id": "p1"}]))
        self._write("data/paddle_checkout_notifications.json", json.dumps({"p1": {}}))
        r = fna.build_founder_next_action()
        arms = [g["arm"] for g in r["queue"]]
        self.assertNotIn("paddle", arms)

    def test_webhook_secret_gate_present_when_missing(self):
        self._write(".env", "")
        self._publish_state(approved=True, ever=True)
        self._write("data/paddle_products.json", json.dumps([]))
        r = fna.build_founder_next_action()
        arms = [g["arm"] for g in r["queue"]]
        self.assertIn("paddle_webhook", arms)

    def test_webhook_secret_gate_absent_when_set(self):
        self._default_env()
        self._publish_state(approved=True, ever=True)
        self._write("data/paddle_products.json", json.dumps([]))
        r = fna.build_founder_next_action()
        arms = [g["arm"] for g in r["queue"]]
        self.assertNotIn("paddle_webhook", arms)

    def test_affiliate_grouped_single_action(self):
        self._default_env()
        self._publish_state(approved=True, ever=True)
        self._write("data/paddle_products.json", json.dumps([{"product_id": "p1"}]))
        self._write("data/paddle_checkout_notifications.json", json.dumps({"p1": {}}))
        opp = {
            "opportunity_id": "CO-digitalocean-affiliate",
            "program_name": "DigitalOcean Affiliate Program",
            "status": "DISCOVERED",
            "target_customer": "devs",
        }
        self._write("data/commission_opportunities.jsonl", json.dumps(opp) + "\n")
        r = fna.build_founder_next_action()
        groups = [g for g in r["queue"] if g["arm"] == "affiliate_approvals"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["program_count"], 1)
        self.assertIn("DigitalOcean", groups[0]["action"])

    def test_open_gate_count_consolidated(self):
        self._default_env()
        self._publish_state(approved=False)
        self._write("data/paddle_products.json", json.dumps([{"product_id": "p1"}]))
        self._write("data/commission_opportunities.jsonl", "")
        r = fna.build_founder_next_action()
        self.assertEqual(r["open_gate_count"], 3)  # gumroad + paddle + webhook
        self.assertLessEqual(r["open_gate_count"], 6)  # never a wall of 20

    def test_amazon_tag_gate(self):
        self._default_env()  # no AMAZON_ASSOCIATE_TAG
        self._publish_state(approved=True, ever=True)
        self._write("data/paddle_products.json", json.dumps([{"product_id": "p1"}]))
        self._write("data/paddle_checkout_notifications.json", json.dumps({"p1": {}}))
        r = fna.build_founder_next_action()
        arms = [g["arm"] for g in r["queue"]]
        self.assertIn("amazon_affiliate", arms)


if __name__ == "__main__":
    unittest.main()