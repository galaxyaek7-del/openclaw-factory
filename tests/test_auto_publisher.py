"""Tests for the autonomous 5-gate publisher (src/publish/auto_publisher.py).

Rewritten as a unittest.TestCase in the Cycle 88 review: the original bare
pytest functions were never collected by CI's unittest runner, and one of
them wrote to the real data/publish_log.jsonl. The original five assertions
are kept; three fail-closed checks are added. No network: _publish_to_gumroad
and distributor.distribute are patched; no network.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.publish import auto_publisher as ap  # noqa: E402

FULL_PRODUCT = {
    "id": "test-no-cover-xxx",
    "name": "Test Product",
    "price_usd": 29,
    "price_basis": "MARKET_MINUS_10_PERCENT",
    "demand_evidence": {"type": "REAL"},
    "problem_statement": "A" * 60,
    "target_audience": "B" * 30,
    "measurable_value": "C" * 40,
    "differentiation": "D" * 35,
    "distribution_channels": ["gumroad"],
    "competition_level": "MEDIUM",
    "tags": ["tag1"],
}


class TestAutoPublisher(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.pub = ap.AutoPublisher(log_path=str(self.tmp / "publish_log.jsonl"))

    # --- the original five assertions ---------------------------------------
    def test_all_5_gates_required(self):
        result = self.pub.evaluate(FULL_PRODUCT, "Real content " * 50)
        self.assertEqual(result["decision"], "HOLD")
        self.assertIn("COVER_EXISTS", result["failed_gates"])

    def test_no_publish_without_price_evidence(self):
        gate = self.pub.gate_2_price({"id": "x", "price_usd": 29, "price_basis": "UNKNOWN",
                                      "demand_evidence": {"type": "MOCK"}})
        self.assertFalse(gate["passed"])

    def test_no_publish_with_placeholders(self):
        gate = self.pub.gate_5_complete({}, "Real content " * 30 + "[TODO]")
        self.assertFalse(gate["passed"])
        self.assertIn("[TODO]", gate["found"])

    def test_description_under_300_blocked(self):
        gate = self.pub.gate_4_description("Short description only")
        self.assertFalse(gate["passed"])
        self.assertLess(gate["word_count"], 300)

    def test_publish_log_created(self):
        self.pub._log({"test": True, "action": "TEST"})
        self.assertTrue(os.path.exists(self.pub.log_path))
        self.assertTrue(str(self.pub.log_path).startswith(str(self.tmp)))   # never the real log

    # --- Cycle 88 fail-closed checks -----------------------------------------
    def test_unreadable_cover_fails_closed(self):
        (self.tmp / "reports" / "T-COVER").mkdir(parents=True)
        (self.tmp / "reports" / "T-COVER" / "cover.png").write_bytes(b"not an image")
        cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, cwd)
        gate = self.pub.gate_3_cover({"id": "T-COVER"})
        self.assertFalse(gate["passed"])

    def test_live_step_goes_through_distributor_never_a_direct_post(self):
        """With the switch on, the live step calls distributor.distribute()
        for the gumroad arm with a real file -- no direct HTTP from here."""
        f = self.tmp / "deliverable.xlsx"
        f.write_bytes(b"PK real bytes")
        product = {"id": "T-1", "title": "T", "price_usd": 9.99, "files": [str(f)]}
        ok = [{"arm": "gumroad", "attempted": True, "ok": False, "skip_reason": "BLOCKED by write gate", "result": None}]
        with patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"}),              patch("distributor.distribute", return_value=ok) as dist,              patch("urllib.request.urlopen") as net:
            out = self.pub._publish_to_gumroad(product, "content")
        self.assertTrue(dist.called)
        args, kw = dist.call_args
        self.assertEqual((kw["arm_names"], kw["dry_run"]), (["gumroad"], False))
        self.assertEqual(args[0].file_path, str(f))
        self.assertFalse(net.called)
        self.assertEqual(out, {"success": False, "error": "BLOCKED by write gate"})

    def test_no_file_or_no_price_never_reaches_the_distributor(self):
        with patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"}),              patch("distributor.distribute") as dist:
            r1 = self.pub._publish_to_gumroad({"id": "T", "title": "T", "price_usd": 9, "files": ["missing.xlsx"]}, "c")
            f = self.tmp / "d.xlsx"; f.write_bytes(b"x")
            r2 = self.pub._publish_to_gumroad({"id": "T", "title": "T", "price_usd": 0, "files": [str(f)]}, "c")
            r3 = self.pub._publish_to_gumroad({"id": "T", "title": "T", "price_usd": 9, "files": [str(f)],
                                               "file_sha256": "0" * 64}, "c")
        self.assertFalse(dist.called)
        self.assertIn("no deliverable file", r1["error"])
        self.assertIn("no valid price", r2["error"])
        self.assertIn("identity mismatch", r3["error"])

    def test_live_switch_off_holds_before_anything_else(self):
        passed = {"all_passed": True, "failed_gates": [], "decision": "PUBLISH", "gates": []}
        with patch.object(self.pub, "evaluate", return_value=passed), \
             patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "false"}), \
             patch.object(self.pub, "_publish_to_gumroad") as post:
            out = self.pub.publish({"id": "T-2", "title": "T"}, "content")
        self.assertFalse(post.called)
        self.assertIn("live publish is disabled", out["reason"])


if __name__ == "__main__":
    unittest.main()
