import pytest
"""Tests for the Circuit Breaker integration with safe_mode.py and
channels/publish_protection.py (Founder Directive, Phase B, 2026-08-20):
deterministic safety behavior when a critical execution path is isolated.

Runs with stdlib unittest. Never touches real data state files -- every test
passes explicit temp paths.

    python -m unittest tests.test_circuit_breaker_integration -v
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
from channels import publish_protection as pp
from circuit_breaker import CircuitBreakerState

# Cycle 84: this module exercises Gumroad write logic against a mocked
# HTTP layer, so it explicitly opts in to write authorization. It was
# previously getting this from an AUTOUSE fixture that set
# FACTORY_LIVE_PUBLISH=true for the whole suite -- a hidden broad
# permission. The opt-in is now visible here, in the file that needs it.
pytestmark = pytest.mark.usefixtures("authorize_live_writes")


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    return path


_HEALTHY_PROTECTION_STATUS = {
    "arms": {},
    "global": {"emergency_stopped": False, "emergency_reason": None, "emergency_stopped_at": None, "emergency_triggered_by": None},
}


class BaseIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.safe_mode_path = _temp_path()
        self.protection_path = _temp_path()
        self.circuit_breaker_path = _temp_path()
        self.cb = CircuitBreakerState(state_path=self.circuit_breaker_path)

    def tearDown(self):
        for p in (self.safe_mode_path, self.protection_path, self.circuit_breaker_path):
            if os.path.exists(p):
                os.remove(p)


class TestSafeModeCircuitBreakerIntegration(BaseIntegrationTest):
    def test_isolated_breaker_blocks_subsystem_execution(self):
        self.cb.record_failure("ai_generation", "f1")
        self.cb.record_failure("ai_generation", "f2")
        self.cb.record_failure("ai_generation", "f3")
        self.assertTrue(
            sm.is_subsystem_safe_mode("ai_generation",
                                      state_path=self.safe_mode_path,
                                      circuit_breaker_state_path=self.circuit_breaker_path)
        )

    def test_closed_breaker_keeps_subsystem_healthy(self):
        self.assertFalse(
            sm.is_subsystem_safe_mode("market_intelligence",
                                      state_path=self.safe_mode_path,
                                      circuit_breaker_state_path=self.circuit_breaker_path)
        )

    def test_recovery_clears_breaker_gate(self):
        self.cb.record_failure("ai_generation", "f1")
        self.cb.record_failure("ai_generation", "f2")
        self.cb.record_failure("ai_generation", "f3")
        self.cb.enter_half_open("ai_generation")
        self.cb.record_recovery_success("ai_generation")
        self.assertFalse(
            sm.is_subsystem_safe_mode("ai_generation",
                                      state_path=self.safe_mode_path,
                                      circuit_breaker_state_path=self.circuit_breaker_path)
        )

    def test_list_status_exposes_circuit_breaker_state_for_founder_visibility(self):
        self.cb.record_failure("ai_generation", "f1")
        self.cb.record_failure("ai_generation", "f2")
        self.cb.record_failure("ai_generation", "f3")
        with patch("channels.publish_protection.list_publish_protection_status",
                  return_value=_HEALTHY_PROTECTION_STATUS):
            status = sm.list_safe_mode_status(state_path=self.safe_mode_path,
                                              circuit_breaker_state_path=self.circuit_breaker_path)
        self.assertEqual(status["ai_generation"]["circuit_breaker"]["state"], "ISOLATED")
        self.assertIn("circuit_breaker", status["marketplace_publishing"])

    def test_marketplace_publishing_isolated_breaker_reflected(self):
        self.cb.record_failure("marketplace_publishing", "f1")
        self.cb.record_failure("marketplace_publishing", "f2")
        self.cb.record_failure("marketplace_publishing", "f3")
        with patch("channels.publish_protection.list_publish_protection_status",
                  return_value=_HEALTHY_PROTECTION_STATUS):
            status = sm.list_safe_mode_status(state_path=self.safe_mode_path,
                                              circuit_breaker_state_path=self.circuit_breaker_path)
        self.assertEqual(status["marketplace_publishing"]["circuit_breaker"]["state"], "ISOLATED")


class TestPublishProtectionCircuitBreakerIntegration(BaseIntegrationTest):
    def test_isolated_breaker_blocks_publishing(self):
        self.cb.record_failure("marketplace_publishing", "f1")
        self.cb.record_failure("marketplace_publishing", "f2")
        self.cb.record_failure("marketplace_publishing", "f3")
        result = pp.check_publish_allowed(
            "gumroad",
            state_path=self.protection_path,
            circuit_breaker_state_path=self.circuit_breaker_path,
        )
        self.assertFalse(result["allowed"])
        self.assertIn("circuit breaker is ISOLATED", result["reason"])

    def test_closed_breaker_does_not_block_publishing(self):
        result = pp.check_publish_allowed(
            "gumroad",
            state_path=self.protection_path,
            circuit_breaker_state_path=self.circuit_breaker_path,
        )
        self.assertTrue(result["allowed"])

    def test_emergency_stop_still_blocks_even_when_breaker_closed(self):
        pp.trigger_emergency_stop("founder order", triggered_by="founder", state_path=self.protection_path)
        result = pp.check_publish_allowed(
            "gumroad",
            state_path=self.protection_path,
            circuit_breaker_state_path=self.circuit_breaker_path,
        )
        self.assertFalse(result["allowed"])
        self.assertIn("global publish emergency stop", result["reason"])

    def test_existing_callers_without_breaker_path_are_unchanged(self):
        # Backward compatibility: no circuit_breaker_state_path -> default
        # (missing file = CLOSED) -> non-blocking, same as before.
        result = pp.check_publish_allowed("gumroad", state_path=self.protection_path)
        self.assertTrue(result["allowed"])


if __name__ == "__main__":
    unittest.main()