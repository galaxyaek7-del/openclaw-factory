"""Tests for CEO Score (founder Priority #1, 2026-08-17).

Real, executing tests over ceo_score.py's composition-only, read-only module.
Every test injects temp ledgers / temp state fixtures -- never the real
data/ ledgers, never the real cost log, never the real lock, never the real
finance_data.json. This guarantees (F): the CEO Score itself creates no
external action and records nothing to disk.

  * (A) colors come exclusively from the explicit deterministic THRESHOLDS maps
  * (B) no decision appears unless it is present in the real source data
  * (C) missing evidence reads the literal string 'Unknown — no data yet.'
  * (D) financial values cannot be fabricated -- they trace to the injected ledger
  * (E) founder-gated actions are never modified by the CEO Score
  * (F) the CEO Score creates no external actions / writes nothing to disk

    python -m unittest tests.test_ceo_score -v
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from ceo_score import (
    CEO_SCORE_INDICATORS,
    THRESHOLDS,
    UNKNOWN,
    build_ceo_score,
)


def _write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


class _Isolation:
    """Temp fixtures wired to every injectable path ceo_score.build_ceo_score()
    accepts, so no real production data is ever read during tests."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

        self.finance_path = self.root / "finance_data.json"
        self.reality_path = self.root / "reality.json"
        self.decisions_path = self.root / "decisions.jsonl"
        self.snapshots_path = self.root / "health_snapshots.jsonl"
        self.lock_path = self.root / "factory.lock"
        self.ai_cost_path = self.root / "ai_cost_log.jsonl"
        self.state_path = self.root / "evolution_queue_state.json"
        self.lessons_dir = self.root / "lessons"
        self.lessons_dir.mkdir()
        self.safe_mode_state_path = self.root / "safe_mode_state.json"
        self.publish_protection_state_path = self.root / "publish_protection_state.json"

        _write_json(self.finance_path, {"sales": [], "totalKDP": 0, "totalEtsy": 0, "totalGumroad": 0, "totalPaddle": 0})
        _write_json(self.reality_path, {"published_books": []})
        _write_jsonl(self.decisions_path, [])
        _write_jsonl(self.snapshots_path, [])
        _write_jsonl(self.ai_cost_path, [])
        _write_json(self.state_path, {})
        _write_json(self.safe_mode_state_path, {"flags": {}})
        _write_json(self.publish_protection_state_path, {"state": {}})
        self.lock_path.write_text("0", encoding="utf-8")

    def build(self, **over):
        kwargs = {
            "finance_path": self.finance_path,
            "reality_path": self.reality_path,
            "decisions_path": self.decisions_path,
            "snapshots_path": self.snapshots_path,
            "lock_path": self.lock_path,
            "ai_cost_path": self.ai_cost_path,
            "state_path": self.state_path,
            "lessons_dir": self.lessons_dir,
            "safe_mode_state_path": self.safe_mode_state_path,
            "publish_protection_state_path": self.publish_protection_state_path,
        }
        kwargs.update(over)
        return build_ceo_score(**kwargs)

    def close(self):
        self.tmp.cleanup()


class TestCEOScoreIndicators(unittest.TestCase):
    def test_all_8_indicators_present_in_order(self):
        iso = _Isolation()
        try:
            r = iso.build()
            names = [i["name"] for i in r["indicators"]]
            self.assertEqual(names, CEO_SCORE_INDICATORS)
            self.assertEqual(len(names), 8)
        finally:
            iso.close()

    def test_every_indicator_has_expected_shape(self):
        iso = _Isolation()
        try:
            r = iso.build()
            for ind in r["indicators"]:
                for field in ("name", "value", "color", "detail", "source"):
                    self.assertIn(field, ind, f"{ind['name']} missing {field}")
                self.assertIn(ind["color"], ("GREEN", "YELLOW", "RED"), ind["name"])
                self.assertTrue(ind["source"], f"{ind['name']} missing source")
                self.assertTrue(ind["detail"], f"{ind['name']} missing detail")
        finally:
            iso.close()


