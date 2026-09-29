#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V6.2 regression tests: access experiment + single gate honesty.

Offline, hermetic: schema + anti-fabrication invariants. Proves the
experiment never claims execution, the gate carries all 8 fields, and no
state above PREPARED/AUTHORIZATION-pending appears without evidence.
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


class TestV62Experiment(unittest.TestCase):
    def test_21_fields(self):
        rows = _load_jsonl("v62_market_access_experiments.jsonl")
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

    def test_never_claims_execution(self):
        blob = json.dumps(_load_jsonl("v62_market_access_experiments.jsonl")).lower()
        for forbidden in ("exposure_confirmed", "response_observed",
                          "transaction_verified", "action_submitted"):
            self.assertNotIn(forbidden, blob)
        for r in _load_jsonl("v62_market_access_experiments.jsonl"):
            self.assertTrue(r["status"].startswith("PREPARED"), r["status"])
            self.assertIn("PENDING", r["approval_status"])


class TestV62Gate(unittest.TestCase):
    def test_8_fields(self):
        with open(_FACTORY_ROOT / "data" / "founder_gate_v62.json",
                  encoding="utf-8") as f:
            doc = json.load(f)
        for k in ("action", "why_required", "evidence", "risk",
                  "expected_outcome", "cost", "deadline_if_any",
                  "exact_founder_decision"):
            self.assertIn(k, doc["gate"], k)

    def test_no_credential_requests(self):
        blob = json.dumps(json.load(
            open(_FACTORY_ROOT / "data" / "founder_gate_v62.json",
                 encoding="utf-8"))).lower()
        for forbidden in ("password", "secret key", "auth code",
                          "access token", "paste your"):
            self.assertNotIn(forbidden, blob)


if __name__ == "__main__":
    unittest.main(verbosity=2)
