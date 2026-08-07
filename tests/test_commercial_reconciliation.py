"""Tests for commercial_reconciliation.py (ADR-202, 2026-08-07). No live
Paddle API call is ever made -- the arm's get_sales()/status() are patched.

    python -m unittest tests.test_commercial_reconciliation -v
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

import commercial_reconciliation as cr
from channels.base_arm import ArmStatus
from channels import registry


def _write_finance(tmp, sales):
    path = os.path.join(tmp, "finance_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"sales": sales}, f)
    return path


class FakeArm:
    name = "paddle"

    def __init__(self, ready=True, transactions=None, error=None):
        self._ready = ready
        self._transactions = transactions or []
        self._error = error

    def status(self):
        return ArmStatus.READY if self._ready else ArmStatus.UNAVAILABLE

    def get_sales(self):
        if self._error:
            return [], self._error
        return self._transactions, None


class TestReconcilePaddle(unittest.TestCase):
    def test_not_reconcilable_when_arm_not_ready(self):
        with patch.object(registry, "get", return_value=FakeArm(ready=False)):
            result = cr.reconcile_paddle()
        self.assertEqual(result["status"], "NOT_RECONCILABLE")

    def test_reconciled_when_both_sides_are_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [])
            with patch.object(registry, "get", return_value=FakeArm(ready=True, transactions=[])):
                result = cr.reconcile_paddle(finance_path=path)
        self.assertEqual(result["status"], "RECONCILED")
        self.assertEqual(result["discrepancies"], [])

    def test_reconciled_when_amounts_and_counts_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [
                {"platform": "Paddle", "amount": 15.5, "product": "X"},
            ])
            txn = {"id": "txn_1", "details": {"totals": {"grand_total": "1550"}}}
            with patch.object(registry, "get", return_value=FakeArm(ready=True, transactions=[txn])):
                result = cr.reconcile_paddle(finance_path=path)
        self.assertEqual(result["status"], "RECONCILED")
        self.assertEqual(result["platform_reported"]["total_usd"], 15.5)
        self.assertEqual(result["internal_reported"]["total_usd"], 15.5)

    def test_discrepancy_found_on_count_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [])  # 0 internal records
            txn = {"id": "txn_1", "details": {"totals": {"grand_total": "1550"}}}
            with patch.object(registry, "get", return_value=FakeArm(ready=True, transactions=[txn])):
                result = cr.reconcile_paddle(finance_path=path)
        self.assertEqual(result["status"], "DISCREPANCY_FOUND")
        self.assertEqual(len(result["discrepancies"]), 1)
        d = result["discrepancies"][0]
        self.assertIn("difference_usd", d)
        self.assertIn("possible_cause", d)
        self.assertIn("financial_impact", d)
        self.assertIn("confidence", d)
        self.assertIn("recommended_action", d)

    def test_discrepancy_found_on_amount_mismatch_same_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [
                {"platform": "Paddle", "amount": 10.0, "product": "X"},
            ])
            txn = {"id": "txn_1", "details": {"totals": {"grand_total": "1550"}}}  # $15.50, not $10
            with patch.object(registry, "get", return_value=FakeArm(ready=True, transactions=[txn])):
                result = cr.reconcile_paddle(finance_path=path)
        self.assertEqual(result["status"], "DISCREPANCY_FOUND")
        self.assertEqual(result["discrepancies"][0]["difference_usd"], 5.5)

    def test_never_modifies_finance_data_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [])
            with open(path, encoding="utf-8") as f:
                before = f.read()
            txn = {"id": "txn_1", "details": {"totals": {"grand_total": "1550"}}}
            with patch.object(registry, "get", return_value=FakeArm(ready=True, transactions=[txn])):
                cr.reconcile_paddle(finance_path=path)
            with open(path, encoding="utf-8") as f:
                after = f.read()
        self.assertEqual(before, after)


class TestReconcileAll(unittest.TestCase):
    def test_gumroad_etsy_payhip_are_honestly_not_reconcilable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [])
            with patch.object(registry, "get", return_value=FakeArm(ready=False)):
                result = cr.reconcile_all(finance_path=path)
        for platform in ("gumroad", "etsy", "payhip"):
            self.assertEqual(result["platforms"][platform]["status"], "NOT_RECONCILABLE")

    def test_total_discrepancies_found_matches_real_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_finance(tmp, [])
            txn = {"id": "txn_1", "details": {"totals": {"grand_total": "1550"}}}
            with patch.object(registry, "get", return_value=FakeArm(ready=True, transactions=[txn])):
                result = cr.reconcile_all(finance_path=path)
        self.assertEqual(result["total_discrepancies_found"], 1)


if __name__ == "__main__":
    unittest.main()