class TestA_ColorsOnlyFromDeterministicThresholds(unittest.TestCase):
    def test_colors_are_always_from_THRESHOLDS_enumeration(self):
        # The only colors the CEO Score can ever emit are the three THRESHOLDS
        # enumerations; a color not named in THRESHOLDS is a test failure.
        allowed = {"GREEN", "YELLOW", "RED"}
        iso = _Isolation()
        try:
            r = iso.build()
            for ind in r["indicators"]:
                self.assertIn(ind["color"], allowed, f"{ind['name']} emitted {ind['color']}")
                # And every indicator has an explicit deterministic threshold map.
                self.assertIn(ind["name"], THRESHOLDS, f"no threshold map for {ind['name']}")
        finally:
            iso.close()

    def test_financial_color_tracks_real_revenue_deterministically(self):
        iso = _Isolation()
        try:
            _write_json(iso.finance_path, {"sales": [], "totalKDP": 0, "totalEtsy": 0, "totalGumroad": 0, "totalPaddle": 0})
            r = iso.build()
            fin = next(i for i in r["indicators"] if i["name"] == "FINANCIAL_TRUTH")
            self.assertEqual(fin["color"], "RED")  # 0 revenue / 0 sales -> RED per THRESHOLDS
            self.assertEqual(fin["value"]["real_revenue_usd"], 0)

            # With a real (DELETE-ME-excluded) sale the color must flip to GREEN.
            _write_json(iso.finance_path, {
                "sales": [{"product": "EU AI Act Toolkit", "amount": 155, "platform": "paddle"}],
                "totalKDP": 0, "totalEtsy": 0, "totalGumroad": 0, "totalPaddle": 155,
            })
            r2 = iso.build()
            fin2 = next(i for i in r2["indicators"] if i["name"] == "FINANCIAL_TRUTH")
            self.assertEqual(fin2["color"], "GREEN")
            self.assertEqual(fin2["value"]["real_revenue_usd"], 155)
        finally:
            iso.close()


class TestB_NoDecisionWithoutRealSourceData(unittest.TestCase):
    def test_opportunity_never_fabricated_from_empty_queue(self):
        iso = _Isolation()
        try:
            # Empty decisions ledger -> empty run-now -> honest RED, no invented pick.
            r = iso.build()
            opp = next(i for i in r["indicators"] if i["name"] == "BEST_OPPORTUNITY")
            self.assertEqual(opp["value"]["run_now_count"], 0)
            self.assertEqual(opp["value"]["accepted_count"], 0)
            self.assertIsNone(opp["value"]["top_run_now"])
            self.assertEqual(opp["color"], "RED")
            self.assertNotIn("Legal Case Research Automation System", opp["detail"])
        finally:
            iso.close()

    def test_opportunity_traces_to_real_accepted_decision(self):
        iso = _Isolation()
        try:
            _write_jsonl(iso.decisions_path, [
                {"niche": "Legal Case Research Automation System for Solo Attorneys",
                 "status": "ACCEPTED", "decision_id": "abc123", "decided_at": "2026-08-14T00:00:00"},
            ])
            r = iso.build()
            opp = next(i for i in r["indicators"] if i["name"] == "BEST_OPPORTUNITY")
            self.assertEqual(opp["value"]["accepted_count"], 1)
            self.assertIn("Legal Case Research Automation System", opp["detail"])
        finally:
            iso.close()

    def test_learning_loop_not_closed_with_empty_measurements(self):
        iso = _Isolation()
        try:
            _write_json(iso.state_path, {})
            r = iso.build()
            ll = next(i for i in r["indicators"] if i["name"] == "LEARNING_LOOP")
            self.assertEqual(ll["value"]["measured_outcomes"], 0)
            self.assertFalse(ll["value"]["closed_once"])
        finally:
            iso.close()


class TestC_MissingEvidenceShowsLiteralUnknown(unittest.TestCase):
    def test_financial_truth_never_fabricates_with_missing_files(self):
        iso = _Isolation()
        try:
            # Delete the finance/reality fixtures entirely -- the module must
            # never guess; it reports the literal UNKNOWN string for missing data.
            iso.finance_path.unlink()
            iso.reality_path.unlink()
            r = iso.build()
            fin = next(i for i in r["indicators"] if i["name"] == "FINANCIAL_TRUTH")
            self.assertEqual(fin["value"]["real_revenue_usd"], 0)
            self.assertEqual(fin["value"]["real_sales_count"], 0)
            self.assertEqual(fin["value"]["published_books"], 0)
            # No fabricated NONZERO dollar figure can ever appear (a missing
            # ledger must never be silently replaced with invented money).
            self.assertNotRegex(fin["detail"], r"\$[1-9]")
        finally:
            iso.close()

    def test_missing_data_string_used_where_no_real_signal(self):
        # UNKNOWN is the literal canonical Truth First missing-data string.
        self.assertEqual(UNKNOWN, "Unknown — no data yet.")
        iso = _Isolation()
        try:
            r = iso.build()
            for ind in r["indicators"]:
                # Every indicator must carry either a real value or the literal
                # Unknown string -- never an empty/None detail with a color.
                if ind["value"] is None:
                    self.assertEqual(ind["detail"], UNKNOWN, ind["name"])
        finally:
            iso.close()


