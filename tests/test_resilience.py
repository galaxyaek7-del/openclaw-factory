"""Resilience Tests (Global Trust & Resilience Layer, Round 9,
2026-07-29): "continuously simulate API failures, marketplace downtime,
payment failures, network interruptions, AI provider outages, database
corruption, human mistakes. The company must recover automatically
whenever possible."

This is a real, mocked fault-injection suite -- never a live chaos
system running against real production data (this factory has no
scheduler and no staging environment; fuzzing production would be
reckless, not resilient). Every scenario here exercises REAL recovery
code that already exists elsewhere in this factory -- this suite adds
cross-cutting, multi-module integration checks that no single module's
own unit tests already prove (isolation across arms during a real
failure, consistency of the "corrupt file -> safe default" contract
across independently-built modules, and the real startup-recovery
classification path) -- it does not re-test what channels/base_arm.py,
factory_state.py, recovery/startup_check.py, etc. already cover in their
own dedicated test files (tests/test_distributor.py,
tests/test_factory_state.py, tests/test_startup_check.py).

Never touches any real data/*.json(l) file -- every test passes explicit
temp paths or mocks.

    python -m unittest tests.test_resilience -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import distributor
import factory_state
from channels import registry as channel_registry
from channels import publish_protection
from channels.base_arm import PublishResult
from schemas.product import Product
import safe_mode
from recovery import startup_check


def _temp_path(suffix=".json"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _fake_product(source_id="PROD-resilience-1"):
    return Product(
        title="t", subtitle="", description="d", price_usd=19.0, file_path="/fake/path.pdf",
        cover_path=None, tags=[], language="ar", source_id=source_id, raw_price_hint=19.0,
        needs_pricing=False, price_source="profit_raw",
    )


class TestMarketplacePublishFailureIsolation(unittest.TestCase):
    """One real arm failing (simulated marketplace downtime/timeout)
    must never affect another -- Constitution §7 Self-Healing: 'if one
    module fails: continue production where possible, report the
    failure, never terminate the whole factory'."""

    def setUp(self):
        self._saved_arms = channel_registry.all_arms()
        channel_registry.clear()
        self.ledger_path = _temp_path(".jsonl")
        self.protection_state_path = _temp_path(".json")
        self._orig_enqueue_retry = factory_state.enqueue_retry
        self._enqueued = []
        factory_state.enqueue_retry = lambda task, error, path=None: self._enqueued.append((task, str(error)))

    def tearDown(self):
        factory_state.enqueue_retry = self._orig_enqueue_retry
        channel_registry.clear()
        for a in self._saved_arms:
            channel_registry.register(a)
        for p in (self.ledger_path, self.protection_state_path):
            if os.path.exists(p):
                os.remove(p)

    def _register_fake_arm(self, name, publish_result):
        fake_arm = MagicMock()
        fake_arm.name = name
        fake_arm.supports.return_value = True
        fake_arm.publish.return_value = publish_result
        channel_registry.register(fake_arm)
        return fake_arm

    def test_one_arm_timing_out_never_blocks_a_healthy_arm(self):
        self._register_fake_arm("gumroad", PublishResult(
            ok=False, platform="gumroad", product_id=None, url=None,
            error="Gumroad API request failed: timeout", dry_run=False,
        ))
        healthy_arm = self._register_fake_arm("etsy", PublishResult(
            ok=True, platform="etsy", product_id="e1", url="http://x", error=None, dry_run=False,
        ))
        outcomes = distributor.distribute(
            _fake_product(), dry_run=False, ledger_path=self.ledger_path,
            protection_state_path=self.protection_state_path,
        )
        healthy_arm.publish.assert_called_once()
        etsy_outcome = next(o for o in outcomes if o["arm"] == "etsy")
        self.assertTrue(etsy_outcome["ok"])
        # The real failure is still honestly recorded, and remembered for retry.
        self.assertEqual(len(self._enqueued), 1)
        self.assertIn("gumroad", self._enqueued[0][0])

    def test_a_failing_arm_recovers_via_a_later_real_success(self):
        """Simulates a transient marketplace outage clearing -- the same
        real arm succeeding on a later real attempt must fully clear its
        cooldown/failure state (no permanent penalty for a real transient
        failure)."""
        publish_protection.note_publish_outcome("gumroad", False, state_path=self.protection_state_path)
        publish_protection.note_publish_outcome("gumroad", True, state_path=self.protection_state_path)
        status = publish_protection.list_publish_protection_status(state_path=self.protection_state_path)
        self.assertEqual(status["arms"]["gumroad"]["consecutive_failures"], 0)


