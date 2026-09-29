#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V6.0 regression tests: root-cause blockers + access experiment.

Offline, hermetic: schema + honesty invariants only. Proves cause states
are restricted to the allowed vocabulary, no CONFIRMED-without-evidence
shortcuts in structure, experiment never claims execution, budget $0.
"""

import json
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))


def _load_jsonl(name):
    rows = []
    with open(_FACTORY_ROOT / "data" / name, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class TestRootCauseBlockers(unittest.TestCase):
    def test_14_fields(self):
        rows = _load_jsonl("v60_market_access_blockers.jsonl")
        required = ("blocker_id", "affected_channel", "affected_offer",
                    "observed_problem", "evidence_reference",
                    "root_cause_status", "confirmed_cause",
                    "possible_causes", "confidence", "repair_options",
                    "cost", "founder_approval_required", "next_action",
                    "status")
        self.assertGreaterEqual(len(rows), 1)
        for r in rows:
            for k in required:
                self.assertIn(k, r, (r.get("blocker_id"), k))

    def test_cause_vocabulary_restricted(self):
        for r in _load_jsonl("v60_market_access_blockers.jsonl"):
            self.assertIn(r["root_cause_status"],
                          ("CONFIRMED", "LIKELY", "POSSIBLE", "UNKNOWN"))

    def test_confirmed_has_cause_or_empty_possible(self):
        for r in _load_jsonl("v60_market_access_blockers.jsonl"):
            if r["root_cause_status"] == "CONFIRMED":
                self.assertTrue(r["confirmed_cause"],
                                r["blocker_id"])
            else:
                self.assertTrue(r["possible_causes"] or r["confirmed_cause"] == "",
                                r["blocker_id"])


class TestAccessExperiment(unittest.TestCase):
    def test_20_fields_and_prepared_not_executed(self):
        rows = _load_jsonl("v60_market_access_experiments.jsonl")
        required = ("experiment_id", "offer_id", "audience", "problem",
                    "channel", "content_reference", "permission_status",
                    "publication_method", "hypothesis", "start_timestamp",
                    "observation_window", "exposure_measurement",
                    "response_measurement", "intent_measurement",
                    "transaction_measurement", "budget",
                    "approval_status", "status", "evidence", "result",
                    "next_action")
        self.assertGreaterEqual(len(rows), 1)
        for r in rows:
            for k in required:
                self.assertIn(k, r, (r.get("experiment_id"), k))
            self.assertEqual(r["budget"], "$0")
            self.assertNotEqual(r["status"], "EXECUTED")

    def test_no_success_claims(self):
        blob = json.dumps(_load_jsonl("v60_market_access_experiments.jsonl")).lower()
        for forbidden in ("exposure_observed", "response_observed",
                          "transaction_verified", "success"):
            self.assertNotIn(forbidden, blob)


if __name__ == "__main__":
    unittest.main(verbosity=2)
