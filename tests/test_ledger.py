"""Tests for channels/ledger.py's finance reconciliation (ADR-077, Product
Generation Pipeline — Finance Ledger stage).

Runs with stdlib unittest. Never touches the real data/sales_ledger.jsonl
or finance_data.json — every test passes explicit temp paths.

    python -m unittest tests.test_ledger -v
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import ledger
from channels.base_arm import PublishResult


def _temp_path(suffix):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class TestRecordPublishAttemptProtectionFields(unittest.TestCase):
    """Global Commercial Hardening, Phase 1 (2026-07-29): record_publish_
    attempt()'s new optional risk_score/protection_decision kwargs must be
    backward compatible -- omitted entirely from the event when not given,
    exactly the pre-existing shape."""

    def setUp(self):
        self.ledger_path = _temp_path(".jsonl")

    def tearDown(self):
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)

    def _fake_product(self):
        product = mock.Mock()
        product.title = "t"
        product.source_id = "PROD-test-1"
        product.product_type = "book"
        return product

    def _fake_result(self):
        return PublishResult(ok=True, platform="gumroad", product_id="p1", url="http://x", error=None, dry_run=False)

    def test_omitted_kwargs_produce_the_original_event_shape(self):
        event = ledger.record_publish_attempt(self._fake_product(), self._fake_result(), ledger_path=self.ledger_path)
        self.assertNotIn("risk_score", event)
        self.assertNotIn("protection_decision", event)

    def test_given_kwargs_are_recorded_verbatim(self):
        event = ledger.record_publish_attempt(
            self._fake_product(), self._fake_result(), ledger_path=self.ledger_path,
            risk_score=42, protection_decision="allowed",
        )
        self.assertEqual(event["risk_score"], 42)
        self.assertEqual(event["protection_decision"], "allowed")

    def test_backfill_reason_omitted_produces_original_shape(self):
        """Production Hardening (ADR-204, Phase 14, 2026-08-08):
        regression test for FAILURE_REGISTER.md F3's fix."""
        event = ledger.record_publish_attempt(self._fake_product(), self._fake_result(), ledger_path=self.ledger_path)
        self.assertNotIn("backfilled", event)
        self.assertNotIn("backfill_reason", event)

    def test_backfill_reason_given_tags_event_honestly(self):
        event = ledger.record_publish_attempt(
            self._fake_product(), self._fake_result(), ledger_path=self.ledger_path,
            backfill_reason="real event confirmed live against the Paddle account, never recorded at the time",
        )
        self.assertTrue(event["backfilled"])
        self.assertIn("real event confirmed live", event["backfill_reason"])


class TestRecordSaleMarketEvidenceHook(unittest.TestCase):
    """Market Learning Loop (2026-07-22): record_sale()'s new optional
    `niche` param should also log a real closed_sale market-evidence
    event -- but only when a niche is actually given, and never at the
    cost of the real sale record itself."""

    def setUp(self):
        self.ledger_path = _temp_path(".jsonl")
        self.evidence_path = _temp_path(".jsonl")

    def tearDown(self):
        for p in (self.ledger_path, self.evidence_path):
            if os.path.exists(p):
                os.remove(p)

    def test_no_niche_given_records_sale_only_no_evidence_event(self):
        import market_evidence
        with mock.patch.object(market_evidence, "DEFAULT_EVIDENCE_PATH", Path(self.evidence_path)):
            ledger.record_sale("gumroad", {"id": "s1", "price": "9.99"}, ledger_path=self.ledger_path)
        self.assertEqual(market_evidence.read_evidence(evidence_path=self.evidence_path), [])

    def test_niche_given_also_logs_a_real_closed_sale_event(self):
        import market_evidence
        with mock.patch.object(market_evidence, "DEFAULT_EVIDENCE_PATH", Path(self.evidence_path)):
            ledger.record_sale("gumroad", {"id": "s2", "price": "9.99"}, ledger_path=self.ledger_path, niche="a real niche")
        events = market_evidence.read_evidence("a real niche", "closed_sale", evidence_path=self.evidence_path)
        self.assertEqual(len(events), 1)

    def test_evidence_logging_failure_never_loses_the_real_sale_record(self):
        import market_evidence
        with mock.patch.object(market_evidence, "record_evidence", side_effect=RuntimeError("disk full")):
            recorded = ledger.record_sale("gumroad", {"id": "s3", "price": "9.99"}, ledger_path=self.ledger_path, niche="a real niche")
        self.assertEqual(recorded["event_type"], "sale")
        with open(self.ledger_path, encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)


