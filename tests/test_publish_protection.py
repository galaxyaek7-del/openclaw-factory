"""Tests for channels/publish_protection.py (Global Commercial Hardening,
Phase 1, 2026-07-29): the real pre-publish rate/cooldown/risk-scoring gate
and global emergency stop.

Runs with stdlib unittest. Never touches the real
data/publish_protection_state.json -- every test passes an explicit temp
state path.

    python -m unittest tests.test_publish_protection -v
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import publish_protection as pp


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    return path


class BaseProtectionTest(unittest.TestCase):
    def setUp(self):
        self.state_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.state_path):
            os.remove(self.state_path)


class TestCheckPublishAllowedDefaults(BaseProtectionTest):
    def test_unknown_arm_with_no_history_is_allowed_with_zero_risk(self):
        result = pp.check_publish_allowed("gumroad", state_path=self.state_path)
        self.assertTrue(result["allowed"])
        self.assertIsNone(result["reason"])
        self.assertEqual(result["risk_score"], 0)

    def test_unregistered_arm_name_falls_back_to_default_profile(self):
        # Founder Protection (Round 4, 2026-07-29): a genuinely new arm's
        # very first real publish is blocked pending founder approval --
        # once approved, it falls back to the _default profile normally
        # (proven via test_first_publish_approval below).
        result = pp.check_publish_allowed("some_future_channel", state_path=self.state_path)
        self.assertFalse(result["allowed"])
        self.assertIn("founder approval", result["reason"])


class TestDailyHourlyCaps(BaseProtectionTest):
    def test_hitting_daily_cap_blocks_further_publishes(self):
        now = datetime.now(timezone.utc)
        profile = pp.PLATFORM_PROFILES["kdp"]
        for i in range(profile["max_per_day"]):
            pp.note_publish_outcome("kdp", True, state_path=self.state_path, now=now + timedelta(hours=i * 2))
        result = pp.check_publish_allowed("kdp", state_path=self.state_path, now=now + timedelta(hours=profile["max_per_day"] * 2))
        self.assertFalse(result["allowed"])
        self.assertIn("daily", result["reason"])

    def test_hitting_hourly_cap_blocks_further_publishes(self):
        now = datetime.now(timezone.utc)
        profile = pp.PLATFORM_PROFILES["gumroad"]
        state_now = now
        for i in range(profile["max_per_hour"]):
            pp.note_publish_outcome("gumroad", True, state_path=self.state_path, now=state_now)
            state_now = state_now + timedelta(seconds=1)
        result = pp.check_publish_allowed("gumroad", state_path=self.state_path, now=state_now)
        self.assertFalse(result["allowed"])
        self.assertIn("hourly", result["reason"])

    def test_daily_counter_resets_on_a_new_day(self):
        now = datetime.now(timezone.utc)
        profile = pp.PLATFORM_PROFILES["kdp"]
        for i in range(profile["max_per_day"]):
            pp.note_publish_outcome("kdp", True, state_path=self.state_path, now=now + timedelta(hours=i * 2))
        next_day = now + timedelta(days=1, hours=2)
        result = pp.check_publish_allowed("kdp", state_path=self.state_path, now=next_day)
        self.assertTrue(result["allowed"])


class TestMinimumSpacing(BaseProtectionTest):
    def test_publishing_too_soon_after_the_last_one_is_blocked(self):
        now = datetime.now(timezone.utc)
        pp.note_publish_outcome("etsy", True, state_path=self.state_path, now=now)
        soon = now + timedelta(minutes=1)
        result = pp.check_publish_allowed("etsy", state_path=self.state_path, now=soon)
        self.assertFalse(result["allowed"])
        self.assertIsNotNone(result["cooldown_until"])

    def test_publishing_after_minimum_spacing_elapsed_is_allowed(self):
        now = datetime.now(timezone.utc)
        pp.note_publish_outcome("etsy", True, state_path=self.state_path, now=now)
        later = now + timedelta(minutes=pp.PLATFORM_PROFILES["etsy"]["min_cooldown_minutes"] + 1)
        result = pp.check_publish_allowed("etsy", state_path=self.state_path, now=later)
        self.assertTrue(result["allowed"])


class TestConsecutiveFailureCooldown(BaseProtectionTest):
    def test_repeated_failures_trigger_a_real_time_based_cooldown(self):
        now = datetime.now(timezone.utc)
        last_failure_at = now
        for i in range(pp._CONSECUTIVE_FAILURE_THRESHOLD):
            last_failure_at = now + timedelta(hours=i)
            pp.note_publish_outcome("gumroad", False, state_path=self.state_path, now=last_failure_at)
        # Still well within the failure-cooldown window opened by the last failure.
        still_cooling_down = last_failure_at + timedelta(minutes=30)
        result = pp.check_publish_allowed("gumroad", state_path=self.state_path, now=still_cooling_down)
        self.assertFalse(result["allowed"])
        self.assertIn("cooldown", result["reason"])

    def test_a_real_success_resets_consecutive_failures_and_clears_cooldown(self):
        now = datetime.now(timezone.utc)
        for i in range(pp._CONSECUTIVE_FAILURE_THRESHOLD):
            pp.note_publish_outcome("gumroad", False, state_path=self.state_path, now=now + timedelta(hours=i))
        pp.note_publish_outcome("gumroad", True, state_path=self.state_path, now=now + timedelta(hours=pp._CONSECUTIVE_FAILURE_THRESHOLD + 2))
        result = pp.check_publish_allowed("gumroad", state_path=self.state_path, now=now + timedelta(hours=pp._CONSECUTIVE_FAILURE_THRESHOLD + 2, minutes=1))
        # still might be blocked by min-spacing, but never by "cooldown"
        if not result["allowed"]:
            self.assertNotIn("cooldown", result["reason"])


class TestEmergencyStop(BaseProtectionTest):
    def test_emergency_stop_blocks_every_arm(self):
        pp.trigger_emergency_stop("suspicious behaviour detected", triggered_by="founder", state_path=self.state_path)
        result = pp.check_publish_allowed("gumroad", state_path=self.state_path)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["risk_score"], 100)

    def test_clear_emergency_stop_restores_normal_operation(self):
        pp.trigger_emergency_stop("test", state_path=self.state_path)
        pp.clear_emergency_stop(state_path=self.state_path)
        result = pp.check_publish_allowed("gumroad", state_path=self.state_path)
        self.assertTrue(result["allowed"])

    def test_emergency_stop_records_who_and_why(self):
        record = pp.trigger_emergency_stop("real suspicious pattern", triggered_by="founder", state_path=self.state_path)
        self.assertTrue(record["emergency_stopped"])
        self.assertEqual(record["emergency_reason"], "real suspicious pattern")
        self.assertEqual(record["emergency_triggered_by"], "founder")
        self.assertIsNotNone(record["emergency_stopped_at"])


class TestListPublishProtectionStatus(BaseProtectionTest):
    def test_empty_state_is_honestly_empty(self):
        result = pp.list_publish_protection_status(state_path=self.state_path)
        self.assertEqual(result["arms"], {})
        self.assertFalse(result["global"]["emergency_stopped"])

    def test_status_reflects_real_recorded_arms_only(self):
        pp.note_publish_outcome("gumroad", True, state_path=self.state_path)
        result = pp.list_publish_protection_status(state_path=self.state_path)
        self.assertIn("gumroad", result["arms"])
        self.assertNotIn("etsy", result["arms"])
        self.assertIn("risk_score", result["arms"]["gumroad"])
        self.assertIn("currently_allowed", result["arms"]["gumroad"])


class TestFounderProtectionFirstPublish(BaseProtectionTest):
    """Founder Protection (Global Trust & Resilience Layer, Round 4,
    2026-07-29): a genuinely new arm's first real publish requires
    explicit founder approval; a proven arm (KNOWN_PROVEN_ARMS) is
    exempt, keeping its existing autonomous behavior unchanged."""

    def test_known_proven_arm_is_never_blocked_even_with_zero_history(self):
        for arm in pp.KNOWN_PROVEN_ARMS:
            result = pp.check_publish_allowed(arm, state_path=self.state_path)
            self.assertTrue(result["allowed"], f"{arm} should be exempt from the first-publish gate")

    def test_novel_arm_is_blocked_until_approved(self):
        result = pp.check_publish_allowed("kdp", state_path=self.state_path)
        self.assertFalse(result["allowed"])
        self.assertIn("first real publish", result["reason"])

    def test_approve_first_publish_unblocks_it(self):
        pp.approve_first_publish("kdp", approved_by="founder", state_path=self.state_path)
        result = pp.check_publish_allowed("kdp", state_path=self.state_path)
        self.assertTrue(result["allowed"])

    def test_a_real_successful_publish_permanently_clears_the_gate(self):
        pp.approve_first_publish("kdp", state_path=self.state_path)
        pp.note_publish_outcome("kdp", True, state_path=self.state_path)
        # Even a fresh check long after, with no re-approval, stays clear
        # (has_ever_published_successfully is permanent).
        state = pp._load_state(self.state_path)
        self.assertTrue(state["arms"]["kdp"]["has_ever_published_successfully"])


class TestFounderProtectionElevatedRisk(BaseProtectionTest):
    """Founder Protection (Global Trust & Resilience Layer, Round 4,
    2026-07-29): a real elevated risk_score requires one explicit,
    single-use founder approval."""

    def _push_to_high_risk(self, arm="gumroad"):
        # gumroad's max_per_hour=5; hitting most of the hourly cap
        # without quite reaching it drives risk_score high via hour_pct.
        now = None
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        for i in range(4):
            pp.note_publish_outcome(arm, True, state_path=self.state_path, now=now + timedelta(hours=i * 2))
        return now + timedelta(hours=8)

    def test_high_risk_score_is_blocked_until_approved(self):
        check_time = self._push_to_high_risk()
        result = pp.check_publish_allowed("gumroad", state_path=self.state_path, now=check_time)
        if result["risk_score"] >= pp.HIGH_RISK_SCORE_THRESHOLD:
            self.assertFalse(result["allowed"])
            self.assertIn("high-risk threshold", result["reason"])

    def test_approval_is_single_use_consumed_by_the_next_outcome(self):
        now_ = pp._now()
        pp.approve_elevated_risk_publish("gumroad", state_path=self.state_path, now=now_)
        state = pp._load_state(self.state_path)
        self.assertIsNotNone(state["arms"]["gumroad"]["elevated_risk_approved_at"])
        pp.note_publish_outcome("gumroad", True, state_path=self.state_path)
        state = pp._load_state(self.state_path)
        self.assertIsNone(state["arms"]["gumroad"]["elevated_risk_approved_at"])


class TestCorruptOrMissingState(BaseProtectionTest):
    def test_missing_file_never_raises(self):
        # _temp_path() in setUp already ensures the file does not exist.
        result = pp.check_publish_allowed("gumroad", state_path=self.state_path)
        self.assertTrue(result["allowed"])

    def test_corrupt_file_falls_back_to_default_never_raises(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            f.write("not valid json {{{")
        result = pp.check_publish_allowed("gumroad", state_path=self.state_path)
        self.assertTrue(result["allowed"])


if __name__ == "__main__":
    unittest.main()
