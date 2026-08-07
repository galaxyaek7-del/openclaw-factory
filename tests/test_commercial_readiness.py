import json
import os
import tempfile
import unittest

import commercial_readiness as cr


class TestCommercialReadinessScore(unittest.TestCase):
    def test_never_fabricates_technical_when_not_supplied(self):
        result = cr.commercial_readiness_score(channel_statuses={}, decisions_path="C:/definitely/not/real.jsonl")
        self.assertIsNone(result["dimensions"]["technical"]["score"])
        self.assertEqual(result["dimensions"]["technical"]["source"], "not_computed_this_call")

    def test_overall_excludes_uncomputed_technical(self):
        result = cr.commercial_readiness_score(channel_statuses={}, decisions_path="C:/definitely/not/real.jsonl")
        scored = [d["score"] for d in result["dimensions"].values() if d["score"] is not None]
        self.assertAlmostEqual(result["overall"], round(sum(scored) / len(scored), 1))

    def test_commercial_score_zero_channels_zero_accepted_zero_sales(self):
        with tempfile.TemporaryDirectory() as tmp:
            decisions_path = os.path.join(tmp, "decisions.jsonl")
            with open(decisions_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"niche": "x", "status": "REJECTED"}) + "\n")
            result = cr._commercial_readiness(channel_statuses={}, decisions_path=decisions_path)
            self.assertEqual(result["score"], 0.0)

    def test_commercial_score_credits_real_accepted_opportunity(self):
        with tempfile.TemporaryDirectory() as tmp:
            decisions_path = os.path.join(tmp, "decisions.jsonl")
            with open(decisions_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"niche": "x", "status": "ACCEPTED"}) + "\n")
            result = cr._commercial_readiness(channel_statuses={"paddle": "ArmStatus.READY"}, decisions_path=decisions_path)
            self.assertGreaterEqual(result["score"], 30.0)

    def test_bottleneck_is_the_real_lowest_scored_dimension(self):
        result = cr.commercial_readiness_score(
            reality_audit_results={"percentages": {"REAL": 98.8}},
            channel_statuses={}, decisions_path="C:/definitely/not/real.jsonl",
        )
        lowest = min(result["dimensions"].items(), key=lambda kv: kv[1]["score"])
        self.assertEqual(result["bottleneck"], lowest[0])

    def test_no_dimension_score_is_fabricated_above_100_or_below_0(self):
        result = cr.commercial_readiness_score(
            reality_audit_results={"percentages": {"REAL": 98.8}},
            channel_statuses={}, decisions_path="C:/definitely/not/real.jsonl",
        )
        for name, d in result["dimensions"].items():
            if d["score"] is not None:
                self.assertGreaterEqual(d["score"], 0.0, name)
                self.assertLessEqual(d["score"], 100.0, name)


class TestCommercialReadinessSnapshotRecorder(unittest.TestCase):
    def test_recorder_is_additive_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap_path = os.path.join(tmp, "commercial_readiness_snapshots.jsonl")
            fake_score = {"overall": 42.0, "bottleneck": "financial", "dimensions": {"financial": {"score": 0.0}}}
            cr.record_commercial_readiness_snapshot(score_result=fake_score, snapshots_path=snap_path)
            history_1 = cr.commercial_readiness_history(snapshots_path=snap_path)
            self.assertEqual(len(history_1["entries"]), 1)

            cr.record_commercial_readiness_snapshot(score_result=fake_score, snapshots_path=snap_path)
            history_2 = cr.commercial_readiness_history(snapshots_path=snap_path)
            self.assertEqual(len(history_2["entries"]), 2)
            # first entry untouched
            self.assertEqual(history_2["entries"][0], history_1["entries"][0])

    def test_history_honestly_empty_before_any_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap_path = os.path.join(tmp, "does_not_exist.jsonl")
            result = cr.commercial_readiness_history(snapshots_path=snap_path)
            self.assertEqual(result["entries"], [])
            self.assertTrue(result["reason"])

    def test_recorded_entry_matches_the_real_score_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap_path = os.path.join(tmp, "commercial_readiness_snapshots.jsonl")
            fake_score = {"overall": 42.0, "bottleneck": "financial", "dimensions": {"financial": {"score": 0.0}, "legal": {"score": 40.0}}}
            entry = cr.record_commercial_readiness_snapshot(score_result=fake_score, snapshots_path=snap_path)
            self.assertEqual(entry["overall"], 42.0)
            self.assertEqual(entry["bottleneck"], "financial")
            self.assertEqual(entry["dimension_scores"], {"financial": 0.0, "legal": 40.0})
            self.assertIn("generated_at", entry)


class TestCommercialReadinessTrend(unittest.TestCase):
    def test_not_enough_data_with_zero_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap_path = os.path.join(tmp, "does_not_exist.jsonl")
            result = cr.commercial_readiness_trend(snapshots_path=snap_path)
            self.assertEqual(result["trend"], "NOT_ENOUGH_DATA")
            self.assertEqual(result["real_snapshot_count"], 0)

    def test_not_enough_data_with_one_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap_path = os.path.join(tmp, "commercial_readiness_snapshots.jsonl")
            cr.record_commercial_readiness_snapshot(score_result={"overall": 10.0, "bottleneck": "financial", "dimensions": {}}, snapshots_path=snap_path)
            result = cr.commercial_readiness_trend(snapshots_path=snap_path)
            self.assertEqual(result["trend"], "NOT_ENOUGH_DATA")
            self.assertEqual(result["real_snapshot_count"], 1)

    def test_improving_never_fabricated_from_a_flat_or_declining_real_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap_path = os.path.join(tmp, "commercial_readiness_snapshots.jsonl")
            cr.record_commercial_readiness_snapshot(score_result={"overall": 30.0, "bottleneck": "financial", "dimensions": {}}, snapshots_path=snap_path)
            cr.record_commercial_readiness_snapshot(score_result={"overall": 20.0, "bottleneck": "financial", "dimensions": {}}, snapshots_path=snap_path)
            result = cr.commercial_readiness_trend(snapshots_path=snap_path)
            self.assertEqual(result["trend"], "DECLINING")
            self.assertEqual(result["delta"], -10.0)
            self.assertEqual(result["real_snapshot_count"], 2)


if __name__ == "__main__":
    unittest.main()