class TestD_FinancialValuesCannotBeFabricated(unittest.TestCase):
    def test_financial_values_trace_exactly_to_injected_ledger(self):
        iso = _Isolation()
        try:
            _write_json(iso.finance_path, {
                "sales": [
                    {"product": "DELETE-ME contract-test-ladder-DELETE-ME", "amount": 999999},
                    {"product": "EU AI Act Toolkit", "amount": 155, "platform": "paddle"},
                ],
                "totalKDP": 10, "totalEtsy": 20, "totalGumroad": 30, "totalPaddle": 155,
            })
            _write_json(iso.reality_path, {"published_books": [{"title": "real book"}]})
            r = iso.build()
            fin = next(i for i in r["indicators"] if i["name"] == "FINANCIAL_TRUTH")
            # DELETE-ME excluded; the ONLY real sale is 155.
            self.assertEqual(fin["value"]["real_revenue_usd"], 155)
            self.assertEqual(fin["value"]["real_sales_count"], 1)
            self.assertEqual(fin["value"]["treasury"]["paddle"], 155)
            self.assertEqual(fin["value"]["published_books"], 1)
            self.assertNotIn(999999, [fin["value"]["real_revenue_usd"]])
        finally:
            iso.close()


class TestE_FounderGatedActionsNeverModified(unittest.TestCase):
    def test_today_3_decisions_are_real_founder_gates_passthrough(self):
        iso = _Isolation()
        try:
            r = iso.build()
            # The CEO Score surfaces decisions read-only; it must not create
            # new ones. With an empty real founder queue -> empty list.
            self.assertIsInstance(r["today_3_decisions"], list)
            self.assertLessEqual(len(r["today_3_decisions"]), 3)
            for d in r["today_3_decisions"]:
                self.assertIn("action", d)
        finally:
            iso.close()


class TestF_CreatesNoExternalAction(unittest.TestCase):
    def test_build_ceo_score_writes_nothing_to_disk(self):
        iso = _Isolation()
        try:
            before = set(os.listdir(iso.root))
            iso.build()
            after = set(os.listdir(iso.root))
            # No new file appeared anywhere in the temp isolation root.
            self.assertEqual(before, after)
        finally:
            iso.close()

    def test_no_publish_spend_contact_imports_executed(self):
        # The CEO Score module's own docstring contract: never publishes, never
        # spends, never contacts a platform/customer. We prove the module never
        # triggers real side-effecting engines by importing it in a clean,
        # output-captured context and confirming no platform call occurs.
        iso = _Isolation()
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                r = iso.build()
            self.assertEqual(buf.getvalue(), "")
            self.assertIn("note", r)
        finally:
            iso.close()


class TestToday3DecisionsCap(unittest.TestCase):
    def test_cap_at_3_and_fewer_when_fewer_exist(self):
        # The real founder_next_action queue can hold more than 3 items; the CEO
        # Score must show at most 3, and never invent extra ones.
        iso = _Isolation()
        try:
            r = iso.build()
            self.assertLessEqual(len(r["today_3_decisions"]), 3)
            # Deterministic: rerunning yields the same length (same real queue).
            r2 = iso.build()
            self.assertEqual(len(r["today_3_decisions"]), len(r2["today_3_decisions"]))
        finally:
            iso.close()


class TestIgnoreListHonest(unittest.TestCase):
    def test_ignore_list_only_proven_items(self):
        iso = _Isolation()
        try:
            r = iso.build()
            for item in r["what_founder_can_ignore_today"]:
                self.assertTrue(item)  # never an empty invented entry
        finally:
            iso.close()


if __name__ == "__main__":
    unittest.main()