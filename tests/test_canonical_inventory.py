"""Tier-1 tests: canonical inventory views + divergence detection."""
import unittest

import canonical_inventory as ci


class TestInventory(unittest.TestCase):
    def test_build_structure(self):
        inv = ci.build_inventory()
        self.assertIn("head", inv)
        self.assertIn("counts", inv)
        self.assertIn("entrypoints", inv)
        for e in ci.RUNTIME_ENTRYPOINTS:
            self.assertIn(e, inv["entrypoints"])

    def test_divergence_returns_list(self):
        self.assertIsInstance(ci.detect_view_divergence(), list)

    def test_synthetic_staged_source_detected(self):
        fake = {"views": {"lib/new_engine.js": "STAGED_NEW",
                          "server.js": "COMMITTED_CLEAN"},
                "entrypoints": {"server.js": "COMMITTED_CLEAN"}}
        findings = ci.detect_view_divergence(fake)
        kinds = [f["kind"] for f in findings]
        self.assertIn("STAGED_UNCOMMITTED_SOURCE", kinds)

    def test_synthetic_clean_tree_no_findings(self):
        fake = {"views": {"server.js": "COMMITTED_CLEAN"},
                "entrypoints": {"server.js": "COMMITTED_CLEAN"}}
        self.assertEqual(ci.detect_view_divergence(fake), [])

    def test_entrypoint_drift_flagged(self):
        fake = {"views": {"server.js": "WORKTREE_MODIFIED"},
                "entrypoints": {"server.js": "WORKTREE_MODIFIED"}}
        kinds = [f["kind"] for f in ci.detect_view_divergence(fake)]
        self.assertIn("ENTRYPOINT_NOT_COMMITTED_CLEAN", kinds)


if __name__ == "__main__":
    unittest.main()
