"""Tests for growth_funnel.py (Cycle 82, "From Builder to Seller" -- item 5).

Isolation discipline: every test uses an explicit temp path for the events
ledger / finance file / csv, never the real data/content_queue_cycle82.csv
or finance_data.json read-write combination without an override, matching
tests/test_ceo_score.py's own established convention for this factory's
read-only dashboards.

    python -m unittest tests.test_growth_funnel -v
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

import growth_funnel


class _TempFileMixin:
    def setUp(self):
        self._tmp_paths = []

    def tearDown(self):
        for p in self._tmp_paths:
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass

    def _tmp(self, suffix):
        path = Path(tempfile.mktemp(suffix=suffix))
        self._tmp_paths.append(path)
        return path


class TestLoadContentQueue(_TempFileMixin, unittest.TestCase):
    def test_missing_file_returns_empty_not_fabricated(self):
        rows = growth_funnel.load_content_queue(csv_path=self._tmp(".csv"))
        self.assertEqual(rows, [])

    def test_real_csv_rows_are_read_verbatim(self):
        path = self._tmp(".csv")
        path.write_text(
            "post_number,week,type,title_ar,referrer_id,link_template,status\n"
            "1,1,value,test title,cy_test_1,<URL>?referrer=cy_test_1,DRAFT_NOT_SCHEDULED\n",
            encoding="utf-8",
        )
        rows = growth_funnel.load_content_queue(csv_path=path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["referrer_id"], "cy_test_1")


class TestRecordFunnelEvent(_TempFileMixin, unittest.TestCase):
    def test_rejects_unknown_stage(self):
        with self.assertRaises(ValueError):
            growth_funnel.record_funnel_event("cy_test_1", "bogus_stage", 5, events_path=self._tmp(".jsonl"))

    def test_rejects_negative_count(self):
        with self.assertRaises(ValueError):
            growth_funnel.record_funnel_event("cy_test_1", "reach", -1, events_path=self._tmp(".jsonl"))

    def test_appends_a_real_event_never_overwrites(self):
        path = self._tmp(".jsonl")
        growth_funnel.record_funnel_event("cy_test_1", "reach", 100, events_path=path)
        growth_funnel.record_funnel_event("cy_test_1", "clicks", 7, events_path=path)
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), 2)
        first = json.loads(lines[0])
        self.assertEqual(first["stage"], "reach")
        self.assertEqual(first["count"], 100)


class TestBuildGrowthFunnelDashboard(_TempFileMixin, unittest.TestCase):
    def test_zero_events_reports_unknown_not_zero_for_reach(self):
        csv_path = self._tmp(".csv")
        csv_path.write_text(
            "post_number,week,type,title_ar,referrer_id,link_template,status\n"
            "1,1,value,t,cy_test_1,<URL>?referrer=cy_test_1,DRAFT_NOT_SCHEDULED\n",
            encoding="utf-8",
        )
        events_path = self._tmp(".jsonl")  # never created -- zero real events
        finance_path = self._tmp(".json")
        finance_path.write_text(json.dumps({"sales": []}), encoding="utf-8")

        result = growth_funnel.build_growth_funnel_dashboard(
            csv_path=csv_path, events_path=events_path, finance_path=finance_path,
        )
        self.assertEqual(result["funnel"]["posts_drafted"], 1)
        self.assertEqual(result["funnel"]["reach"], growth_funnel.UNKNOWN)
        self.assertEqual(result["funnel"]["real_sales_attributed"], 0)

    def test_real_events_are_summed_per_stage(self):
        csv_path = self._tmp(".csv")
        csv_path.write_text(
            "post_number,week,type,title_ar,referrer_id,link_template,status\n"
            "1,1,value,t,cy_test_1,<URL>?referrer=cy_test_1,DRAFT_NOT_SCHEDULED\n",
            encoding="utf-8",
        )
        events_path = self._tmp(".jsonl")
        growth_funnel.record_funnel_event("cy_test_1", "reach", 300, events_path=events_path)
        growth_funnel.record_funnel_event("cy_test_1", "reach", 50, events_path=events_path)
        growth_funnel.record_funnel_event("cy_test_1", "clicks", 12, events_path=events_path)
        finance_path = self._tmp(".json")
        finance_path.write_text(json.dumps({"sales": []}), encoding="utf-8")

        result = growth_funnel.build_growth_funnel_dashboard(
            csv_path=csv_path, events_path=events_path, finance_path=finance_path,
        )
        self.assertEqual(result["funnel"]["reach"], 350)
        self.assertEqual(result["funnel"]["clicks"], 12)

    def test_never_counts_a_delete_me_smoke_test_sale_as_real_revenue(self):
        csv_path = self._tmp(".csv")
        csv_path.write_text(
            "post_number,week,type,title_ar,referrer_id,link_template,status\n"
            "1,1,value,t,cy_test_1,<URL>?referrer=cy_test_1,DRAFT_NOT_SCHEDULED\n",
            encoding="utf-8",
        )
        finance_path = self._tmp(".json")
        finance_path.write_text(json.dumps({
            "sales": [
                {"product": "contract-test-ladder-DELETE-ME", "amount": 999, "referrer": "cy_test_1"},
                {"product": "real guide", "amount": 15, "referrer": "cy_test_1"},
            ]
        }), encoding="utf-8")

        result = growth_funnel.build_growth_funnel_dashboard(
            csv_path=csv_path, events_path=self._tmp(".jsonl"), finance_path=finance_path,
        )
        # Only the real (non-DELETE-ME) sale counts.
        self.assertEqual(result["ground_truth"]["total_real_sales"], 1)
        self.assertEqual(result["ground_truth"]["attributed_revenue_usd"], 15)


if __name__ == "__main__":
    unittest.main()
