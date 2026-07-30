"""Tests for executive_brain.py (Executive Brain, ADR-144, 2026-07-30):
arbitrates real candidate actions from existing systems into exactly ONE
executive directive per cycle, never executes anything itself.

    python -m unittest tests.test_executive_brain -v
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

import executive_brain as eb


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _candidate(tier, action="do something", source="test"):
    return {"tier": tier, "tier_name": eb.PRIORITY_TIERS[tier], "action": action, "evidence": {}, "source": source}


class TestArbitrate(unittest.TestCase):
    def test_no_candidates_is_honest_no_action(self):
        result = eb._arbitrate([])
        self.assertEqual(result["status"], "NO_ACTION_NEEDED")

    def test_single_lowest_tier_wins(self):
        candidates = [_candidate(3), _candidate(1), _candidate(5)]
        result = eb._arbitrate(candidates)
        self.assertEqual(result["status"], "SINGLE_DIRECTIVE")
        self.assertEqual(result["tier"], 1)

    def test_tie_at_lowest_tier_is_honest_split_never_arbitrary(self):
        candidates = [_candidate(2, action="A"), _candidate(2, action="B"), _candidate(4)]
        result = eb._arbitrate(candidates)
        self.assertEqual(result["status"], "SPLIT")
        self.assertEqual(result["tier"], 2)
        self.assertEqual(len(result["candidates"]), 2)

    def test_single_candidate_at_tier_5_is_still_a_real_directive(self):
        result = eb._arbitrate([_candidate(5)])
        self.assertEqual(result["status"], "SINGLE_DIRECTIVE")
        self.assertEqual(result["tier"], 5)


class TestCandidateDirectives(unittest.TestCase):
    def _empty_inputs(self):
        brief = {"top_risks": {"resilience_active_alerts": []}, "founder_decisions_required": {"pending_decisions": [], "publish_emergency_stop": None}, "products_to_accelerate": []}
        gox = {"diversification_recommendations": []}
        cap = {"top_roi_initiatives": []}
        evo_queue = {"awaiting_approval": []}
        return brief, gox, cap, evo_queue

    def test_zero_real_signals_is_honest_zero_candidates(self):
        candidates = eb._candidate_directives(*self._empty_inputs())
        self.assertEqual(candidates, [])

    def test_active_resilience_alert_becomes_tier_1_candidate(self):
        brief, gox, cap, evo_queue = self._empty_inputs()
        brief["top_risks"]["resilience_active_alerts"] = [{"area": "test_area", "severity": "warning"}]
        candidates = eb._candidate_directives(brief, gox, cap, evo_queue)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["tier"], 1)

    def test_publish_emergency_stop_becomes_tier_1_candidate(self):
        brief, gox, cap, evo_queue = self._empty_inputs()
        brief["founder_decisions_required"]["publish_emergency_stop"] = {"reason": "test"}
        candidates = eb._candidate_directives(brief, gox, cap, evo_queue)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["tier"], 1)

    def test_evolution_queue_entry_becomes_tier_5_candidate(self):
        brief, gox, cap, evo_queue = self._empty_inputs()
        evo_queue["awaiting_approval"] = [{"proposal_id": "p1", "tool": "test tool"}]
        candidates = eb._candidate_directives(brief, gox, cap, evo_queue)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["tier"], 5)

    def test_every_candidate_cites_a_real_source(self):
        brief, gox, cap, evo_queue = self._empty_inputs()
        brief["top_risks"]["resilience_active_alerts"] = [{"area": "x", "severity": "critical"}]
        cap["top_roi_initiatives"] = [{"niche": "n1"}]
        candidates = eb._candidate_directives(brief, gox, cap, evo_queue)
        for c in candidates:
            self.assertTrue(c.get("source"), "every candidate must cite a real source, never silent")


class TestArchitectureHealthCitation(unittest.TestCase):
    def test_missing_report_is_honest_none(self):
        result = eb._architecture_health_citation(report_path="/does/not/exist.md")
        self.assertIsNone(result["overall_score"])

    def test_real_report_is_mechanically_parsed_never_guessed(self):
        path = _temp_path(suffix=".md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("**Date:** 2026-08-01\n\n| **Overall architecture score** | **77 / 100** | test |\n")
        result = eb._architecture_health_citation(report_path=path)
        os.remove(path)
        self.assertEqual(result["overall_score"], 77)
        self.assertEqual(result["last_reviewed"], "2026-08-01")


class TestRiskLevel(unittest.TestCase):
    def test_no_active_alerts_is_informational(self):
        result = eb._risk_level([])
        self.assertEqual(result["level"], "informational")

    def test_max_severity_among_active_alerts_wins(self):
        alerts = [{"severity": "warning"}, {"severity": "critical"}, {"severity": "warning"}]
        result = eb._risk_level(alerts)
        self.assertEqual(result["level"], "critical")


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.ledger_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)

    def test_empty_ledger_is_honest_zero(self):
        result = eb.list_executive_directives(ledger_path=self.ledger_path)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["entries"], [])

    def test_append_then_list_reads_back_most_recent_first(self):
        eb._append_ledger({"generated_at": "2026-01-01", "directive": {"status": "NO_ACTION_NEEDED"}}, ledger_path=self.ledger_path)
        eb._append_ledger({"generated_at": "2026-01-02", "directive": {"status": "NO_ACTION_NEEDED"}}, ledger_path=self.ledger_path)
        result = eb.list_executive_directives(ledger_path=self.ledger_path)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["entries"][0]["generated_at"], "2026-01-02", "most recent must be first")


class TestBuildExecutiveDirectiveIntegration(unittest.TestCase):
    """Full-chain test with every real heavy dependency mocked -- never
    hits real data files or the real ~55-60s live compute path."""

    def _mock_brief(self, alerts=None):
        return {
            "company_health": {"resilience_score": 90},
            "top_risks": {"resilience_active_alerts": alerts or []},
            "top_opportunities": [],
            "products_to_accelerate": [],
            "founder_decisions_required": {"pending_decisions": [], "pending_evolution_proposals": [], "publish_emergency_stop": None},
        }

    @patch("channels.ledger.revenue_trend")
    @patch("evolution_queue.list_evolution_queue")
    @patch("capital_allocation_engine.build_capital_allocation_dashboard")
    @patch("global_opportunity_exchange.build_global_opportunity_exchange_dashboard")
    @patch("strategic_intelligence_core.build_executive_brief")
    def test_record_ledger_false_never_writes(self, mock_brief, mock_gox, mock_cap, mock_evo, mock_rev):
        mock_brief.return_value = self._mock_brief()
        mock_gox.return_value = {"market_health": {}, "diversification_recommendations": []}
        mock_cap.return_value = {"top_roi_initiatives": []}
        mock_evo.return_value = {"awaiting_approval": [], "stage_distribution": {}}
        mock_rev.return_value = {"recent_7d_revenue_usd": 0, "trailing_daily_avg_usd": None, "note": None}

        ledger_path = _temp_path()
        record = eb.build_executive_directive(ledger_path=ledger_path, record_ledger=False)
        self.assertEqual(record["directive"]["status"], "NO_ACTION_NEEDED")
        self.assertTrue(record["requires_founder_approval"], "must always require founder approval -- never auto-executes")
        self.assertFalse(os.path.exists(ledger_path), "record_ledger=False must never write to the permanent ledger")

    @patch("channels.ledger.revenue_trend")
    @patch("evolution_queue.list_evolution_queue")
    @patch("capital_allocation_engine.build_capital_allocation_dashboard")
    @patch("global_opportunity_exchange.build_global_opportunity_exchange_dashboard")
    @patch("strategic_intelligence_core.build_executive_brief")
    def test_record_ledger_true_writes_exactly_once(self, mock_brief, mock_gox, mock_cap, mock_evo, mock_rev):
        mock_brief.return_value = self._mock_brief(alerts=[{"area": "test", "severity": "warning"}])
        mock_gox.return_value = {"market_health": {}, "diversification_recommendations": []}
        mock_cap.return_value = {"top_roi_initiatives": []}
        mock_evo.return_value = {"awaiting_approval": [], "stage_distribution": {}}
        mock_rev.return_value = {"recent_7d_revenue_usd": 0, "trailing_daily_avg_usd": None, "note": None}

        ledger_path = _temp_path()
        record = eb.build_executive_directive(ledger_path=ledger_path, record_ledger=True)
        self.assertEqual(record["directive"]["status"], "SINGLE_DIRECTIVE")
        self.assertEqual(record["directive"]["tier"], 1)
        self.assertEqual(record["current_mission"], record["directive"]["action"])

        result = eb.list_executive_directives(ledger_path=ledger_path)
        self.assertEqual(result["count"], 1, "exactly one ledger entry per real generation call")
        os.remove(ledger_path)


if __name__ == "__main__":
    unittest.main()
