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


if __name__ == "__main__":
    unittest.main()
