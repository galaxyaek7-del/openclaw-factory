"""Tests for strategic_intelligence/ (ADR-054).

Runs with stdlib unittest. Every function reads only from temp-file-
isolated stores passed explicitly — never the real data/*.jsonl files.
Strictly read-only: no test here ever calls anything that executes,
publishes, or mutates production state.

    python -m unittest tests.test_strategic_intelligence -v
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import ledger as sales_ledger
from decision_engine import store as decision_store
from decision_engine.types import Decision, Outcome, make_decision_id

from strategic_intelligence import (
    bottleneck_effort,
    channel_value,
    decision_patterns,
    rejection_patterns,
    report,
    technical_debt,
)


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _decision(niche, status, ai_ceo_decision, score=80, decided_at=None, dimension_scores=None):
    decided_at = decided_at or datetime.now(timezone.utc).isoformat()
    return Decision(
        decision_id=make_decision_id(niche, "tier4", decided_at), niche=niche, tier="tier4",
        decided_at=decided_at, status=status, ai_ceo_decision=ai_ceo_decision,
        opportunity_score=score, opportunity_score_accepted=(status == "ACCEPTED"),
        reasoning=["real evidence"],
        evaluation_snapshot={"dimension_scores": dimension_scores or {}},
    )


class TestDecisionPatternsUnknownWithoutData(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

    def test_success_patterns_unknown_with_zero_real_sales(self):
        result = decision_patterns.find_success_patterns(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertEqual(result["answer"], "Unknown")

    def test_least_predictive_unknown_with_zero_real_sales(self):
        result = decision_patterns.find_least_predictive_dimensions(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertEqual(result["answer"], "Unknown")

    def test_success_patterns_real_with_enough_samples(self):
        dims_sold = {"demand": {"normalized_score": 90, "confidence": 80, "raw_data": {}, "explanation": ""}}
        dims_not_sold = {"demand": {"normalized_score": 20, "confidence": 80, "raw_data": {}, "explanation": ""}}
        for i in range(3):
            niche = f"sold niche {i}"
            d = _decision(niche, "ACCEPTED", "BUILD", dimension_scores=dims_sold)
            decision_store.append_decision(d, path=self.decisions_path)
            decision_store.append_outcome(
                Outcome(outcome_id=f"o{i}", decision_id=d.decision_id, niche=niche, recorded_at="t", matched=True, match_method="x", raw_sale_event={}),
                path=self.outcomes_path,
            )
        d2 = _decision("not sold niche", "ACCEPTED", "BUILD", dimension_scores=dims_not_sold)
        decision_store.append_decision(d2, path=self.decisions_path)

        result = decision_patterns.find_success_patterns(decisions_path=self.decisions_path, outcomes_path=self.outcomes_path)
        self.assertEqual(result["answer"], "demand")
        self.assertIn("source", result)


class TestRejectionPatterns(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    def test_no_rejections_is_unknown(self):
        result = rejection_patterns.most_frequent_rejection_reasons(decisions_path=self.decisions_path)
        self.assertEqual(result["answer"], "Unknown")

    def test_most_frequent_category_is_correctly_identified(self):
        decision_store.append_decision(_decision("n1", "REJECTED", "PIVOT"), path=self.decisions_path)
        decision_store.append_decision(_decision("n2", "REJECTED", "PIVOT"), path=self.decisions_path)
        decision_store.append_decision(_decision("n3", "REJECTED", "REJECT"), path=self.decisions_path)
        result = rejection_patterns.most_frequent_rejection_reasons(decisions_path=self.decisions_path)
        self.assertEqual(result["answer"], "PIVOT")
        self.assertEqual(result["counts"]["PIVOT"], 2)
        self.assertEqual(result["counts"]["REJECT"], 1)

    def test_accepted_decisions_never_counted_as_rejections(self):
        decision_store.append_decision(_decision("accepted one", "ACCEPTED", "BUILD"), path=self.decisions_path)
        result = rejection_patterns.most_frequent_rejection_reasons(decisions_path=self.decisions_path)
        self.assertEqual(result["answer"], "Unknown")


class TestBottleneckEffort(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.timeline_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.outcomes_path, self.timeline_path):
            if os.path.exists(p):
                os.remove(p)

    def test_no_bottlenecks_is_unknown(self):
        result = bottleneck_effort.most_effort_consuming_bottleneck(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path, timeline_path=self.timeline_path,
        )
        self.assertEqual(result["answer"], "Unknown")

    def test_reuses_validation_layer_reliability_not_a_second_computation(self):
        from datetime import timedelta
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        decision_store.append_decision(_decision("aging", "ACCEPTED", "BUILD", decided_at=old), path=self.decisions_path)
        result = bottleneck_effort.most_effort_consuming_bottleneck(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path, timeline_path=self.timeline_path,
        )
        self.assertEqual(result["answer"], "queue_aging")


class TestChannelValue(unittest.TestCase):
    def setUp(self):
        self.sales_ledger_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.sales_ledger_path):
            os.remove(self.sales_ledger_path)

    def test_no_real_sales_is_unknown(self):
        result = channel_value.highest_long_term_value_channel(sales_ledger_path=self.sales_ledger_path)
        self.assertEqual(result["answer"], "Unknown")

    def test_counts_real_sales_per_platform(self):
        sales_ledger.append_event({"event_type": "sale", "platform": "gumroad", "raw": {"id": "s1"}}, ledger_path=self.sales_ledger_path)
        sales_ledger.append_event({"event_type": "sale", "platform": "gumroad", "raw": {"id": "s2"}}, ledger_path=self.sales_ledger_path)
        sales_ledger.append_event({"event_type": "sale", "platform": "payhip", "raw": {"id": "s3"}}, ledger_path=self.sales_ledger_path)
        result = channel_value.highest_long_term_value_channel(sales_ledger_path=self.sales_ledger_path)
        self.assertEqual(result["answer_by_count"], "gumroad")
        self.assertEqual(result["sale_counts"]["gumroad"], 2)

    def test_missing_price_field_never_fabricates_a_revenue_total(self):
        sales_ledger.append_event({"event_type": "sale", "platform": "gumroad", "raw": {"id": "s1"}}, ledger_path=self.sales_ledger_path)
        result = channel_value.highest_long_term_value_channel(sales_ledger_path=self.sales_ledger_path)
        self.assertIsNone(result["revenue_totals"])
        self.assertEqual(result["answer_by_revenue"], "Unknown")

    def test_real_numeric_price_field_is_summed_correctly(self):
        sales_ledger.append_event({"event_type": "sale", "platform": "gumroad", "raw": {"id": "s1", "price": 999}}, ledger_path=self.sales_ledger_path)
        sales_ledger.append_event({"event_type": "sale", "platform": "gumroad", "raw": {"id": "s2", "price": 500}}, ledger_path=self.sales_ledger_path)
        result = channel_value.highest_long_term_value_channel(sales_ledger_path=self.sales_ledger_path)
        self.assertEqual(result["revenue_totals"]["gumroad"], 1499)


class TestTechnicalDebt(unittest.TestCase):
    def test_reuses_executive_intelligence_inactivity_directly(self):
        timeline_path = _temp_path()
        sales_ledger_path = _temp_path()
        try:
            result = technical_debt.components_at_risk_of_technical_debt(
                timeline_path=timeline_path, sales_ledger_path=sales_ledger_path,
            )
            self.assertIsInstance(result["answer"], list)
            self.assertTrue(len(result["answer"]) > 0)
        finally:
            for p in (timeline_path, sales_ledger_path):
                if os.path.exists(p):
                    os.remove(p)


class TestFullStrategicReport(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.timeline_path = _temp_path()
        self.sales_ledger_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.outcomes_path, self.timeline_path, self.sales_ledger_path):
            if os.path.exists(p):
                os.remove(p)

    def test_report_answers_all_six_required_questions(self):
        r = report.generate_strategic_report(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path,
        )
        for key in (
            "which_decision_patterns_lead_to_success", "most_frequent_rejection_reasons",
            "bottleneck_consuming_most_effort", "least_predictive_scoring_dimensions",
            "highest_long_term_value_channel", "components_at_risk_of_technical_debt",
        ):
            self.assertIn(key, r)
            self.assertIn("source", r[key])

    def test_markdown_renders_without_error_and_shows_unknown_honestly(self):
        r = report.generate_strategic_report(
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
            timeline_path=self.timeline_path, sales_ledger_path=self.sales_ledger_path,
        )
        md = report.render_markdown(r)
        self.assertIsInstance(md, str)
        self.assertIn("Unknown", md)

    def test_module_never_imports_anything_execution_related(self):
        """Structural guarantee: this layer must remain completely
        read-only. None of its modules should import book_generator,
        distributor, or profit_oracle's scoring internals directly —
        only already-built reporting/store modules."""
        import strategic_intelligence.bottleneck_effort as m1
        import strategic_intelligence.channel_value as m2
        import strategic_intelligence.decision_patterns as m3
        import strategic_intelligence.rejection_patterns as m4
        import strategic_intelligence.technical_debt as m5
        for mod in (m1, m2, m3, m4, m5):
            src = mod.__file__
            with open(src, encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("import book_generator", content)
            self.assertNotIn("import distributor", content)


if __name__ == "__main__":
    unittest.main()