class TestReconcileLedgerToFinance(unittest.TestCase):
    def setUp(self):
        self.ledger_path = _temp_path(".jsonl")
        self.finance_path = _temp_path(".json")

    def tearDown(self):
        for p in (self.ledger_path, self.finance_path):
            if os.path.exists(p):
                os.remove(p)

    def test_no_ledger_file_reconciles_to_the_honest_default_shape(self):
        result = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)
        self.assertEqual(result, {"reconciled": 0, "skipped_unrecognized": 0, "total_sales": 0})
        self.assertFalse(Path(self.finance_path).exists())  # nothing to write, file untouched

    def test_gumroad_sale_reconciles_with_real_amount(self):
        ledger.record_sale("gumroad", {"id": "sale_1", "price": "19.99", "product_name": "Real Book"}, ledger_path=self.ledger_path)
        result = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)

        self.assertEqual(result["reconciled"], 1)
        self.assertEqual(result["skipped_unrecognized"], 0)
        self.assertEqual(result["total_sales"], 19.99)

        with open(self.finance_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["totalGumroad"], 19.99)
        self.assertEqual(data["totalSales"], 19.99)
        self.assertEqual(data["sales"][0]["platform"], "Gumroad")
        self.assertEqual(data["sales"][0]["source_ledger_key"], "gumroad:sale_1")
        self.assertEqual(data["byLadder"]["kdp_books"], 19.99)  # honest default rank

    def test_paddle_sale_amount_extracted_from_grand_total_cents(self):
        raw = {"id": "txn_1", "details": {"totals": {"grand_total": "38800"}}}
        ledger.record_sale("paddle", raw, ledger_path=self.ledger_path)
        result = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)

        self.assertEqual(result["reconciled"], 1)
        with open(self.finance_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["totalPaddle"], 388.0)

    def test_unrecognized_platform_is_skipped_never_counted_as_zero(self):
        ledger.record_sale("mystery_platform", {"id": "x"}, ledger_path=self.ledger_path)
        result = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)

        self.assertEqual(result["reconciled"], 0)
        self.assertEqual(result["skipped_unrecognized"], 1)
        self.assertFalse(Path(self.finance_path).exists())

    def test_rerunning_reconciliation_never_double_counts(self):
        ledger.record_sale("gumroad", {"id": "sale_1", "price": "19.99"}, ledger_path=self.ledger_path)
        ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)
        second = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)

        self.assertEqual(second["reconciled"], 0)
        self.assertEqual(second["total_sales"], 19.99)
        with open(self.finance_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["sales"]), 1)

    def test_reconciliation_is_additive_to_existing_finance_data(self):
        existing = {
            "sales": [{"id": 1, "platform": "KDP", "amount": 5.0, "product": "old", "date": "2026-01-01"}],
            "totalKDP": 5.0, "totalEtsy": 0, "totalGumroad": 0, "totalPaddle": 0, "totalSales": 5.0,
            "byLadder": {"kdp_books": 5.0}, "lastUpdated": "2026-01-01T00:00:00+00:00",
        }
        with open(self.finance_path, "w", encoding="utf-8") as f:
            json.dump(existing, f)

        ledger.record_sale("gumroad", {"id": "sale_1", "price": "19.99"}, ledger_path=self.ledger_path)
        result = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)

        self.assertEqual(result["total_sales"], 24.99)
        with open(self.finance_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["sales"]), 2)
        self.assertEqual(data["sales"][0]["platform"], "KDP")  # pre-existing sale preserved verbatim
        self.assertEqual(data["sales"][1]["id"], 2)  # new sale's id continues the sequence


