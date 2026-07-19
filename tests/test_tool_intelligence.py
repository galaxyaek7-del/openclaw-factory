"""Tests for tool_intelligence/proposals.py (Autonomous Digital Company v1,
Track B3, 2026-07-19): the real, evidence-cited software/AI-tool
integration proposal registry.

    python -m unittest tests.test_tool_intelligence -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from tool_intelligence import proposals

REQUIRED_FIELDS = [
    "id", "tool", "status", "why_needed", "expected_business_value",
    "implementation_effort", "estimated_roi", "dependencies", "risks", "evidence",
]


class TestProposals(unittest.TestCase):
    def test_at_least_two_real_proposals_exist(self):
        self.assertGreaterEqual(len(proposals.list_proposals()), 2)

    def test_every_proposal_has_all_required_fields(self):
        for p in proposals.list_proposals():
            for field in REQUIRED_FIELDS:
                self.assertIn(field, p, f"proposal {p.get('id')} missing field {field}")
                self.assertTrue(p[field], f"proposal {p.get('id')} has an empty {field}")

    def test_every_proposal_is_marked_proposed_not_implemented(self):
        for p in proposals.list_proposals():
            self.assertEqual(p["status"], "مقترَح، لا تنفيذ")

    def test_dependencies_and_risks_are_non_empty_lists(self):
        for p in proposals.list_proposals():
            self.assertIsInstance(p["dependencies"], list)
            self.assertGreater(len(p["dependencies"]), 0)
            self.assertIsInstance(p["risks"], list)
            self.assertGreater(len(p["risks"]), 0)

    def test_ids_are_unique(self):
        ids = [p["id"] for p in proposals.list_proposals()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_get_proposal_by_id(self):
        first = proposals.list_proposals()[0]
        found = proposals.get_proposal(first["id"])
        self.assertEqual(found, first)

    def test_get_proposal_missing_id_returns_none(self):
        self.assertIsNone(proposals.get_proposal("does-not-exist"))

    def test_render_markdown_proposal_includes_all_sections(self):
        p = proposals.list_proposals()[0]
        md = proposals.render_markdown_proposal(p)
        for heading in ["لماذا يُحتاج إليه", "القيمة التجارية المتوقَّعة", "جهد التنفيذ", "العائد المقدَّر", "الاعتماديات", "المخاطر", "الدليل"]:
            self.assertIn(heading, md)

    def test_render_markdown_all_includes_every_proposal(self):
        md = proposals.render_markdown_all()
        for p in proposals.list_proposals():
            self.assertIn(p["tool"], md)


if __name__ == "__main__":
    unittest.main()
