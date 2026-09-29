#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V5.9 regression tests: access inventory, exposure experiments, blockers.

Offline, hermetic: validates the structure and honesty invariants of the
V5.9 artifacts (no invented accounts, no estimated exposure, no revenue
claims) -- never network, never production mutation.
"""

import json
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))


def _load_json(name):
    with open(_FACTORY_ROOT / "data" / name, encoding="utf-8") as f:
        return json.load(f)


def _load_jsonl(name):
    rows = []
    with open(_FACTORY_ROOT / "data" / name, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class TestAccessInventory(unittest.TestCase):
    def test_17_fields_per_channel(self):
        inv = _load_json("v59_market_access_inventory.json")
        required = ("channel_id", "channel_name", "platform",
                    "target_audience", "audience_relevance",
                    "current_account_or_asset", "permitted_activity",
                    "terms_review_status", "publishing_status",
                    "access_status", "tracking_capability", "current_offer",
                    "known_blocker", "approval_required",
                    "evidence_reference", "next_action", "status")
        self.assertGreaterEqual(len(inv["channels"]), 1)
        for c in inv["channels"]:
            for k in required:
                self.assertIn(k, c, (c.get("channel_id"), k))

    def test_no_invented_assets(self):
        inv = _load_json("v59_market_access_inventory.json")
        blob = json.dumps(inv).lower()
        for forbidden in ("partnership with", "10k followers", "guaranteed reach"):
            self.assertNotIn(forbidden, blob)

    def test_unverifiable_terms_flagged(self):
        inv = _load_json("v59_market_access_inventory.json")
        gated = [c for c in inv["channels"]
                 if c.get("approval_required", "").lower().startswith("founder")
                 or "founder" in c.get("approval_required", "").lower()
                 or "founder" in c.get("known_blocker", "").lower()]
        self.assertGreaterEqual(len(gated), 1)


class TestExposureExperiments(unittest.TestCase):
    def test_19_fields_and_zero_budget(self):
        rows = _load_jsonl("v59_exposure_experiments.jsonl")
        required = ("experiment_id", "hypothesis", "offer_id",
                    "target_audience", "channel", "content_reference",
                    "permission_status", "test_start", "observation_window",
                    "exposure_success_condition",
                    "response_success_condition",
                    "intent_success_condition", "measurement_method",
                    "budget", "risks", "status", "observed_result",
                    "evidence_reference", "next_action")
        self.assertGreaterEqual(len(rows), 1)
        for r in rows:
            for k in required:
                self.assertIn(k, r, (r.get("experiment_id"), k))
            self.assertEqual(r["budget"], "$0")

    def test_no_estimated_sample_sizes(self):
        blob = json.dumps(_load_jsonl("v59_exposure_experiments.jsonl")).lower()
        for forbidden in ("statistical significance", "n=1000", "guaranteed impressions"):
            self.assertNotIn(forbidden, blob)


class TestExposureBlockers(unittest.TestCase):
    def test_11_fields_and_honest_cause_split(self):
        rows = _load_jsonl("v59_exposure_blockers.jsonl")
        required = ("blocker_id", "affected_channel", "affected_offer",
                    "observed_symptom", "evidence", "likely_cause",
                    "cause_confidence", "safe_repair",
                    "founder_approval_required", "status", "next_action")
        self.assertGreaterEqual(len(rows), 1)
        for r in rows:
            for k in required:
                self.assertIn(k, r, (r.get("blocker_id"), k))

    def test_revenue_never_claimed(self):
        blob = json.dumps(_load_jsonl("v59_exposure_blockers.jsonl"))
        self.assertNotIn("VERIFIED REVENUE = $", blob.replace("$0", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
