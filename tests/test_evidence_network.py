"""Tests for evidence_network.py (Evidence Connector registry, ADR-128,
2026-07-25).

    python -m unittest tests.test_evidence_network -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import evidence_completeness as ec
import evidence_network as en


class TestRegistryStructure(unittest.TestCase):
    def test_every_registered_connector_has_all_required_fields(self):
        for c in en.EVIDENCE_CONNECTOR_REGISTRY:
            d = c.to_dict()
            for field in ("name", "source", "criteria_resolved", "status", "reliability", "refresh_frequency", "cost", "latency", "confidence_contribution"):
                self.assertIn(field, d)
                self.assertIsNotNone(d[field], f"{c.name}.{field} must not be None")

    def test_every_status_is_real_or_discovery(self):
        for c in en.EVIDENCE_CONNECTOR_REGISTRY:
            self.assertIn(c.status, (en.REAL, en.DISCOVERY))

    def test_real_connectors_have_a_real_callable_fetch(self):
        for c in en.EVIDENCE_CONNECTOR_REGISTRY:
            if c.status == en.REAL:
                self.assertTrue(callable(c.fetch), f"{c.name} is REAL but has no callable fetch")

    def test_discovery_connectors_have_no_fetch(self):
        """Founder rule: never fabricate a working connector -- a
        DISCOVERY connector genuinely cannot be called."""
        for c in en.EVIDENCE_CONNECTOR_REGISTRY:
            if c.status == en.DISCOVERY:
                self.assertIsNone(c.fetch, f"{c.name} is DISCOVERY but has a real fetch — should be REAL")

    def test_every_criterion_from_evidence_completeness_has_at_least_one_declared_connector(self):
        """Founder rule 1 (ADR-128): every UNKNOWN criterion must declare
        which evidence source could resolve it — even the always-
        deterministic ones (which are honestly reported by
        evidence_completeness._research_action_for as needing no source),
        and even the permanent gaps must have SOME name to work toward."""
        undeclared = []
        for criterion in ec.CRITERIA:
            if not en.connectors_for_criterion(criterion) and criterion not in (
                "low_or_moderate_competition", "premium_pricing_potential",
                "global_scalability", "long_term_strategic_value", "high_profit_margin",
                "ai_significant_advantage",
            ):
                undeclared.append(criterion)
        self.assertEqual(undeclared, [], f"criteria with no declared evidence source at all: {undeclared}")


class TestConnectorsForCriterion(unittest.TestCase):
    def test_difficult_to_copy_has_a_real_connector(self):
        connectors = en.connectors_for_criterion("difficult_to_copy")
        self.assertTrue(any(c.status == en.REAL for c in connectors))

    def test_pain_severity_has_a_real_connector(self):
        connectors = en.connectors_for_criterion("pain_severity")
        self.assertTrue(any(c.status == en.REAL for c in connectors))

    def test_proof_of_payment_now_has_a_real_connector(self):
        """Evidence Network upgrade (payment_evidence_connector.py): the
        single highest-weighted gate (proof_of_payment, ADR-121) went from
        DISCOVERY-only to a real, callable connector reusing the same three
        free keyless sources as customer_pain."""
        connectors = en.connectors_for_criterion("proof_of_payment")
        self.assertTrue(len(connectors) > 0)
        self.assertTrue(any(c.status == en.REAL for c in connectors))

    def test_real_connectors_sort_before_discovery_ones(self):
        connectors = en.connectors_for_criterion("proof_of_payment")
        statuses = [c.status for c in connectors]
        self.assertEqual(statuses, sorted(statuses, key=lambda s: s != en.REAL))

    def test_real_connector_for_criterion_returns_none_when_only_discovery_exists(self):
        self.assertIsNone(en.real_connector_for_criterion("high_commercial_value"))

    def test_real_connector_for_criterion_returns_the_real_one(self):
        c = en.real_connector_for_criterion("difficult_to_copy")
        self.assertIsNotNone(c)
        self.assertEqual(c.status, en.REAL)


class TestResolveCriterion(unittest.TestCase):
    def test_resolve_unbuilt_criterion_declares_sources_without_attempting(self):
        result = en.resolve_criterion("high_commercial_value", "test niche")
        self.assertFalse(result["attempted"])
        self.assertIsNone(result["connector"])
        self.assertTrue(len(result["declared_sources"]) > 0)

    def test_resolve_real_criterion_calls_the_real_connector(self):
        with patch("competitor_discovery.get_or_refresh_competitors", return_value={"total_found": 2}) as mock_fn:
            result = en.resolve_criterion("difficult_to_copy", "test niche")
            mock_fn.assert_called_once()
        self.assertTrue(result["attempted"])
        self.assertTrue(result["acquired"])
        self.assertEqual(result["connector"], "competitor_discovery")

    def test_resolve_handles_a_real_exception_honestly(self):
        with patch("competitor_discovery.get_or_refresh_competitors", side_effect=RuntimeError("real network failure")):
            result = en.resolve_criterion("difficult_to_copy", "test niche")
        self.assertTrue(result["attempted"])
        self.assertFalse(result["acquired"])
        self.assertIn("real network failure", result["error"])


class TestNetworkStatusReport(unittest.TestCase):
    def test_reports_real_and_discovery_connectors_separately(self):
        report = en.network_status_report()
        self.assertEqual(len(report["real_connectors"]) + len(report["discovery_connectors"]), report["total_connectors"])
        self.assertTrue(len(report["real_connectors"]) >= 2)
        self.assertTrue(len(report["discovery_connectors"]) >= 1)

    def test_criteria_with_real_coverage_matches_real_connectors(self):
        report = en.network_status_report()
        self.assertIn("difficult_to_copy", report["criteria_with_real_automated_coverage"])
        self.assertIn("pain_severity", report["criteria_with_real_automated_coverage"])

    def test_declared_but_not_real_excludes_criteria_that_already_have_real_coverage(self):
        report = en.network_status_report()
        self.assertNotIn("difficult_to_copy", report["criteria_declared_but_not_yet_real"])
        self.assertNotIn("proof_of_payment", report["criteria_declared_but_not_yet_real"])

    def test_proof_of_payment_now_in_real_automated_coverage(self):
        report = en.network_status_report()
        self.assertIn("proof_of_payment", report["criteria_with_real_automated_coverage"])


if __name__ == "__main__":
    unittest.main()
