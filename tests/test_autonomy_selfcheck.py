import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import autonomy_selfcheck as sc  # noqa: E402


def _w(root, rel, text):
    p = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


class SelfCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name

    def rows(self, env, gate=None):
        from pathlib import Path
        gate = gate or {"open": False, "why": "WAITING FOR REAL DATA", "signals": {}}
        out = sc.collect(root=Path(self.root), env=env, health_fn=lambda: True, gate_fn=lambda: gate,
                         autostart_fn=lambda: "Ready")
        return {str(r["stage"]): r for r in out}

    def test_empty_factory_blocks_what_it_should_and_waits_on_demand(self):
        r = self.rows({})
        self.assertEqual("WAITING", r["0"]["status"])
        self.assertEqual("BLOCKED", r["1"]["status"])      # no loop log
        self.assertEqual("BLOCKED", r["2"]["status"])      # production switch off
        self.assertEqual("BLOCKED", r["6"]["status"])      # no Pinterest board
        self.assertEqual("BLOCKED", r["9"]["status"])      # no Telegram
        self.assertEqual("OK", r["10"]["status"])

    def test_live_publish_needs_both_switches(self):
        self.assertEqual("BLOCKED", self.rows({"FACTORY_LIVE_PUBLISH": "false", "GF_AUTO_PUBLISH_APPROVED": "true"})["5"]["status"])
        self.assertEqual("OK", self.rows({"FACTORY_LIVE_PUBLISH": "true", "GF_AUTO_PUBLISH_APPROVED": "true"})["5"]["status"])

    def test_telegram_needs_token_and_chat_id_and_values_are_never_printed(self):
        env = {"TELEGRAM_BOT_TOKEN": "SECRET-TOKEN-123456", "OPENCLAW_TELEGRAM_CHAT_ID": ""}
        r = self.rows(env)
        self.assertEqual("BLOCKED", r["9"]["status"])
        self.assertNotIn("SECRET-TOKEN-123456", json.dumps(r))

    def test_open_gate_and_freeze_mode_are_reported(self):
        r = self.rows({"GF_FREEZE_NEW_PRODUCTS": "true", "GF_DEMAND_GATED": "true"},
                      gate={"open": True, "why": "real demand recorded: SALE", "signals": {"SALE": 1}})
        self.assertEqual("OK", r["0"]["status"])
        self.assertEqual("demand-gated", r["0b"]["detail"])

    def test_sales_and_pinterest_come_from_the_files(self):
        _w(self.root, "data/product_registry.json", json.dumps({"generated_at": "2026-11-05T00:00:00",
            "products": [{"published": True, "sales_count": 2}, {"published": True, "sales_count": 0}]}))
        _w(self.root, "data/pinterest_queue.json", json.dumps({"board": "b1", "summary": {"READY": 3}}))
        _w(self.root, "data/sales_poll_last_check.json", json.dumps({"arms": {"gumroad": {"last_ok_at": "2026-11-05T10:00"}}}))
        r = self.rows({})
        self.assertEqual("OK", r["8"]["status"])
        self.assertIn("2 sales", r["8"]["detail"])
        self.assertEqual("OK", r["6"]["status"])
        self.assertEqual("OK", r["7"]["status"])

    def test_a_fresh_loop_log_means_alive(self):
        _w(self.root, "factory_loop.log", "{}\n")
        self.assertEqual("OK", self.rows({})["1"]["status"])
        old = time.time() - 3 * 3600
        os.utime(os.path.join(self.root, "factory_loop.log"), (old, old))
        self.assertEqual("BLOCKED", self.rows({})["1"]["status"])


if __name__ == "__main__":
    unittest.main()


def test_kids_youtube_stage_reports_what_each_episode_waits_for(tmp_path):
    import json
    import autonomy_selfcheck as sc
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "kids_youtube_status.json").write_text(json.dumps({"episodes": [
        {"episode": "a", "passed": False, "failing": ["approval", "credentials"]},
        {"episode": "b", "passed": False, "failing": ["approval"]}]}))
    rows = sc.collect(root=tmp_path, env={}, health_fn=lambda: 200, gate_fn=lambda: {"open": False, "why": "x", "signals": {}}, autostart_fn=lambda: "Ready")
    k = next(r for r in rows if r["stage"] == "K1")
    assert k["status"] == "BLOCKED" and "approval, credentials" in k["detail"] and "OAuth" in k["owner"]
    (tmp_path / "data" / "kids_youtube_status.json").write_text(json.dumps({"episodes": [{"episode": "a", "passed": True, "failing": []}]}))
    rows = sc.collect(root=tmp_path, env={}, health_fn=lambda: 200, gate_fn=lambda: {"open": False, "why": "x", "signals": {}}, autostart_fn=lambda: "Ready")
    assert next(r for r in rows if r["stage"] == "K1")["status"] == "OK"
