#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GALAXY FORGE V5.4 -- Founder Command Center regression tests.

Offline. Verifies the V5.4 governance contract, not exact live numbers:
truth-first money panel, Founder privacy (no secret values), the mandatory
business-language translation layer, and the 10-question Founder experience
test (Sec 36). Pure citation -- this test never writes, publishes, or spends.
"""

import json
import os
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import founder_command_center as fcc


class TestFounderCommandCenter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = fcc.build_founder_command_center()

    def test_top_level_sections_present(self):
        for key in ("truth", "company_status", "money", "customers",
                    "opportunities", "operations", "factory_feed", "health",
                    "current_priority", "sub001", "portfolio",
                    "founder_actions", "security", "notifications",
                    "daily_summary", "weekly_review", "next_best_actions",
                    "commercial_validation", "market_discovery",
                    "technical_details"):
            self.assertIn(key, self.report, key)

    def test_commercial_validation_honest(self):
        cv = self.report["commercial_validation"]
        self.assertIn(cv["reality_integrity"]["state"], ("PASS", "BLOCKED", "UNKNOWN"))
        # BLOCKED must name its failed checks; UNKNOWN must admit staleness.
        if cv["reality_integrity"]["state"] == "BLOCKED":
            self.assertTrue(cv["reality_integrity"]["failed_checks"])
        self.assertIsInstance(cv["active_experiments"], int)
        for w in cv["experiment_windows"]:
            for k in ("id", "offer", "status", "ends", "next"):
                self.assertIn(k, w, k)

    def test_market_discovery_honest(self):
        md = self.report["market_discovery"]
        self.assertIsInstance(md["market_signals"], int)
        self.assertGreaterEqual(md["market_signals"], 1)
        self.assertEqual(md["transactions"], 0)
        self.assertEqual(md["qualified_demand"], 0)
        # No DEMAND word inflation: levels carry only ladder terms.
        for level in md["by_level"]:
            self.assertIn(level, ("TREND", "SIGNAL", "INTEREST", "INTENT",
                                  "QUALIFIED_DEMAND", "TRANSACTION"))
        for g in md["gates"]:
            self.assertIn(g["gate"], ("GATE_A", "GATE_B", "GATE_C",
                                      "GATE_D", "GATE_E"))
        self.assertTrue(md["top_blocker"])
        self.assertTrue(md["next_discovery_action"])

    def test_truth_first_money_panel(self):
        money = self.report["money"]
        if money["verified_sales_count"] == 0:
            self.assertEqual(money["headline"], "VERIFIED REVENUE: $0")
        else:
            self.assertIn("VERIFIED REVENUE: $", money["headline"])
        # Technical activity is never counted as revenue (Sec 5).
        joined = " ".join(money["not_counted_as_revenue"]).lower()
        for non_revenue in ("clicks", "published products", "generated assets"):
            self.assertIn(non_revenue, joined)
        self.assertEqual(money["currency"], "USD")

    def test_no_secret_values_in_output(self):
        blob = json.dumps(self.report, ensure_ascii=False)
        # No secret-looking token material anywhere in the report.
        self.assertNotIn("sk-live", blob)
        self.assertNotIn("sk-test", blob)
        # Real configured secret VALUES must never leak: if the environment
        # holds them, their values must not appear in the report.
        for name in ("GROQ_KEY", "PADDLE_WEBHOOK_SECRET", "GUMROAD_ACCESS_TOKEN",
                     "MISSION_CONTROL_PASSWORD", "AMAZON_ASSOCIATE_TAG"):
            value = os.environ.get(name)
            if value and len(value) >= 8:
                self.assertNotIn(value, blob, name)
        # The secrets section lists configuration NAMES only.
        configured = self.report["security"]["secrets"].get("configured", [])
        for entry in configured:
            self.assertRegex(entry, r"^[A-Z][A-Z0-9_]+$")

    def test_translation_layer_never_implies_success(self):
        self.assertEqual(fcc.humanize("UNKNOWN"), "No reliable evidence yet")
        self.assertEqual(fcc.humanize("FOUNDER_ACTION_REQUIRED"),
                         "Your decision is needed")
        self.assertEqual(fcc.humanize(None), "No reliable evidence yet")
        # Unknown codes stay visible as unknown -- never green/success (Sec 26).
        strange = fcc.humanize("SOME_WEIRD_INTERNAL_CODE_XYZ")
        self.assertIn("No reliable evidence yet", strange)
        for success_word in ("healthy", "successful", "promising", "Completed", "SAFE"):
            self.assertNotIn(success_word, strange)

    def test_health_is_dimensions_not_single_score(self):
        health = self.report["health"]
        for dim in ("security", "commercial", "operations",
                    "automation", "founder_load", "market_access"):
            self.assertIn("state", health[dim], dim)
            self.assertIn("meaning", health[dim], dim)
        self.assertNotIn("score", {k.lower() for k in health.keys()},
                         "no single blended company score allowed (Sec 13)")

    def test_retention_honest_without_customers(self):
        retention = self.report["customers"]["retention"]
        if self.report["customers"]["real_customers"] == 0:
            self.assertIn("WAITING FOR FIRST VERIFIED CUSTOMER",
                          retention["status"])

    def test_founder_experience_ten_questions(self):
        r = self.report
        self.assertTrue(r["money"]["headline"])                                  # T1 money?
        self.assertIn("real_customers", r["customers"])                          # T2 customers?
        self.assertTrue(r["customers"].get("journey_stops_at"))                 # T3 journey stop?
        self.assertTrue(r["current_priority"].get("current_priority"))          # T4 factory now?
        self.assertIn("new_discoveries_14d", r["opportunities"])                # T5 new opps?
        self.assertIn("blocked_operations", r["operations"])                    # T6 blocking?
        self.assertIn("actions", r["founder_actions"])                          # T7 my actions?
        for opp in r["opportunities"].get("radar", []):                         # T8 evidence?
            self.assertTrue(opp.get("evidence"))
        self.assertTrue(r["security"].get("state"))                             # T9 secure?
        self.assertTrue(r["founder_actions"].get("one_next_action"))            # T10 next decision?

    def test_next_best_actions_cited_not_scored(self):
        nba = self.report["next_best_actions"]
        self.assertLessEqual(len(nba["actions"]), 7)
        self.assertGreaterEqual(len(nba["actions"]), 1)
        blob = json.dumps(nba, ensure_ascii=False)
        for key in ("action", "why", "evidence", "source"):
            for a in nba["actions"]:
                self.assertTrue(a.get(key), key)
        # No invented success ranking or revenue probabilities (V5.5 Sec 12).
        for forbidden in ("probability", "expected revenue", "success rate",
                          "projected income", "% chance"):
            self.assertNotIn(forbidden, blob.lower())

    def test_founder_actions_are_business_language(self):
        for action in self.report["founder_actions"]["actions"]:
            for key in ("what", "why", "what_factory_already_did",
                        "what_happens_if_approved", "what_you_need_to_do",
                        "risk", "choices"):
                self.assertIn(key, action, key)
            blob = json.dumps(action)
            # Never ask the Founder to do technical work (Sec 10).
            for technical in ("Edit config/", "edit JSON", "inspect logs",
                              "run a terminal command", "reality.json"):
                self.assertNotIn(technical, blob)
            self.assertIn(action["risk"], ("LOW", "MEDIUM", "HIGH"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
