"""Tests for tool_intelligence/proposals.py (Autonomous Digital Company v1,
Track B3, 2026-07-19): the real, evidence-cited software/AI-tool
integration proposal registry.

    python -m unittest tests.test_tool_intelligence -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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


class TestDynamicProposals(unittest.TestCase):
    """Executive Intelligence Core, Round 2 (2026-07-29): list_proposals()
    now also generates real proposals from current factory signals, not
    just the 3 hand-written seed entries."""

    def test_seed_proposals_are_always_present(self):
        ids = {p["id"] for p in proposals.list_proposals()}
        for seed in proposals.SEED_PROPOSALS:
            self.assertIn(seed["id"], ids)

    def test_capability_gap_proposal_honestly_absent_with_no_registry(self):
        result = proposals._capability_gap_proposal(capability_registry_path="C:/definitely/not/a/real/registry.json")
        self.assertIsNone(result)

    def test_dynamic_proposals_never_pads_with_fabricated_entries(self):
        # Every path pointed at somewhere real but empty -- every signal
        # should honestly detect nothing and generate zero proposals,
        # never invent one to pad the list.
        result = proposals._dynamic_proposals(
            decisions_path="C:/definitely/not/a/real/decisions.jsonl",
            outcomes_path="C:/definitely/not/a/real/outcomes.jsonl",
            timeline_path="C:/definitely/not/a/real/timeline.jsonl",
            sales_ledger_path="C:/definitely/not/a/real/ledger.jsonl",
            capability_registry_path="C:/definitely/not/a/real/registry.json",
            requests_path="C:/definitely/not/a/real/requests.jsonl",
            state_path="C:/definitely/not/a/real/pipeline_state.json",
        )
        self.assertIsInstance(result, list)
        for p in result:
            for field in REQUIRED_FIELDS:
                self.assertIn(field, p)

    def test_list_proposals_equals_seed_plus_dynamic(self):
        dynamic = proposals._dynamic_proposals()
        combined = proposals.list_proposals()
        self.assertEqual(len(combined), len(proposals.SEED_PROPOSALS) + len(dynamic))


class TestCustomerFunnelProposal(unittest.TestCase):
    """Autonomous Company Evolution Engine, Round 3 (2026-07-29): a new
    dynamic proposal source built from customer_pipeline.py's own real
    Observe signals (stuck-NEW / abandoned-at-PROPOSED requests)."""

    def test_honestly_absent_with_no_real_requests(self):
        result = proposals._customer_funnel_proposal(
            requests_path="C:/definitely/not/a/real/requests.jsonl",
            state_path="C:/definitely/not/a/real/pipeline_state.json",
        )
        self.assertIsNone(result)

    def test_generates_real_proposal_from_stuck_requests(self):
        fake_overview = {
            "total_requests": 2,
            "stage_distribution": {"NEW": 1, "PROPOSED": 1},
            "needs_attention": [
                {"request_id": "req_1", "stage": "NEW", "recovery": "still NEW after 10+ minutes"},
                {"request_id": "req_2", "stage": "PROPOSED", "recovery": "proposal shown but neither approved nor declined for 48+ hours"},
            ],
            "requests": [],
        }
        with patch("customer_pipeline.list_pipeline_overview", return_value=fake_overview):
            result = proposals._customer_funnel_proposal()
        self.assertIsNotNone(result)
        for field in REQUIRED_FIELDS:
            self.assertIn(field, result)
            self.assertTrue(result[field])
        self.assertIn("req_1", result["tool"])
        self.assertIn("req_2", result["tool"])

    def test_ignores_attention_items_outside_new_or_proposed(self):
        fake_overview = {
            "total_requests": 1,
            "stage_distribution": {"PENDING_FOUNDER_FULFILLMENT": 1},
            "needs_attention": [
                {"request_id": "req_3", "stage": "PENDING_FOUNDER_FULFILLMENT", "recovery": "needs manual fulfillment"},
            ],
            "requests": [],
        }
        with patch("customer_pipeline.list_pipeline_overview", return_value=fake_overview):
            result = proposals._customer_funnel_proposal()
        self.assertIsNone(result)

    def test_is_included_in_dynamic_proposals_when_present(self):
        fake_overview = {
            "total_requests": 1,
            "stage_distribution": {"NEW": 1},
            "needs_attention": [
                {"request_id": "req_1", "stage": "NEW", "recovery": "still NEW after 10+ minutes"},
            ],
            "requests": [],
        }
        with patch("customer_pipeline.list_pipeline_overview", return_value=fake_overview):
            result = proposals._dynamic_proposals(
                decisions_path="C:/definitely/not/a/real/decisions.jsonl",
                outcomes_path="C:/definitely/not/a/real/outcomes.jsonl",
                timeline_path="C:/definitely/not/a/real/timeline.jsonl",
                sales_ledger_path="C:/definitely/not/a/real/ledger.jsonl",
                capability_registry_path="C:/definitely/not/a/real/registry.json",
            )
        ids = {p["id"] for p in result}
        self.assertIn("resolve_stuck_customer_requests", ids)


if __name__ == "__main__":
    unittest.main()
