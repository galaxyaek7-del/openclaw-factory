"""Tier-1 tests: gap engine scoring/order + learning-extractor gate."""
import unittest

import factory_gap_engine as ge
import experiment_learning_extractor as le


class TestGapEngine(unittest.TestCase):
    def test_busywork_labels(self):
        low = ge.busywork_score(commercial_value=5, technical_value=5,
                                risk_reduction=0, founder_time_saved=0,
                                evidence_gain=0)
        self.assertEqual(low["label"], "LOW_VALUE_ACTIVITY")
        high = ge.busywork_score(commercial_value=90, technical_value=20,
                                 risk_reduction=80, founder_time_saved=50,
                                 evidence_gain=70)
        self.assertEqual(high["label"], "WORTH_DOING")

    def test_prioritize_orders_by_rank(self):
        gaps = [{"gap_id": "B", "rank": 5}, {"gap_id": "A", "rank": 1}]
        self.assertEqual(ge.prioritize(gaps)[0]["gap_id"], "A")

    def test_cycle_no_write(self):
        rep = ge.run_cycle(write_report=False)
        self.assertIn("gaps", rep)
        self.assertIn("daily_questions", rep)
        self.assertIn("highest_value_action", rep["daily_questions"])
        self.assertNotIn("report_path", rep)

    def test_gap_classes_valid(self):
        rep = ge.run_cycle(write_report=False)
        for g in rep["gaps"]:
            self.assertIn(g["class"], ge.GAP_CLASSES)


class TestLearningGate(unittest.TestCase):
    def test_held_or_draft_never_concludes_early(self):
        out = le.extract_post_window_learning("EXP-SUB-001")
        self.assertIn(out["state"], ("HELD", "DRAFT"))
        if out["state"] == "HELD":
            self.assertIsNone(out["draft"])
        else:
            self.assertIn("UNDETERMINED", str(out["draft"]))


if __name__ == "__main__":
    unittest.main()
