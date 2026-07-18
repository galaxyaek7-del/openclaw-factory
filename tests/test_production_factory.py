"""Tests for production_factory/ (Phase 7).

Runs with stdlib unittest. Never spends money, never executes real
production — this package only assembles dossiers from data already
computed.

    python -m unittest tests.test_production_factory -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import registry as channel_registry
from channels.etsy_arm import EtsyArm
from channels.gumroad_arm import GumroadArm
from channels.payhip_arm import PayhipArm
from decision_engine import store
from decision_engine.types import Decision, make_decision_id

from production_factory import dossier, factory


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _accepted_decision(niche="a production factory test niche", price_str="$19", **snapshot_overrides):
    decided_at = "2026-07-16T10:00:00+00:00"
    snapshot = {
        "pricing": {"recommended_price": price_str, "note": "x"},
        "demand_pattern": {"pattern": "Evergreen", "reason": "x"},
        "competitors": {"total_found": 1, "by_category": {}},
        "opportunity_gap": 70,
        "customer_pain": {"reason": "real pain evidence"},
        "confidence": {"score": 80, "level": "high", "note": "x"},
        "risk": {"score": 90, "level": "low", "notes": []},
        "dimension_scores": {"execution": {"normalized_score": 90, "explanation": "fits book_engine"}},
    }
    snapshot.update(snapshot_overrides)
    return Decision(
        decision_id=make_decision_id(niche, "tier4", decided_at), niche=niche, tier="tier4",
        decided_at=decided_at, status="ACCEPTED", ai_ceo_decision="BUILD",
        opportunity_score=85.0, opportunity_score_accepted=True,
        reasoning=["real evidence"], evaluation_snapshot=snapshot,
    )


class TestProductionId(unittest.TestCase):
    def test_production_id_is_derived_from_decision_id_not_a_new_scheme(self):
        d = _accepted_decision().to_dict()
        pid = dossier.make_production_id(d)
        self.assertEqual(pid, f"PROD-{d['decision_id']}")


class TestCustomerProfile(unittest.TestCase):
    def test_real_audience_qualifier_is_detected(self):
        result = dossier._customer_profile("gratitude journal for teens")
        self.assertEqual(result["maturity"], "REAL")
        self.assertEqual(result["audience_qualifier"], "for teens")

    def test_no_qualifier_is_honestly_unknown(self):
        result = dossier._customer_profile("gratitude journal")
        self.assertEqual(result["maturity"], "DISCOVERY")


class TestProductTypeCapability(unittest.TestCase):
    def test_book_engine_types_are_real(self):
        caps = dossier._product_type_capability()
        self.assertIn("REAL", caps["KDP / Digital Books"])

    def test_unbuilt_types_are_honestly_not_built(self):
        caps = dossier._product_type_capability()
        for product_type in ("SaaS", "AI Tools", "APIs", "Automation Systems"):
            self.assertIn("NOT YET BUILT", caps[product_type])


class TestPublishingChecklist(unittest.TestCase):
    def setUp(self):
        # channels.registry is global, mutable, module-level state shared
        # across the whole test process — other test files (test_base_arm.py,
        # test_sales_poll.py, test_paddle_arm.py) register their own arms as
        # an import/setup side effect and never fully reset it. Found live
        # (2026-07-18 architecture review): re-registering just these 3
        # WITHOUT clearing first let `paddle` (registered by test_paddle_arm.py
        # elsewhere in the same full-suite run) leak into this test's
        # checklist, failing it only in full-suite order, never standalone —
        # a real test-isolation bug, not a paddle-arm defect. clear() first
        # so this test's platform set is authoritative regardless of what
        # ran before it in the same process.
        channel_registry.clear()
        channel_registry.register(GumroadArm())
        channel_registry.register(EtsyArm())
        channel_registry.register(PayhipArm())

    def test_checklist_reflects_real_arm_status_not_hardcoded(self):
        checklist = dossier._publishing_checklist()
        platforms = {c["platform"] for c in checklist}
        self.assertEqual(platforms, {"gumroad", "etsy", "payhip"})
        for c in checklist:
            self.assertIn(c["status"], ("ready", "unavailable", "cooldown"))


class TestPreProductionVerification(unittest.TestCase):
    def test_no_ready_platform_fails_verification_even_if_accepted(self):
        """Confirmed real state today: zero live platform API keys exist
        (BLOCKERS.md #2), so market_readiness must be False and
        all_checks_passed must be False even for an ACCEPTED decision."""
        d = _accepted_decision().to_dict()
        result = dossier._pre_production_verification(d, {"maturity": "DISCOVERY", "reason": "x"})
        self.assertFalse(result["market_readiness"]["market_ready"])
        self.assertFalse(result["all_checks_passed"])

    def test_high_risk_fails_verification(self):
        d = _accepted_decision(risk={"score": 10, "level": "high", "notes": ["blocked"]}).to_dict()
        result = dossier._pre_production_verification(d, {"maturity": "DISCOVERY", "reason": "x"})
        self.assertFalse(result["all_checks_passed"])


class TestBuildProductionDossier(unittest.TestCase):
    def test_dossier_has_every_required_section(self):
        d = _accepted_decision().to_dict()
        result = dossier.build_production_dossier(d)
        for key in (
            "production_id", "niche", "product_specification", "market_positioning",
            "customer_profile", "pricing_strategy", "asset_checklist", "quality_checklist",
            "publishing_checklist", "success_metrics", "product_type_capability",
            "pre_production_verification",
        ):
            self.assertIn(key, result)

    def test_quality_checklist_matches_real_inspectors_check_names(self):
        d = _accepted_decision().to_dict()
        result = dossier.build_production_dossier(d)
        self.assertIn("pdf_not_corrupt", result["quality_checklist"])
        self.assertIn("not_duplicate", result["quality_checklist"])


class TestRunProductionFactory(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    def test_no_accepted_opportunities_reports_honestly(self):
        result = factory.run_production_factory(decisions_path=self.decisions_path)
        self.assertEqual(result["processed"], 0)
        self.assertIn("reason", result)

    def test_accepted_opportunity_produces_exactly_one_dossier(self):
        d = _accepted_decision()
        store.append_decision(d, path=self.decisions_path)
        result = factory.run_production_factory(decisions_path=self.decisions_path)
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["dossiers"][0]["niche"], d.niche)

    def test_never_imports_orchestrator_so_it_cannot_trigger_real_execution(self):
        """Structural guarantee: only orchestrator.run_cycle(execute_
        production=True) can actually spend money or publish live in
        this factory. Neither dossier.py nor factory.py imports
        orchestrator at all -- not gated by convention, structurally
        incapable of it."""
        for module_file in (dossier.__file__, factory.__file__):
            with open(module_file, encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("import orchestrator", content)


if __name__ == "__main__":
    unittest.main()
