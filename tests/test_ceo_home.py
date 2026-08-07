import json
import os
import tempfile
import unittest
from unittest.mock import patch

import ceo_home


class TestCeoHomeBriefing(unittest.TestCase):
    def test_products_summary_counts_real_data_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            reality_path = os.path.join(tmp, "reality.json")
            decisions_path = os.path.join(tmp, "decisions.jsonl")
            finance_path = os.path.join(tmp, "finance.json")
            with open(reality_path, "w", encoding="utf-8") as f:
                json.dump({"published_books": [{"title": "x"}]}, f)
            with open(decisions_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"niche": "a", "status": "ACCEPTED"}) + "\n")
                f.write(json.dumps({"niche": "b", "status": "DEFERRED"}) + "\n")
                f.write(json.dumps({"niche": "c", "status": "REJECTED"}) + "\n")
            with open(finance_path, "w", encoding="utf-8") as f:
                json.dump({"sales": [{"product": "real-product", "amount": 10}, {"product": "smoke-DELETE-ME", "amount": 5}]}, f)

            with patch.object(ceo_home, "_REALITY_PATH", reality_path), \
                 patch.object(ceo_home, "_DECISIONS_PATH", decisions_path), \
                 patch.object(ceo_home, "_FINANCE_PATH", finance_path):
                result = ceo_home._products_summary()
                self.assertEqual(result["products_ready"], 1)
                self.assertEqual(result["products_waiting"], 1)
                self.assertEqual(result["products_selling"], 1)
                self.assertEqual(result["active_opportunities"], 2)

    def test_financial_summary_excludes_smoke_test_sale(self):
        with tempfile.TemporaryDirectory() as tmp:
            finance_path = os.path.join(tmp, "finance.json")
            cost_path = os.path.join(tmp, "cost.jsonl")
            with open(finance_path, "w", encoding="utf-8") as f:
                json.dump({"sales": [{"product": "contract-test-ladder-DELETE-ME", "amount": 150}]}, f)
            with open(cost_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"cost_usd": 0.01}) + "\n")

            with patch.object(ceo_home, "_FINANCE_PATH", finance_path), \
                 patch.object(ceo_home, "_AI_COST_LOG_PATH", cost_path):
                result = ceo_home._financial_summary()
                self.assertEqual(result["revenue"], 0)
                self.assertEqual(result["expenses"], 0.01)

    def test_technical_readiness_none_when_ledger_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = os.path.join(tmp, "evidence_ledger.jsonl")
            open(ledger_path, "w", encoding="utf-8").close()
            with patch.object(ceo_home, "_EVIDENCE_LEDGER_PATH", ledger_path):
                result = ceo_home._technical_readiness_from_ledger()
                self.assertIsNone(result["score"])

    def test_technical_readiness_uses_most_recent_day_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = os.path.join(tmp, "evidence_ledger.jsonl")
            with open(ledger_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"module": "reality_audit:x", "output": "NOT_IMPLEMENTED", "timestamp": "2026-08-01T00:00:00Z"}) + "\n")
                f.write(json.dumps({"module": "reality_audit:y", "output": "REAL", "timestamp": "2026-08-07T00:00:00Z"}) + "\n")
                f.write(json.dumps({"module": "reality_audit:z", "output": "REAL", "timestamp": "2026-08-07T01:00:00Z"}) + "\n")
            with patch.object(ceo_home, "_EVIDENCE_LEDGER_PATH", ledger_path):
                result = ceo_home._technical_readiness_from_ledger()
                self.assertEqual(result["score"], 100.0)
                self.assertEqual(result["as_of"], "2026-08-07")

    def test_highest_roi_opportunity_picks_max_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            decisions_path = os.path.join(tmp, "decisions.jsonl")
            with open(decisions_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"niche": "low", "status": "DEFERRED", "opportunity_score": 40}) + "\n")
                f.write(json.dumps({"niche": "high", "status": "ACCEPTED", "opportunity_score": 90}) + "\n")
                f.write(json.dumps({"niche": "rejected-but-high", "status": "REJECTED", "opportunity_score": 99}) + "\n")
            result = ceo_home._highest_roi_opportunity(decisions_path)
            self.assertEqual(result["niche"], "high")

    def test_critical_risks_excludes_resolved_incidents(self):
        with tempfile.TemporaryDirectory() as tmp:
            incidents_path = os.path.join(tmp, "incidents.jsonl")
            with open(incidents_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"incident_id": "a", "event": "opened", "area": "x"}) + "\n")
                f.write(json.dumps({"incident_id": "a", "event": "resolved", "area": "x"}) + "\n")
                f.write(json.dumps({"incident_id": "b", "event": "opened", "area": "y"}) + "\n")
            with patch.object(ceo_home, "_INCIDENTS_PATH", incidents_path):
                result = ceo_home._critical_risks()
                self.assertEqual(result["count"], 1)
                self.assertEqual(result["items"][0]["area"], "y")

    def test_todays_recommendation_honestly_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "executive_directives.jsonl")
            open(path, "w", encoding="utf-8").close()
            with patch.object(ceo_home, "_EXECUTIVE_DIRECTIVES_PATH", path):
                result = ceo_home._todays_executive_recommendation()
                self.assertIsNone(result["recommendation"])


if __name__ == "__main__":
    unittest.main()
