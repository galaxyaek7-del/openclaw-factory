"""Tests for enterprise_validation.py (Enterprise Validation Phase,
ADR-166, 2026-07-31): almost entirely a citation orchestrator over
already-real validation functions -- detect_unused_services() is the
one genuinely new, real, mechanical check.

    python -m unittest tests.test_enterprise_validation -v
"""

import sys
import unittest
from unittest import mock
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import enterprise_validation as ev


class TestDetectUnusedServices(unittest.TestCase):
    def test_real_endpoint_referenced_in_server_js_not_flagged(self):
        result = ev.detect_unused_services()
        self.assertNotIn("opportunities", result["unreferenced_in_server_or_factory_loop"])

    def test_finds_a_real_daily_tick_endpoint_only_via_factory_loop(self):
        # record_daily_growth_stage_snapshot (ADR-159) is dispatched only
        # from factory_loop.js, never server.js -- must not be flagged as
        # unused just because it's absent from server.js alone.
        result = ev.detect_unused_services()
        self.assertNotIn("record_daily_growth_stage_snapshot", result["unreferenced_in_server_or_factory_loop"])

    def test_isolated_fixture_flags_a_genuinely_unreferenced_endpoint(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            server_path = os.path.join(tmp, "server.js")
            loop_path = os.path.join(tmp, "factory_loop.js")
            with open(server_path, "w", encoding="utf-8") as f:
                f.write("const x = 'opportunities';")
            with open(loop_path, "w", encoding="utf-8") as f:
                f.write("// nothing")
            result = ev.detect_unused_services(server_js_path=server_path, factory_loop_js_path=loop_path)
        self.assertIn("strategic_score", result["unreferenced_in_server_or_factory_loop"])
        self.assertNotIn("opportunities", result["unreferenced_in_server_or_factory_loop"])

    def test_reports_a_real_total_count(self):
        result = ev.detect_unused_services()
        self.assertGreater(result["total_endpoints"], 100)


class TestDetectDuplicatedLogic(unittest.TestCase):
    def test_cites_real_function_never_recomputes(self):
        fake_result = {"answer": [], "method": "x"}
        with mock.patch("enterprise_executive_brain._detect_duplicated_work", return_value=fake_result) as m:
            result = ev.detect_duplicated_logic()
            m.assert_called_once()
        self.assertEqual(result["answer"], fake_result)


class TestDetectBottlenecks(unittest.TestCase):
    def test_cites_real_evolution_report(self):
        fake_report = {"bottlenecks": {"answer": []}}
        with mock.patch("evolution_engine.build_evolution_report", return_value=fake_report):
            result = ev.detect_bottlenecks()
        self.assertEqual(result["answer"], {"answer": []})


class TestReadinessScore(unittest.TestCase):
    def test_accepts_injected_division_readiness_no_recomputation(self):
        fake = {"divisions": {}}
        result = ev.readiness_score(division_readiness=fake)
        self.assertEqual(result["answer"], fake)


if __name__ == "__main__":
    unittest.main()
