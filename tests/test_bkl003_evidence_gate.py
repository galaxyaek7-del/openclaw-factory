"""BKL-003: evidence validation separates REAL evidence from labelled simulation.

Offline. No network, no file writes.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from affiliate.opportunities import validate_evidence  # noqa: E402


class TestBKL003EvidenceGate(unittest.TestCase):
    def test_real_mode_rejects_placeholder(self):
        result = validate_evidence({}, mode="REAL")
        self.assertFalse(result["valid"])
        self.assertEqual(result["error"], "EVIDENCE_INCOMPLETE")
        self.assertEqual(sorted(result["missing_fields"]), ["confidence", "data_url", "source", "timestamp"])

    def test_simulation_mode_accepts_placeholder(self):
        result = validate_evidence({"placeholder": True}, mode="SIMULATION")
        self.assertTrue(result["valid"])
        self.assertFalse(result["real_evidence"])
        self.assertEqual(result["warning"], "SYNTHETIC_EVIDENCE_ACCEPTED")

    def test_real_mode_accepts_complete_evidence(self):
        result = validate_evidence({
            "source": "gumroad",
            "timestamp": "2026-10-16T10:11:00Z",
            "confidence": 0.85,
            "data_url": "https://gumroad.com/...",
        }, mode="REAL")
        self.assertTrue(result["valid"])
        self.assertTrue(result["real_evidence"])


if __name__ == "__main__":
    unittest.main()
