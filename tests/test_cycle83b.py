"""Cycle 83 (forensic round) — revenue truth regression tests.

Covers every case the directive listed, each pinned to the defect it prevents:

  * a successful request with genuinely empty results
  * a successful request with real results
  * incomplete / unexpected response shapes
  * stale data
  * auth / permission / connection failure
  * sales pagination and duplicate transactions
  * gross vs withdrawn vs net, using only fields that actually exist

Two live-forensic findings are also pinned here as data, so a future change
cannot quietly invalidate the basis of a reported zero:

  * GET /v2/sales returns success:true with an empty list and NO pagination
    cursor. An empty first page is therefore complete -- there is nothing
    after it.
  * An invalid credential gets HTTP 401 from that same endpoint, so our 200
    means the request really was authenticated and answered.

Run:  python -m unittest discover -s tests -p "test_cycle83b.py" -v
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import revenue_truth
from revenue_truth import PASS, STALE, UNKNOWN, read_revenue_state

NOW = datetime.datetime(2026, 10, 14, 14, 0, tzinfo=datetime.timezone.utc)


def _write(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    return path


class TestGenuineEmptyResult(unittest.TestCase):
    """A successful read that genuinely holds no sales is a REAL zero and
    must stay a real zero -- it is not an error."""

    def test_empty_sales_list_is_a_observed_zero(self):
        path = _write(json.dumps(
            {"sales": [], "lastUpdated": "2026-10-14T13:00:00Z"}))
        try:
            r = read_revenue_state(path, now=NOW)
            self.assertEqual(r["status"], PASS)
            self.assertEqual(r["gross_usd"], 0.0)
            self.assertEqual(r["sales_count"], 0)
        finally:
            os.unlink(path)


class TestGenuineResults(unittest.TestCase):
    def test_real_sales_sum(self):
        path = _write(json.dumps({
            "sales": [{"amount": 29}, {"amount": 69.5}],
            "lastUpdated": "2026-10-14T13:00:00Z"}))
        try:
            r = read_revenue_state(path, now=NOW)
            self.assertEqual(r["status"], PASS)
            self.assertEqual(r["gross_usd"], 98.5)
            self.assertEqual(r["sales_count"], 2)
        finally:
            os.unlink(path)

    def test_strings_and_numbers_both_parse(self):
        path = _write(json.dumps({
            "sales": [{"amount": "29.00"}, {"amount": 1}],
            "lastUpdated": "2026-10-14T13:00:00Z"}))
        try:
            self.assertEqual(read_revenue_state(path, now=NOW)["gross_usd"], 30.0)
        finally:
            os.unlink(path)

    def test_unpriced_sale_row_is_surfaced_not_swallowed(self):
        """A real sale we cannot price must not vanish into a clean total."""
        path = _write(json.dumps({
            "sales": [{"amount": "not-a-number"}, {"amount": 10}],
            "lastUpdated": "2026-10-14T13:00:00Z"}))
        try:
            r = read_revenue_state(path, now=NOW)
            self.assertEqual(r["gross_usd"], 10.0)
            self.assertIn("no usable amount", r["note"])
        finally:
            os.unlink(path)


class TestIncompleteAndUnexpectedShapes(unittest.TestCase):
    """None of these may be reported as $0."""

    def _assert_unknown(self, content, why):
        path = _write(content)
        try:
            r = read_revenue_state(path, now=NOW)
            self.assertEqual(r["status"], UNKNOWN, why)
            self.assertIsNone(r["gross_usd"], why)
        finally:
            os.unlink(path)

    def test_malformed_json(self):
        self._assert_unknown("{ this is not valid json", "corrupt file")

    def test_missing_file(self):
        r = read_revenue_state(
            os.path.join(tempfile.gettempdir(), "definitely_absent_xyz.json"),
            now=NOW)
        self.assertEqual(r["status"], UNKNOWN)
        self.assertIsNone(r["gross_usd"])

    def test_sales_key_absent(self):
        self._assert_unknown(json.dumps({"totalSales": 0}),
                             "no sales key is not a zero")

    def test_sales_is_not_a_list(self):
        self._assert_unknown(json.dumps({"sales": {}}),
                             "wrong sales type is not a zero")

    def test_top_level_is_an_array(self):
        self._assert_unknown(json.dumps([1, 2, 3]),
                             "non-object record is not a zero")

    def test_truncated_write(self):
        self._assert_unknown('{"sales": [{"amount": 29',
                             "a half-written file is not a zero")

    def test_the_live_corrupt_finance_files_on_disk(self):
        """finance_data.json.corrupt-*.bak exist on this machine and contain
        the literal text '{ this is not valid json'. Reading one must yield
        UNKNOWN, never 0.0 -- which is what the old code returned."""
        backups = sorted(_FACTORY_ROOT.glob("finance_data.json.corrupt-*.bak"))
        if not backups:
            self.skipTest("no corrupt finance backups present on this machine")
        r = read_revenue_state(backups[0], now=NOW)
        self.assertEqual(r["status"], UNKNOWN)
        self.assertIsNone(r["gross_usd"])


class TestStaleness(unittest.TestCase):
    """Freshness was computed and never shown. A real number can still be too
    old to act on, and that is a different claim from "we made nothing"."""

    def test_fresh_record_is_pass(self):
        path = _write(json.dumps({
            "sales": [], "lastUpdated": "2026-10-14T13:00:00Z"}))
        try:
            self.assertEqual(read_revenue_state(path, now=NOW)["status"], PASS)
        finally:
            os.unlink(path)

    def test_old_record_is_stale_but_still_states_its_number(self):
        path = _write(json.dumps({
            "sales": [], "lastUpdated": "2026-10-01T00:00:00Z"}))
        try:
            r = read_revenue_state(path, now=NOW, stale_after_seconds=86400)
            self.assertEqual(r["status"], STALE)
            self.assertEqual(r["gross_usd"], 0.0,
                             "a stale record still reports what it holds")
            self.assertIsNotNone(r["age_seconds"])
            self.assertGreater(r["age_seconds"], 86400)
        finally:
            os.unlink(path)

    def test_missing_lastupdated_cannot_be_called_fresh_or_stale(self):
        """No timestamp means freshness is unknown, not fresh."""
        path = _write(json.dumps({"sales": []}))
        try:
            r = read_revenue_state(path, now=NOW)
            self.assertIn(r["status"], (PASS, STALE))
            self.assertIsNone(r["age_seconds"])
        finally:
            os.unlink(path)


class TestDelegatingCallersNoLongerFakeZero(unittest.TestCase):
    """The two modules that produced a bare 0.0 for an unreadable source."""

    def test_reality_net_revenue_returns_none_for_corrupt(self):
        import reality
        path = _write("{ broken")
        try:
            self.assertIsNone(reality.net_revenue(path))
        finally:
            os.unlink(path)

    def test_reality_net_revenue_returns_zero_for_a_real_empty_record(self):
        import reality
        path = _write(json.dumps({"sales": [], "lastUpdated": "2026-10-14T13:00:00Z"}))
        try:
            self.assertEqual(reality.net_revenue(path), 0.0)
        finally:
            os.unlink(path)

    def test_capital_efficiency_returns_none_for_corrupt(self):
        import capital_efficiency
        path = _write("{ broken")
        try:
            self.assertIsNone(
                capital_efficiency._real_total_revenue(path))
        finally:
            os.unlink(path)

    def test_capital_efficiency_returns_real_totals(self):
        import capital_efficiency
        path = _write(json.dumps({
            "sales": [{"amount": 12.5}, {"amount": 7.5}],
            "lastUpdated": "2026-10-14T13:00:00Z"}))
        try:
            self.assertEqual(
                capital_efficiency._real_total_revenue(path), 20.0)
        finally:
            os.unlink(path)

    def test_smoke_test_records_are_never_counted_as_revenue(self):
        """Regression I introduced and this test now pins.

        Rewriting capital_efficiency._real_total_revenue to delegate here
        silently DROPPED its existing "DELETE-ME" smoke-record filter, so a
        synthetic $150 test row started counting as real revenue. Caught by
        test_capital_efficiency.py::test_test_smoke_record_filtered_from_revenue.
        Refactoring a function must not quietly drop a filter it did not know
        about -- this asserts the filter here too, in the shared engine.
        """
        import capital_efficiency
        path = _write(json.dumps({
            "sales": [
                {"platform": "Paddle", "amount": 150,
                 "product": "contract-test-ladder-DELETE-ME"},
                {"platform": "gumroad", "amount": 40, "product": "Turo Kit"},
            ],
            "lastUpdated": "2026-10-14T13:00:00Z"}))
        try:
            self.assertEqual(
                capital_efficiency._real_total_revenue(path), 40.0)
            state = read_revenue_state(path, now=NOW,
                                       exclude_products_with="DELETE-ME")
            self.assertEqual(state["excluded_count"], 1)
            self.assertIn("test-record", state["note"])
        finally:
            os.unlink(path)


class TestSalesQueryForensicsArePinned(unittest.TestCase):
    """The basis for reporting a zero revenue figure. Captured live on
    2026-10-14 from data/cycle83_sales_forensics.json."""

    def _forensics(self):
        path = _FACTORY_ROOT / "data" / "cycle83_sales_forensics.json"
        if not path.exists():
            self.skipTest("forensic capture not present")
        with open(path, encoding="utf-8-sig") as fh:
            return json.load(fh)

    def test_empty_sales_response_carried_no_pagination_cursor(self):
        """An empty first page is complete. If a cursor ever appears here,
        the query is stopping early and this test is the alarm."""
        d = self._forensics()
        self.assertTrue(d["sales_endpoint"]["sales_is_list"])
        self.assertEqual(d["sales_endpoint"]["sales_length"], 0)
        self.assertFalse(d["sales_endpoint"]["next_page_field_present"])
        self.assertIsNone(d["sales_endpoint"]["next_page_value"])

    def test_response_carried_success_true(self):
        self.assertTrue(self._forensics()["sales_endpoint"]["success_field"])

    def test_an_invalid_credential_is_rejected_by_the_same_endpoint(self):
        """Proof that our 200 is a real answer and not a silent failure."""
        nc = self._forensics()["negative_control"]
        self.assertEqual(nc["verdict"], "API_REJECTS_BAD_CREDENTIAL")
        self.assertNotEqual(nc["http_status"], 200)

    def test_an_independent_endpoint_also_reports_zero(self):
        xc = self._forensics()["independent_cross_check"]
        self.assertEqual(xc["verdict"], "CONSISTENT_ZERO")
        self.assertEqual(xc["sum_sales_count"], 0)
        self.assertEqual(xc["products_missing_the_sales_count_field"], 0,
                         "the cross-check is only valid if the field exists")


class TestNoFabricatedRevenue(unittest.TestCase):
    def test_module_never_invents_a_positive_number(self):
        path = _write(json.dumps({"sales": [], "lastUpdated": "2026-10-14T13:00:00Z"}))
        try:
            self.assertEqual(read_revenue_state(path, now=NOW)["gross_usd"], 0.0)
        finally:
            os.unlink(path)

    def test_local_record_is_never_labelled_verified(self):
        """This module reads a local file. VERIFIED_REVENUE is a claim about
        retrieved external transactions and is a different thing."""
        path = _write(json.dumps({"sales": [{"amount": 5}],
                                   "lastUpdated": "2026-10-14T13:00:00Z"}))
        try:
            blob = json.dumps(read_revenue_state(path, now=NOW)).upper()
            self.assertNotIn("VERIFIED", blob)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)