class TestCorruptedStateNeverCrashesAnyReader(unittest.TestCase):
    """Database/file corruption: the same real 'corrupt file -> safe,
    honest default, never raise' contract must hold consistently across
    every independently-built state module in this factory -- not just
    provably true for one of them in isolation."""

    def setUp(self):
        self.path = _temp_path(".json")
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{not valid json at all")

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_factory_state_degrades_to_safe_default(self):
        state = factory_state.load_state(self.path)
        self.assertEqual(state["pending_retries"], [])

    def test_publish_protection_degrades_to_safe_default(self):
        result = publish_protection.check_publish_allowed("gumroad", state_path=self.path)
        self.assertTrue(result["allowed"])

    def test_safe_mode_degrades_to_safe_default(self):
        self.assertFalse(safe_mode.is_subsystem_safe_mode("ai_generation", state_path=self.path))

    def test_none_of_these_real_readers_ever_raise_on_the_same_corrupt_file(self):
        """The real cross-cutting property: one single corrupt file must
        never take down any of these three independently-built modules."""
        try:
            factory_state.load_state(self.path)
            publish_protection.check_publish_allowed("gumroad", state_path=self.path)
            safe_mode.is_subsystem_safe_mode("ai_generation", state_path=self.path)
        except Exception as e:  # pragma: no cover - the whole point of this test
            self.fail(f"a corrupt state file crashed a real reader: {e}")


class TestUncleanShutdownRecoveryClassification(unittest.TestCase):
    """A real human mistake / crash mid-operation must classify honestly
    (RECOVERING when safe to auto-resume, NEEDS_CONFIRMATION when a real
    external side effect might be in an unknown state) -- never silently
    resume when it isn't actually safe to (fail closed)."""

    def setUp(self):
        self.state_path = _temp_path(".json")
        self.timeline_path = _temp_path(".jsonl")

    def tearDown(self):
        for p in (self.state_path, self.timeline_path):
            if os.path.exists(p):
                os.remove(p)

    def test_clean_start_is_always_healthy(self):
        result = startup_check.check_startup_safety(was_stale_lock=False, state_path=self.state_path)
        self.assertEqual(result["classification"], "HEALTHY")

    def test_stale_lock_with_nothing_in_flight_is_a_real_safe_auto_recovery(self):
        result = startup_check.check_startup_safety(was_stale_lock=True, state_path=self.state_path, timeline_path=self.timeline_path)
        self.assertEqual(result["classification"], "RECOVERING")

    def test_stale_lock_mid_risky_publish_step_fails_closed(self):
        factory_state.set_current_task("golden_hunter_tick", step="hunt", path=self.state_path)
        result = startup_check.check_startup_safety(was_stale_lock=True, state_path=self.state_path, timeline_path=self.timeline_path)
        self.assertEqual(result["classification"], "NEEDS_CONFIRMATION")

    def test_recovery_info_is_really_persisted_not_just_returned(self):
        """The classification isn't just an in-memory return value -- it's
        a real, durable record a later `GET /health`/founder review can
        actually see."""
        startup_check.check_startup_safety(was_stale_lock=True, state_path=self.state_path, timeline_path=self.timeline_path)
        state = factory_state.load_state(self.state_path)
        self.assertTrue(state["recovery_info"]["interrupted"])

    def test_resolve_recovery_really_clears_the_persisted_flag(self):
        startup_check.check_startup_safety(was_stale_lock=True, state_path=self.state_path, timeline_path=self.timeline_path)
        startup_check.resolve_recovery(self.state_path)
        state = factory_state.load_state(self.state_path)
        self.assertFalse(state["recovery_info"]["interrupted"])


if __name__ == "__main__":
    unittest.main()
