"""Tests for capital_efficiency.py (ADR-206, Phase 16, 2026-08-08).

    python -m unittest tests.test_capital_efficiency -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import capital_efficiency as ce


def _write_finance(tmp, sales):
    path = os.path.join(tmp, "finance_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"sales": sales}, f)
    return path


def _write_ai_cost_log(tmp, costs):
    path = os.path.join(tmp, "ai_cost_log.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for c in costs:
            f.write(json.dumps({"cost_usd": c}) + "\n")
    return path


class TestCapitalEfficiencyReport(unittest.TestCase):
    def test_revenue_per_ai_cost_computed_when_both_real(self):
        with tempfile.TemporaryDirectory() as tmp:
            finance_path = _write_finance(tmp, [{"platform": "Paddle", "amount": 100, "product": "X"}])
            cost_path = _write_ai_cost_log(tmp, [0.5, 0.5])
            r = ce.capital_efficiency_report(finance_path=finance_path, ai_cost_log_path=cost_path)
            self.assertEqual(r["ratios"]["revenue_per_ai_cost"]["value"], 100.0)

    def test_zero_revenue_still_computes_a_real_zero_ratio(self):
        with tempfile.TemporaryDirectory() as tmp:
            finance_path = _write_finance(tmp, [])
            cost_path = _write_ai_cost_log(tmp, [0.5])
            r = ce.capital_efficiency_report(finance_path=finance_path, ai_cost_log_path=cost_path)
            self.assertEqual(r["ratios"]["revenue_per_ai_cost"]["value"], 0.0)

    def test_missing_ai_cost_log_is_honestly_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            finance_path = _write_finance(tmp, [])
            r = ce.capital_efficiency_report(finance_path=finance_path, ai_cost_log_path=os.path.join(tmp, "does_not_exist.jsonl"))
            self.assertEqual(r["ratios"]["revenue_per_ai_cost"]["status"], "UNKNOWN")

    def test_never_fabricates_untracked_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            finance_path = _write_finance(tmp, [])
            r = ce.capital_efficiency_report(finance_path=finance_path)
            for key in ("revenue_per_development_effort", "revenue_per_marketing_cost", "revenue_per_human_intervention"):
                self.assertEqual(r["ratios"][key]["status"], "UNKNOWN", key)

    def test_test_smoke_record_filtered_from_revenue(self):
        with tempfile.TemporaryDirectory() as tmp:
            finance_path = _write_finance(tmp, [{"platform": "Paddle", "amount": 150, "product": "contract-test-ladder-DELETE-ME"}])
            r = ce.capital_efficiency_report(finance_path=finance_path)
            self.assertEqual(r["total_revenue_usd"], 0)


if __name__ == "__main__":
    unittest.main()
