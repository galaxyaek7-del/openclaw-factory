"""Tests for safe_mode.py (Global Trust & Resilience Layer, Round 2,
2026-07-29): real per-subsystem isolation, generalizing this factory's
existing per-arm circuit-breaker pattern.

Runs with stdlib unittest. Never touches the real
data/safe_mode_state.json or data/publish_protection_state.json -- every
test passes explicit temp paths / mocks.

    python -m unittest tests.test_safe_mode -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import safe_mode as sm


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    return path


_HEALTHY_PROTECTION_STATUS = {
    "arms": {},
    "global": {"emergency_stopped": False, "emergency_reason": None, "emergency_stopped_at": None, "emergency_triggered_by": None},
}


class BaseSafeModeTest(unittest.TestCase):
    def setUp(self):
        self.state_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.state_path):
            os.remove(self.state_path)


class TestMarkAndClearSubsystemUnstable(BaseSafeModeTest):
    def test_mark_unstable_records_a_real_reason_and_trigger(self):
        record = sm.mark_subsystem_unstable("ai_generation", "Groq real timeout rate spiking", triggered_by="system", state_path=self.state_path)
        self.assertTrue(record["unstable"])
        self.assertEqual(record["reason"], "Groq real timeout rate spiking")
        self.assertEqual(record["triggered_by"], "system")
        self.assertIsNotNone(record["since"])

    def test_clear_restores_the_safe_default(self):
        sm.mark_subsystem_unstable("market_intelligence", "test", state_path=self.state_path)
        record = sm.clear_subsystem_unstable("market_intelligence", state_path=self.state_path)
        self.assertFalse(record["unstable"])
        self.assertIsNone(record["reason"])

    def test_unrecognized_subsystem_raises(self):
        with self.assertRaises(ValueError):
            sm.mark_subsystem_unstable("not_a_real_subsystem", "x", state_path=self.state_path)

    def test_marketplace_publishing_cannot_be_marked_directly(self):
        with self.assertRaises(ValueError):
            sm.mark_subsystem_unstable("marketplace_publishing", "x", state_path=self.state_path)

    def test_marketplace_publishing_cannot_be_cleared_directly(self):
        with self.assertRaises(ValueError):
            sm.clear_subsystem_unstable("marketplace_publishing", state_path=self.state_path)

    def test_marking_one_subsystem_never_affects_another(self):
        sm.mark_subsystem_unstable("ai_generation", "test", state_path=self.state_path)
        state = sm._load_state(self.state_path)
        self.assertFalse(state["market_intelligence"]["unstable"])


class TestIsSubsystemSafeMode(BaseSafeModeTest):
    def test_stable_subsystem_is_honestly_false(self):
        self.assertFalse(sm.is_subsystem_safe_mode("ai_generation", state_path=self.state_path))

    def test_marked_subsystem_reports_true(self):
        sm.mark_subsystem_unstable("market_intelligence", "test", state_path=self.state_path)
        self.assertTrue(sm.is_subsystem_safe_mode("market_intelligence", state_path=self.state_path))

    def test_unrecognized_subsystem_raises(self):
        with self.assertRaises(ValueError):
            sm.is_subsystem_safe_mode("not_a_real_subsystem", state_path=self.state_path)

    @patch("channels.publish_protection.list_publish_protection_status")
    def test_marketplace_publishing_reads_the_real_publish_protection_state(self, mock_status):
        mock_status.return_value = {
            "arms": {}, "global": {"emergency_stopped": True, "emergency_reason": "x", "emergency_stopped_at": "t", "emergency_triggered_by": "founder"},
        }
        self.assertTrue(sm.is_subsystem_safe_mode("marketplace_publishing"))

    @patch("channels.publish_protection.list_publish_protection_status")
    def test_marketplace_publishing_honestly_stable_when_protection_layer_is_healthy(self, mock_status):
        mock_status.return_value = _HEALTHY_PROTECTION_STATUS
        self.assertFalse(sm.is_subsystem_safe_mode("marketplace_publishing"))


class TestListSafeModeStatus(BaseSafeModeTest):
    @patch("channels.publish_protection.list_publish_protection_status")
    def test_all_stable_reports_no_subsystem_unstable(self, mock_status):
        mock_status.return_value = _HEALTHY_PROTECTION_STATUS
        result = sm.list_safe_mode_status(state_path=self.state_path)
        self.assertFalse(result["any_subsystem_unstable"])
        self.assertFalse(result["ai_generation"]["unstable"])
        self.assertFalse(result["marketplace_publishing"]["unstable"])

    @patch("channels.publish_protection.list_publish_protection_status")
    def test_one_independent_subsystem_unstable_is_reflected(self, mock_status):
        mock_status.return_value = _HEALTHY_PROTECTION_STATUS
        sm.mark_subsystem_unstable("ai_generation", "real failure", state_path=self.state_path)
        result = sm.list_safe_mode_status(state_path=self.state_path)
        self.assertTrue(result["any_subsystem_unstable"])
        self.assertTrue(result["ai_generation"]["unstable"])
        self.assertFalse(result["market_intelligence"]["unstable"])

    @patch("channels.publish_protection.list_publish_protection_status")
    def test_marketplace_publishing_unstable_is_reflected_via_real_passthrough(self, mock_status):
        mock_status.return_value = {
            "arms": {}, "global": {"emergency_stopped": True, "emergency_reason": "real reason", "emergency_stopped_at": "t", "emergency_triggered_by": "founder"},
        }
        result = sm.list_safe_mode_status(state_path=self.state_path)
        self.assertTrue(result["any_subsystem_unstable"])
        self.assertTrue(result["marketplace_publishing"]["unstable"])
        self.assertEqual(result["marketplace_publishing"]["reason"], "real reason")


class TestCorruptOrMissingState(BaseSafeModeTest):
    def test_missing_file_never_raises(self):
        # _temp_path() in setUp already ensures the file does not exist.
        self.assertFalse(sm.is_subsystem_safe_mode("ai_generation", state_path=self.state_path))

    def test_corrupt_file_falls_back_to_default_never_raises(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            f.write("not valid json {{{")
        self.assertFalse(sm.is_subsystem_safe_mode("ai_generation", state_path=self.state_path))


if __name__ == "__main__":
    unittest.main()
