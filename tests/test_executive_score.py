"""Tests for executive_score.py (Executive Intelligence Core, Round 6,
2026-07-29): a transparent, real-component composite -- never a
fabricated single number, following value_engine.py/reality.py's own
established precedent.

Every network/subprocess-touching real call is mocked/injected --
_check_npm_audit() itself is never invoked live here.

    python -m unittest tests.test_executive_score -v
"""

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

import executive_score as es


def _write_inspections_log(entries):
    fd, path = tempfile.mkstemp(suffix=".log")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return path


class TestDualInspectionPassRate(unittest.TestCase):
    def test_missing_log_is_honest_none(self):
        result = es._dual_inspection_pass_rate("C:/definitely/not/a/real/inspections.log")
        self.assertIsNone(result)

    def test_real_entries_compute_a_real_rate(self):
        path = _write_inspections_log([{"passed": True}, {"passed": True}, {"passed": False}, {"passed": False}])
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        result = es._dual_inspection_pass_rate(path)
        self.assertEqual(result, {"total": 4, "passed": 2, "rate": 50})

    def test_malformed_lines_never_crash_and_are_skipped(self):
        path = _write_inspections_log([{"passed": True}])
        with open(path, "a", encoding="utf-8") as f:
            f.write("not valid json\n")
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        result = es._dual_inspection_pass_rate(path)
        self.assertEqual(result["total"], 1)


class TestProductionQuality(unittest.TestCase):
    def test_no_log_is_honestly_unknown(self):
        result = es._production_quality("C:/definitely/not/a/real/inspections.log")
        self.assertEqual(result["value"], "Unknown")

    def test_real_log_produces_a_real_numeric_value(self):
        path = _write_inspections_log([{"passed": True}, {"passed": True}])
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        result = es._production_quality(path)
        self.assertEqual(result["value"], 100)


class TestTechnicalDebt(unittest.TestCase):
    def test_unknown_answer_stays_unknown(self):
        with patch("strategic_intelligence.technical_debt.components_at_risk_of_technical_debt",
                   return_value={"answer": "Unknown", "reason": "test reason"}):
            result = es._technical_debt()
        self.assertEqual(result["value"], "Unknown")

    def test_real_at_risk_components_stay_unknown_numerically_but_disclose_the_real_list(self):
        with patch("strategic_intelligence.technical_debt.components_at_risk_of_technical_debt",
                   return_value={"answer": ["gumroad_arm"], "evidence": [], "source": "test"}):
            result = es._technical_debt()
        self.assertEqual(result["value"], "Unknown", "no real total-component baseline exists to turn this into a percentage")
        self.assertEqual(result["components_at_risk"], ["gumroad_arm"])


class TestSecurityHealth(unittest.TestCase):
    def test_no_dependencies_anywhere_is_honestly_unknown(self):
        with patch("ai_doctor._check_python_pinning", return_value={"checked": 0, "pinned": 0, "unpinned": []}), \
             patch("ai_doctor._check_node_pinning", return_value={"checked": 0, "pinned": 0, "unpinned": []}):
            result = es._security_health()
        self.assertEqual(result["value"], "Unknown")

    def test_real_pinning_ratio_is_averaged_across_both_ecosystems(self):
        with patch("ai_doctor._check_python_pinning", return_value={"checked": 4, "pinned": 4, "unpinned": []}), \
             patch("ai_doctor._check_node_pinning", return_value={"checked": 4, "pinned": 0, "unpinned": ["a", "b", "c", "d"]}):
            result = es._security_health()
        self.assertEqual(result["value"], 50)


class TestDeliveryQuality(unittest.TestCase):
    def test_ok_verdict_maps_to_100(self):
        with patch("reality.scorecard", return_value={"verdict": "OK"}):
            result = es._delivery_quality()
        self.assertEqual(result["value"], 100)

    def test_critical_verdict_maps_to_0(self):
        with patch("reality.scorecard", return_value={"verdict": "CRITICAL", "reason": "x"}):
            result = es._delivery_quality()
        self.assertEqual(result["value"], 0)

    def test_unexpected_verdict_is_honestly_unknown_never_guessed(self):
        with patch("reality.scorecard", return_value={"verdict": "SOMETHING_NEW"}):
            result = es._delivery_quality()
        self.assertEqual(result["value"], "Unknown")


