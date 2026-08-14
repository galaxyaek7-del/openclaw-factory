"""Tests for revenue_intelligence.py — the KEEP/SCALE/RETEST/PAUSE/REMOVE
decision layer over REAL affiliate data.

    python -m unittest tests.test_revenue_intelligence -v
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from revenue_intelligence import (
    AffiliateMetrics,
    decide_on_program,
    decide_on_many,
    portfolio_decision_summary,
    metrics_from_real_ledgers,
    MIN_CLICKS_TO_DECIDE,
    MIN_CONVERSIONS_TO_SCALE,
    EPC_SCALE_FLOOR,
)


def _now():
    return datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc)


def _metric(**kwargs):
    defaults = dict(
        program_id="CO-test-affiliate",
        program_name="Test Program",
        verification_status="VERIFIED",
        real_clicks=0,
        real_conversions=0,
        real_commission_usd=0.0,
        first_click_at=None,
        last_click_at=None,
        recurring_commission=False,
    )
    defaults.update(kwargs)
    return AffiliateMetrics(**defaults)


class TestNoData(unittest.TestCase):
    def test_zero_clicks_is_insufficient_data(self):
        d = decide_on_program(_metric(), now=_now())
        self.assertEqual(d.decision, "INSUFFICIENT_DATA")
        self.assertIn("لا نقرات", d.reason)

    def test_few_clicks_is_keep_not_guess(self):
        d = decide_on_program(_metric(real_clicks=2), now=_now())
        self.assertEqual(d.decision, "KEEP")
        self.assertIn("KEEP".lower(), d.decision.lower())


class TestScale(unittest.TestCase):
    def test_scale_requires_real_conversions_and_epc_floor(self):
        d = decide_on_program(
            _metric(real_clicks=100, real_conversions=5, real_commission_usd=150.0),
            now=_now(),
        )
        self.assertEqual(d.decision, "SCALE")
        self.assertIn("وسّع", d.reason)

    def test_conversions_but_low_epc_keeps(self):
        d = decide_on_program(
            _metric(real_clicks=100, real_conversions=3, real_commission_usd=1.5),
            now=_now(),
        )
        self.assertEqual(d.decision, "KEEP")
        self.assertIn("EPC", d.reason)


class TestZeroConversion(unittest.TestCase):
    def test_clicks_within_window_keeps(self):
        d = decide_on_program(
            _metric(real_clicks=10, first_click_at=(_now() - timedelta(days=5)).isoformat()),
            now=_now(),
        )
        self.assertEqual(d.decision, "KEEP")
        self.assertIn("نافذة إعادة الاختبار", d.reason)

    def test_clicks_past_retest_window_retests(self):
        d = decide_on_program(
            _metric(real_clicks=10, first_click_at=(_now() - timedelta(days=45)).isoformat()),
            now=_now(),
        )
        self.assertEqual(d.decision, "RETEST")
        self.assertIn("غيّر الزاوية", d.reason)

    def test_clicks_past_long_window_removes(self):
        d = decide_on_program(
            _metric(real_clicks=10, first_click_at=(_now() - timedelta(days=120)).isoformat()),
            now=_now(),
        )
        self.assertEqual(d.decision, "REMOVE")
        self.assertIn("أزل", d.reason)


class TestSummary(unittest.TestCase):
    def test_summary_counts_only_real_decisions(self):
        decisions = decide_on_many([
            _metric(program_id="a", real_clicks=0),
            _metric(program_id="b", real_clicks=100, real_conversions=5, real_commission_usd=150.0),
            _metric(program_id="c", real_clicks=10, first_click_at=(_now() - timedelta(days=120)).isoformat()),
        ], now=_now())
        summary = portfolio_decision_summary(decisions)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["by_decision"]["INSUFFICIENT_DATA"], 1)
        self.assertEqual(summary["by_decision"]["SCALE"], 1)
        self.assertEqual(summary["by_decision"]["REMOVE"], 1)
        self.assertEqual(summary["scale_candidates"], ["b"])


class TestRealLedgerAdapter(unittest.TestCase):
    def test_metrics_from_real_ledgers_never_uses_test_rows(self):
        # Write a tiny REAL click ledger and a TEST-only commission ledger;
        # the TEST commission must never count as a real conversion.
        click_path = None
        comm_path = None
        try:
            fd, click_path = tempfile.mkstemp(suffix=".jsonl")
            os.close(fd)
            os.remove(click_path)
            with open(click_path, "w", encoding="utf-8") as f:
                f.write('{"product_id": "CO-x-affiliate", "timestamp": "2026-08-10T10:00:00+00:00", "referrer": null}\n')
                f.write('{"product_id": "CO-x-affiliate", "timestamp": "2026-08-11T10:00:00+00:00", "referrer": null}\n')

            fd2, comm_path = tempfile.mkstemp(suffix=".jsonl")
            os.close(fd2)
            os.remove(comm_path)
            with open(comm_path, "w", encoding="utf-8") as f:
                f.write('{"opportunity_id": "CO-x-affiliate", "environment": "TEST", "commission_status": "PAID", "gross_commission": 500.0}\n')
                f.write('{"opportunity_id": "CO-x-affiliate", "environment": "REAL", "commission_status": "PAID", "gross_commission": 40.0}\n')

            metrics = metrics_from_real_ledgers(click_ledger_path=click_path, commission_ledger_path=comm_path, portfolio=[])
            m = metrics["CO-x-affiliate"]
            self.assertEqual(m.real_clicks, 2)
            self.assertEqual(m.real_conversions, 1)  # only the REAL row
            self.assertEqual(m.real_commission_usd, 40.0)  # never 540.0
        finally:
            for p in (click_path, comm_path):
                if p and os.path.exists(p):
                    os.remove(p)


if __name__ == "__main__":
    unittest.main()