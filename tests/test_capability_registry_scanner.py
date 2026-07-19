"""Tests for capability_registry_scanner.py (EOS Phase 1, 2026-07-19).

Runs with stdlib unittest. Every function reads only from a temp-file-
isolated fixture -- never the real config/capability_registry.json.

    python -m unittest tests.test_capability_registry_scanner -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import capability_registry_scanner as scanner


def _write_registry(capabilities, last_updated="2026-07-19"):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_note": "x", "last_updated": last_updated, "capabilities": capabilities}, f)
    return path


class TestFindCapabilityGaps(unittest.TestCase):
    def tearDown(self):
        for p in getattr(self, "_paths", []):
            if os.path.exists(p):
                os.remove(p)

    def test_missing_file_returns_honest_empty(self):
        result = scanner.find_capability_gaps(registry_path="/no/such/registry.json")
        self.assertEqual(result["discovery_level"], [])
        self.assertEqual(result["estimated_level"], [])

    def test_filters_by_level_correctly(self):
        capabilities = [
            {"id": "a", "level": "REAL"},
            {"id": "b", "level": "DISCOVERY"},
            {"id": "c", "level": "ESTIMATED"},
            {"id": "d", "level": "DISCOVERY"},
        ]
        path = _write_registry(capabilities)
        self._paths = [path]
        result = scanner.find_capability_gaps(registry_path=path)
        self.assertEqual(len(result["discovery_level"]), 2)
        self.assertEqual(len(result["estimated_level"]), 1)
        self.assertEqual(result["total_capabilities"], 4)
        # REAL-level capability must never be flagged
        self.assertNotIn("a", [c["id"] for c in result["discovery_level"] + result["estimated_level"]])

    def test_include_estimated_false_omits_estimated_level(self):
        capabilities = [{"id": "a", "level": "ESTIMATED"}]
        path = _write_registry(capabilities)
        self._paths = [path]
        result = scanner.find_capability_gaps(registry_path=path, include_estimated=False)
        self.assertEqual(result["estimated_level"], [])

    def test_real_registry_never_throws(self):
        result = scanner.find_capability_gaps()
        self.assertIn("discovery_level", result)
        self.assertIn("total_capabilities", result)


if __name__ == "__main__":
    unittest.main()
