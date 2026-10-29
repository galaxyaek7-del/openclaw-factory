"""Affiliate click classification (backlog B24, 2026-10-29).

Fixtures only: a temp ledger, a temp fake repo for server.js/.env; no live file.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from affiliate_commerce import click_classification as cc  # noqa: E402
from affiliate_commerce import click_tracking as ct  # noqa: E402

SERVER_JS = "const BIND_HOST = process.env.BIND_HOST || '127.0.0.1';\n"
REACH_LOOPBACK = {"loopback_only": True, "since": "2026-07-17", "basis": "fixture"}
REACH_OPEN = {"loopback_only": False, "basis": "fixture"}
IDS = {"B07LCCT6VS", "CO-n8n-affiliate"}


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.ledger = os.path.join(self.d, "clicks.jsonl")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def repo(self, server=SERVER_JS, env=None):
        r = os.path.join(self.d, "repo")
        os.makedirs(r, exist_ok=True)
        Path(r, "server.js").write_text(server, encoding="utf-8")
        if env is not None:
            Path(r, ".env").write_text(env, encoding="utf-8")
        return r


class Reachability(Base):
    def test_loopback_default_without_override(self):
        r = cc.server_reachability(self.repo(env="PORT=3000\n"), environ={})
        self.assertTrue(r["loopback_only"])
        self.assertEqual("2026-07-17", r["since"])

    def test_env_override_to_public_address(self):
        self.assertFalse(cc.server_reachability(self.repo(), environ={"BIND_HOST": "0.0.0.0"})["loopback_only"])
        self.assertFalse(cc.server_reachability(self.repo(env="BIND_HOST=0.0.0.0\n"), environ={})["loopback_only"])
        self.assertTrue(cc.server_reachability(self.repo(env="BIND_HOST=127.0.0.1\n"), environ={})["loopback_only"])

    def test_changed_default_is_unknown_not_assumed(self):
        r = cc.server_reachability(self.repo(server="app.listen(PORT, '0.0.0.0')\n"), environ={})
        self.assertIsNone(r["loopback_only"])


class Classify(unittest.TestCase):
    def test_rules_in_order(self):
        row = {"product_id": "B07LCCT6VS", "timestamp": "2026-10-29T10:00:00+00:00"}
        self.assertEqual("BOT", cc.classify(dict(row, ua_category="bot", origin="external"), REACH_OPEN, IDS)[0])
        self.assertEqual("INTERNAL", cc.classify(dict(row, origin="loopback", ua_category="browser"), REACH_OPEN, IDS)[0])
        self.assertEqual("INTERNAL", cc.classify(row, REACH_LOOPBACK, IDS)[0])
        self.assertEqual("TEST", cc.classify(dict(row, product_id="fixture-x"), REACH_OPEN, IDS)[0])
        self.assertEqual("EXTERNAL_BROWSER",
                         cc.classify(dict(row, origin="external", ua_category="browser"), REACH_OPEN, IDS)[0])
        self.assertEqual("UNKNOWN", cc.classify(row, REACH_OPEN, IDS)[0])
        self.assertEqual("UNKNOWN", cc.classify(dict(row, origin="external", ua_category="unknown"),
                                                REACH_OPEN, IDS)[0])

    def test_loopback_window_does_not_cover_older_rows(self):
        old = {"product_id": "B07LCCT6VS", "timestamp": "2026-07-01T00:00:00+00:00"}
        self.assertEqual("UNKNOWN", cc.classify(old, REACH_LOOPBACK, IDS)[0])

    def test_recorded_external_beats_reachability_inference(self):
        row = {"product_id": "B07LCCT6VS", "timestamp": "2026-10-29T10:00:00+00:00",
               "origin": "external", "ua_category": "browser"}
        self.assertEqual("EXTERNAL_BROWSER", cc.classify(row, REACH_LOOPBACK, IDS)[0])


class Summary(Base):
    def test_only_external_browser_counts_as_possible_human(self):
        rows = [
            {"product_id": "B07LCCT6VS", "timestamp": "2026-10-29T10:00:00+00:00", "origin": "loopback"},
            {"product_id": "B07LCCT6VS", "timestamp": "2026-10-29T10:01:00+00:00",
             "origin": "external", "ua_category": "browser"},
            {"product_id": "B07LCCT6VS", "timestamp": "2026-10-29T10:02:00+00:00",
             "origin": "external", "ua_category": "bot"},
        ]
        with open(self.ledger, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        s = cc.summarize(self.ledger, root=self.repo(env=""), environ={}, known_ids=IDS)
        self.assertEqual(3, s["total_recorded"])
        self.assertEqual(1, s["possible_human"])
        self.assertEqual({"BOT": 1, "INTERNAL": 1, "TEST": 0, "EXTERNAL_BROWSER": 1, "UNKNOWN": 0}, s["counts"])
        out = os.path.join(self.d, "summary.json")
        cc.write_summary(out, ledger_path=self.ledger, root=self.repo(env=""), environ={}, known_ids=IDS)
        self.assertEqual(1, json.load(open(out, encoding="utf-8"))["possible_human"])

    def test_empty_ledger(self):
        s = cc.summarize(os.path.join(self.d, "none.jsonl"), root=self.repo(), environ={}, known_ids=IDS)
        self.assertEqual(0, s["total_recorded"])
        self.assertEqual(0, s["possible_human"])


class Capture(Base):
    def test_only_fixed_vocabulary_is_stored(self):
        r = ct.record_attributed_click("B07LCCT6VS", ledger_path=self.ledger,
                                       ua_category="browser", origin="external")
        self.assertEqual(("browser", "external"), (r["ua_category"], r["origin"]))
        r = ct.record_attributed_click("B07LCCT6VS", ledger_path=self.ledger,
                                       ua_category="Mozilla/5.0 (X11)", origin="203.0.113.9")
        self.assertNotIn("ua_category", r)
        self.assertNotIn("origin", r)
        r = ct.record_attributed_click("B07LCCT6VS", ledger_path=self.ledger)
        self.assertNotIn("origin", r)

    def test_click_summary_reports_classification(self):
        ct.record_attributed_click("B07LCCT6VS", ledger_path=self.ledger, ua_category="browser", origin="loopback")
        s = ct.click_summary(self.ledger)
        self.assertEqual(1, s["total_real_clicks"])
        self.assertEqual(1, s["by_classification"]["INTERNAL"])
        self.assertEqual(0, s["possible_human_clicks"])


class ArmText(unittest.TestCase):
    def test_affiliate_arm_states_click_classes(self):
        import business_arms as b
        out = b._affiliate_cfg(b.ARMS["affiliate_intelligence"],
                               {"total": 38, "counts": {"INTERNAL": 38, "BOT": 0}, "possible_human": 0})
        self.assertEqual("38 click(s) recorded (38 INTERNAL); 0 could be from an outside person", out["gap"])
        self.assertIn("AMAZON_ASSOCIATE_TAG", out["blocker"])
        self.assertIs(b.ARMS["affiliate_intelligence"],
                      b._affiliate_cfg(b.ARMS["affiliate_intelligence"], {}))


if __name__ == "__main__":
    unittest.main()
