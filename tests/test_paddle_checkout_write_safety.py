"""Write-safety of the Paddle checkout check (2026-10-22).

check_and_notify_all() POSTs a Paddle transaction per product. Three defects
were found against the live system, none of which had executed a write yet,
because every call currently returns 403:
  1. Only a SUCCESSFUL Telegram send stopped re-creation. With Telegram
     unconfigured, every factory tick would have created a new transaction
     per product, indefinitely, once checkout worked.
  2. It ran on every ~10-minute tick (728 runs since 2026-10-15), adding to
     Paddle 429 refusals.
  3. A "read-only" gate reader (autonomous_commerce_ops.human_gate_orchestrator,
     reached from founder_next_action and first_dollar_engine) called it, so
     merely reading status attempted live Paddle writes, even from tests.
All network and Telegram calls are patched; nothing here contacts Paddle.

    python -m pytest tests/test_paddle_checkout_write_safety.py -q
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.check_paddle_checkout_status as cpcs  # noqa: E402

T0 = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)


class _Tmp(unittest.TestCase):
    def setUp(self):
        # These tests exercise the live-probe write path, which is off by
        # default since 2026-10-22; opt in explicitly (still fully mocked).
        _env = patch.dict("os.environ", {cpcs.LIVE_PROBE_ENV: "1"})
        _env.start()
        self.addCleanup(_env.stop)
        self._d = tempfile.TemporaryDirectory()
        self.addCleanup(self._d.cleanup)
        d = Path(self._d.name)
        self.state = d / "notifications.json"
        self.registry = d / "products.json"
        self.registry.write_text(json.dumps([{"title": "P", "price_id": "pri_1", "price": 10}]),
                                 encoding="utf-8")

    def run_all(self, now, **kw):
        return cpcs.check_and_notify_all(registry_path=self.registry, state_path=self.state, now=now, **kw)


class TestOneTransactionPerProduct(_Tmp):
    def test_failed_telegram_never_causes_a_second_transaction(self):
        with patch.object(cpcs.paddle_publisher, "load_api_key", return_value="k"), \
             patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                          return_value=({}, "https://pay.example/x")) as create, \
             patch.object(cpcs.telegram_direct, "send_telegram_message",
                          return_value={"sent": False, "error": "chat id not configured"}) as send:
            self.run_all(T0, min_interval_seconds=0)
            self.run_all(T0 + timedelta(hours=1), min_interval_seconds=0)
            self.run_all(T0 + timedelta(hours=2), min_interval_seconds=0)
        self.assertEqual(create.call_count, 1)
        self.assertEqual(send.call_count, 3)
        recorded = json.loads(self.state.read_text(encoding="utf-8"))["pri_1"]
        self.assertEqual(recorded["checkout_url"], "https://pay.example/x")
        self.assertFalse(recorded["notified"])


class TestThrottle(_Tmp):
    def test_second_call_inside_the_interval_does_not_touch_paddle(self):
        with patch.object(cpcs.paddle_publisher, "load_api_key", return_value="k"), \
             patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                          side_effect=RuntimeError("403 Client Error: Forbidden")) as create:
            self.run_all(T0)
            out = self.run_all(T0 + timedelta(minutes=10))
            self.assertTrue(out["throttled"])
            self.assertEqual(create.call_count, 1)
            self.run_all(T0 + timedelta(minutes=31))
            self.assertEqual(create.call_count, 2)

    def test_meta_lives_beside_a_custom_state_file_never_in_data(self):
        with patch.object(cpcs.paddle_publisher, "load_api_key", return_value="k"), \
             patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                          side_effect=RuntimeError("403 Forbidden")):
            self.run_all(T0)
        self.assertTrue((self.state.parent / "notifications_check_meta.json").exists())
        # The notifications file itself must NOT be created by a failed run:
        # founder_next_action treats its existence as "checkout enabled".
        self.assertFalse(self.state.exists())


class TestPermissionDeniedIsNamed(_Tmp):
    def test_403_gets_a_category_and_a_top_level_error(self):
        with patch.object(cpcs.paddle_publisher, "load_api_key", return_value="k"), \
             patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                          side_effect=RuntimeError("HTTP 403: You aren't permitted to perform this request.")):
            out = self.run_all(T0)
        self.assertFalse(out["success"])
        self.assertEqual(out["results"][0]["error_category"], "PADDLE_PERMISSION_DENIED")
        self.assertIn("PADDLE_PERMISSION_DENIED", out["error"])


class TestReadersNeverWrite(_Tmp):
    def test_recorded_status_reads_state_only(self):
        self.state.write_text(json.dumps({"pri_1": {"checkout_url": "https://pay.example/x"}}), encoding="utf-8")
        with patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                          side_effect=AssertionError("must not call Paddle")):
            out = cpcs.recorded_checkout_status(state_path=self.state)
        self.assertTrue(out["read_only"])
        self.assertTrue(out["results"][0]["checkout_ready"])

    def test_human_gate_orchestrator_never_runs_the_live_check(self):
        import autonomous_commerce_ops as aco
        with patch.object(cpcs, "check_and_notify_all", side_effect=AssertionError("live write path")), \
             patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                          side_effect=AssertionError("must not call Paddle")):
            gates = aco.human_gate_orchestrator()["gates"]
        paddle = [g for g in gates if g["gate_id"] == "GATE-PADDLE-ONBOARDING"][0]
        self.assertIn(paddle["status"], ("BLOCKING", "READY_FOR_VERIFICATION"))


class TestLiveProbeOffByDefault(_Tmp):
    """Phase 2 step 1 (2026-10-22): no transaction is created unless asked."""

    def setUp(self):
        super().setUp()
        _env = patch.dict("os.environ", {cpcs.LIVE_PROBE_ENV: ""})
        _env.start()
        self.addCleanup(_env.stop)

    def test_default_run_never_creates_a_transaction(self):
        with patch.object(cpcs.paddle_publisher, "load_api_key", return_value="k"), \
             patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                          side_effect=AssertionError("must not call Paddle")):
            out = self.run_all(T0)
        self.assertTrue(out["success"])
        self.assertTrue(out["live_probe_disabled"])
        self.assertTrue(out["results"][0]["live_probe_disabled"])
        self.assertIsNone(out["results"][0]["checkout_ready"])
        self.assertNotIn("error", out)
        self.assertFalse(self.state.exists())
        self.assertFalse((self.state.parent / "notifications_check_meta.json").exists())

    def test_explicit_opt_in_still_probes(self):
        with patch.object(cpcs.paddle_publisher, "load_api_key", return_value="k"), \
             patch.object(cpcs.paddle_publisher, "create_checkout_transaction",
                          side_effect=RuntimeError("403 Forbidden")) as create:
            self.run_all(T0, allow_live_probe=True)
        self.assertEqual(create.call_count, 1)

    def test_env_flag_values(self):
        self.assertTrue(cpcs.live_probe_allowed({cpcs.LIVE_PROBE_ENV: "1"}))
        self.assertFalse(cpcs.live_probe_allowed({}))
        self.assertFalse(cpcs.live_probe_allowed({cpcs.LIVE_PROBE_ENV: "0"}))


if __name__ == "__main__":
    unittest.main()