class TestAutomation(unittest.TestCase):
    def test_no_providers_is_honestly_unknown(self):
        with patch("ai_capability.registry.list_providers", return_value=[]):
            result = es._automation()
        self.assertEqual(result["value"], "Unknown")

    def test_real_configured_ratio(self):
        providers = [{"configured": True}, {"configured": False}, {"configured": False}, {"configured": False}]
        with patch("ai_capability.registry.list_providers", return_value=providers):
            result = es._automation()
        self.assertEqual(result["value"], 25)


class TestGrowth(unittest.TestCase):
    def test_discovery_maturity_is_honestly_unknown(self):
        with patch("growth_engine.growth_forecast", return_value={"maturity": "DISCOVERY", "forecast": None, "reason": "0 real sales"}):
            result = es._growth()
        self.assertEqual(result["value"], "Unknown")

    def test_real_maturity_with_no_numeric_forecast_stays_unknown(self):
        with patch("growth_engine.growth_forecast", return_value={"maturity": "REAL", "forecast": {"value": None, "reason": "needs 2 windows"}}):
            result = es._growth()
        self.assertEqual(result["value"], "Unknown")

    def test_real_numeric_forecast_is_used_when_it_exists(self):
        with patch("growth_engine.growth_forecast", return_value={"maturity": "REAL", "forecast": {"value": 12.5}}):
            result = es._growth()
        self.assertEqual(result["value"], 12.5)


class TestPublishingSafety(unittest.TestCase):
    """Global Commercial Hardening, Phase 1 (2026-07-29)."""

    def test_no_arms_recorded_yet_is_honestly_unknown(self):
        fake_status = {"arms": {}, "global": {"emergency_stopped": False}}
        with patch("channels.publish_protection.list_publish_protection_status", return_value=fake_status):
            result = es._publishing_safety()
        self.assertEqual(result["value"], "Unknown")

    def test_active_emergency_stop_is_a_real_zero_not_unknown(self):
        fake_status = {"arms": {"gumroad": {"risk_score": 0}}, "global": {"emergency_stopped": True, "emergency_reason": "test"}}
        with patch("channels.publish_protection.list_publish_protection_status", return_value=fake_status):
            result = es._publishing_safety()
        self.assertEqual(result["value"], 0)

    def test_real_risk_scores_average_into_a_real_value(self):
        fake_status = {
            "arms": {"gumroad": {"risk_score": 20}, "etsy": {"risk_score": 40}},
            "global": {"emergency_stopped": False},
        }
        with patch("channels.publish_protection.list_publish_protection_status", return_value=fake_status):
            result = es._publishing_safety()
        self.assertEqual(result["value"], 70)  # 100 - avg(20, 40)


class TestArchitectureHealth(unittest.TestCase):
    def test_always_honestly_unknown(self):
        result = es._architecture_health()
        self.assertEqual(result["value"], "Unknown")
        self.assertTrue(result["reason"])


class TestComputeExecutiveScore(unittest.TestCase):
    def test_every_sub_score_value_is_a_number_or_the_string_unknown_never_a_nested_object(self):
        result = es.compute_executive_score()
        for name, sub in result["sub_scores"].items():
            value = sub["value"]
            self.assertTrue(
                isinstance(value, (int, float)) or value == "Unknown",
                f"{name}'s value must be numeric or the literal string 'Unknown', got: {value!r}",
            )

    def test_real_call_never_throws_and_covers_all_named_sub_scores(self):
        result = es.compute_executive_score()
        for name in ("trust", "production_quality", "technical_debt", "security_health",
                     "delivery_quality", "automation", "growth", "architecture_health"):
            self.assertIn(name, result["sub_scores"])


if __name__ == "__main__":
    unittest.main()