class TestRevenueTrend(unittest.TestCase):
    def setUp(self):
        self.ledger_path = _temp_path(".jsonl")

    def tearDown(self):
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)

    def _sale_event(self, timestamp, platform="gumroad", price="19.99", sale_id="s"):
        return {
            "event_type": "sale", "platform": platform, "timestamp": timestamp,
            "raw": {"id": sale_id, "price": price},
        }

    def test_no_sales_reports_honestly_zero_never_a_fabricated_trend(self):
        result = ledger.revenue_trend(ledger_path=self.ledger_path)
        self.assertEqual(result["total_sales_count"], 0)
        self.assertEqual(result["total_revenue_usd"], 0)
        self.assertIsNone(result["trailing_daily_avg_usd"])
        self.assertEqual(result["by_day"], {})
        self.assertIn("لا توجد مبيعات", result["note"])

    def test_publish_attempt_events_never_counted_as_revenue(self):
        ledger.record_publish_attempt(
            type("P", (), {"title": "t", "source_id": "1", "product_type": "book"})(),
            type("R", (), {"platform": "gumroad", "ok": True, "dry_run": False, "product_id": "p", "url": None, "error": None})(),
            ledger_path=self.ledger_path,
        )
        result = ledger.revenue_trend(ledger_path=self.ledger_path)
        self.assertEqual(result["total_sales_count"], 0)

    def test_sales_bucketed_by_day_and_summed_correctly(self):
        now = datetime(2026, 7, 20, tzinfo=timezone.utc)
        ledger.append_event(self._sale_event("2026-07-19T10:00:00+00:00", price="10.00", sale_id="a"), ledger_path=self.ledger_path)
        ledger.append_event(self._sale_event("2026-07-19T15:00:00+00:00", price="5.00", sale_id="b"), ledger_path=self.ledger_path)
        ledger.append_event(self._sale_event("2026-07-18T00:00:00+00:00", price="20.00", sale_id="c"), ledger_path=self.ledger_path)

        result = ledger.revenue_trend(now=now, ledger_path=self.ledger_path)
        self.assertEqual(result["total_sales_count"], 3)
        self.assertEqual(result["total_revenue_usd"], 35.00)
        self.assertEqual(result["by_day"]["2026-07-19"], 15.00)
        self.assertEqual(result["by_day"]["2026-07-18"], 20.00)

    def test_recent_7d_vs_trailing_average_matches_getcosttrend_style_shape(self):
        now = datetime(2026, 7, 20, tzinfo=timezone.utc)
        # 10 days ago (trailing) and 1 day ago (recent).
        ledger.append_event(self._sale_event("2026-07-05T00:00:00+00:00", price="30.00", sale_id="old"), ledger_path=self.ledger_path)
        ledger.append_event(self._sale_event("2026-07-19T00:00:00+00:00", price="9.00", sale_id="new"), ledger_path=self.ledger_path)

        result = ledger.revenue_trend(now=now, ledger_path=self.ledger_path)
        self.assertEqual(result["recent_7d_revenue_usd"], 9.00)
        self.assertEqual(result["recent_7d_sales_count"], 1)
        self.assertEqual(result["trailing_daily_avg_usd"], 30.00)
        self.assertIsNone(result["note"])

    def test_unrecognized_platform_amount_excluded_never_guessed(self):
        ledger.append_event(
            {"event_type": "sale", "platform": "mystery", "timestamp": "2026-07-19T00:00:00+00:00", "raw": {"id": "x"}},
            ledger_path=self.ledger_path,
        )
        result = ledger.revenue_trend(ledger_path=self.ledger_path)
        self.assertEqual(result["total_sales_count"], 0)


class TestRecordSaleAttribution(unittest.TestCase):
    """Global Commercial Revenue OS, Section 4 (ADR-202, 2026-08-07)."""

    def setUp(self):
        self.ledger_path = _temp_path(".jsonl")

    def tearDown(self):
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)

    def test_omitted_attribution_fields_produce_the_original_event_shape(self):
        recorded = ledger.record_sale("gumroad", {"id": "s1"}, ledger_path=self.ledger_path)
        for key in ("country", "channel", "campaign", "partner", "customer_segment"):
            self.assertNotIn(key, recorded)

    def test_given_attribution_fields_are_recorded_verbatim(self):
        recorded = ledger.record_sale(
            "gumroad", {"id": "s1"}, ledger_path=self.ledger_path,
            country="EG", channel="affiliate", campaign="launch_week", partner="acme", customer_segment="smb",
        )
        self.assertEqual(recorded["country"], "EG")
        self.assertEqual(recorded["channel"], "affiliate")
        self.assertEqual(recorded["campaign"], "launch_week")
        self.assertEqual(recorded["partner"], "acme")
        self.assertEqual(recorded["customer_segment"], "smb")

    def test_partial_attribution_only_records_given_fields(self):
        recorded = ledger.record_sale("gumroad", {"id": "s1"}, ledger_path=self.ledger_path, country="EG")
        self.assertEqual(recorded["country"], "EG")
        self.assertNotIn("channel", recorded)
        self.assertNotIn("campaign", recorded)


if __name__ == "__main__":
    unittest.main()
