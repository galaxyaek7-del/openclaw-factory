"""Tests for commercial_execution/ (Universal Production Engine Roadmap
Step 4, 2026-07-19): the unified Publish Pipeline, PublishRecord, and
founder approval gates.

Never touches the real data/sales_ledger.jsonl or data/factory_state.json
— every test passes explicit temp paths, same discipline
tests/test_distributor.py already established.

    python -m unittest tests.test_commercial_execution -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import factory_state
from channels import registry as channel_registry
from channels.base_arm import ArmStatus, PublishResult
from schemas.product import Product

from commercial_execution.approval_gates import check_approval_gates
from commercial_execution.pipeline import (
    resolve_target_arms, build_publish_record, run_publish_pipeline,
)
from product_families.manifest import ProductManifest
from product_families import manifest as manifest_registry


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _fake_product(source_id="PROD-ce-test-1"):
    return Product(
        title="t", subtitle="", description="d", price_usd=197.0, file_path="/fake/path.pdf",
        cover_path=None, tags=[], language="ar", source_id=source_id, raw_price_hint=197.0,
        needs_pricing=False, price_source="profit_raw", product_type="techdoc",
    )


class _FakeArmMixin:
    def setUp(self):
        self._saved_arms = channel_registry.all_arms()
        channel_registry.clear()

    def tearDown(self):
        channel_registry.clear()
        for a in self._saved_arms:
            channel_registry.register(a)

    def _register_fake_arm(self, name, status=ArmStatus.READY, publish_result=None):
        fake_arm = MagicMock()
        fake_arm.name = name
        fake_arm.status.return_value = status
        fake_arm.supports.return_value = True
        if publish_result is not None:
            fake_arm.publish.return_value = publish_result
        channel_registry.register(fake_arm)
        return fake_arm


class TestResolveTargetArms(unittest.TestCase):
    def setUp(self):
        self._saved = manifest_registry.all_manifests()

    def tearDown(self):
        manifest_registry.clear()
        for m in self._saved:
            manifest_registry.register(m)

    def test_no_family_means_every_registered_arm(self):
        self.assertIsNone(resolve_target_arms(None))
        self.assertIsNone(resolve_target_arms(""))

    def test_family_with_no_manifest_means_every_registered_arm(self):
        manifest_registry.clear()
        self.assertIsNone(resolve_target_arms("kdp_books"))

    def test_family_with_a_manifest_narrows_to_its_compatible_arms(self):
        manifest_registry.register(ProductManifest(
            product_id="demo_ce_family", family="demo_ce_family", category="c",
            content_generator="a", asset_builder="b", packager="c",
            supported_marketplaces=["paddle", "shopify"],  # shopify not registered
        ))
        result = resolve_target_arms("demo_ce_family")
        self.assertNotIn("shopify", result)  # honestly excluded — no arm exists


class TestApprovalGates(_FakeArmMixin, unittest.TestCase):
    def test_ready_arms_are_autonomous_others_are_gated_with_a_reason(self):
        self._register_fake_arm("paddle", status=ArmStatus.READY)
        self._register_fake_arm("gumroad", status=ArmStatus.UNAVAILABLE)
        self._register_fake_arm("etsy", status=ArmStatus.COOLDOWN)

        result = check_approval_gates()
        autonomous_names = {a["marketplace"] for a in result["autonomous"]}
        gated_by_name = {g["marketplace"]: g for g in result["gated"]}

        self.assertEqual(autonomous_names, {"paddle"})
        self.assertEqual(set(gated_by_name), {"gumroad", "etsy"})
        self.assertIn("credentials", gated_by_name["gumroad"]["reason"])
        self.assertIn("circuit breaker", gated_by_name["etsy"]["reason"])

    def test_no_registered_arms_is_honestly_empty(self):
        result = check_approval_gates()
        self.assertEqual(result, {"gated": [], "autonomous": []})


class TestBuildPublishRecord(unittest.TestCase):
    def setUp(self):
        self.ledger_path = _temp_path(".jsonl")
        self.state_path = _temp_path(".json")

    def tearDown(self):
        for p in (self.ledger_path, self.state_path):
            if os.path.exists(p):
                os.remove(p)

    def test_real_fields_assembled_from_a_successful_outcome(self):
        product = _fake_product()
        outcomes = [{
            "arm": "paddle", "attempted": True, "ok": True, "skip_reason": None,
            "result": PublishResult(ok=True, platform="paddle", product_id="pdl_123",
                                     url="http://checkout", error=None, dry_run=False),
        }]
        record = build_publish_record(product, outcomes, version="1.0.0",
                                       ledger_path=self.ledger_path, state_path=self.state_path)
        self.assertEqual(record["product_id"], "PROD-ce-test-1")
        self.assertEqual(record["version"], "1.0.0")
        m = record["marketplaces"][0]
        self.assertEqual(m["marketplace"], "paddle")
        self.assertEqual(m["publish_status"], "ok")
        self.assertEqual(m["marketplace_id"], "pdl_123")
        self.assertEqual(m["recovery_token"], "arm_publish:paddle:PROD-ce-test-1")
        self.assertFalse(m["has_pending_retry"])

    def test_not_ready_is_distinguished_from_a_real_failure(self):
        product = _fake_product()
        outcomes = [{
            "arm": "gumroad", "attempted": True, "ok": False, "skip_reason": None,
            "result": PublishResult(ok=False, platform="gumroad", product_id=None, url=None,
                                     error="arm not ready: unavailable", dry_run=False),
        }]
        record = build_publish_record(product, outcomes, ledger_path=self.ledger_path, state_path=self.state_path)
        self.assertEqual(record["marketplaces"][0]["publish_status"], "not_ready")

    def test_skipped_arm_is_reported_honestly(self):
        product = _fake_product()
        outcomes = [{"arm": "etsy", "attempted": False, "ok": None, "skip_reason": "unsupported product", "result": None}]
        record = build_publish_record(product, outcomes, ledger_path=self.ledger_path, state_path=self.state_path)
        m = record["marketplaces"][0]
        self.assertEqual(m["publish_status"], "not_attempted")
        self.assertEqual(m["skip_reason"], "unsupported product")
        self.assertFalse(m["has_pending_retry"])

    def test_pending_retry_is_reflected_when_one_exists(self):
        product = _fake_product()
        factory_state.enqueue_retry(
            "arm_publish:gumroad:PROD-ce-test-1", RuntimeError("timeout"), path=self.state_path,
        )
        outcomes = [{
            "arm": "gumroad", "attempted": True, "ok": False, "skip_reason": None,
            "result": PublishResult(ok=False, platform="gumroad", product_id=None, url=None,
                                     error="timeout", dry_run=False),
        }]
        record = build_publish_record(product, outcomes, ledger_path=self.ledger_path, state_path=self.state_path)
        self.assertTrue(record["marketplaces"][0]["has_pending_retry"])

    def test_revenue_status_lists_platforms_with_a_successful_publish(self):
        # revenue_status reads real channels.ledger events (never the
        # outcomes list directly) -- populate the ledger the same way
        # distributor.distribute() would have, for real, before asserting.
        from channels import ledger
        product = _fake_product()
        ok_result = PublishResult(ok=True, platform="paddle", product_id="p1", url=None, error=None, dry_run=False)
        failed_result = PublishResult(ok=False, platform="gumroad", product_id=None, url=None, error="x", dry_run=False)
        ledger.record_publish_attempt(product, ok_result, ledger_path=self.ledger_path)
        ledger.record_publish_attempt(product, failed_result, ledger_path=self.ledger_path)

        outcomes = [
            {"arm": "paddle", "attempted": True, "ok": True, "skip_reason": None, "result": ok_result},
            {"arm": "gumroad", "attempted": True, "ok": False, "skip_reason": None, "result": failed_result},
        ]
        record = build_publish_record(product, outcomes, ledger_path=self.ledger_path, state_path=self.state_path)
        self.assertEqual(record["revenue_status"]["listed_on"], ["paddle"])


class TestRunPublishPipelineDryRun(_FakeArmMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.ledger_path = _temp_path(".jsonl")
        self.state_path = _temp_path(".json")
        self.protection_state_path = _temp_path(".json")

    def tearDown(self):
        super().tearDown()
        for p in (self.ledger_path, self.state_path, self.protection_state_path):
            if os.path.exists(p):
                os.remove(p)

    def test_dry_run_never_calls_the_real_publish_only_the_shared_dry_run_result(self):
        """distributor.distribute()'s own real dry_run contract: publish()
        is still called (so shape validation happens), but every arm's
        BaseArm._dry_run_result() short-circuits before any live API call
        — proven here at the pipeline layer, not just the arm layer."""
        from channels.base_arm import BaseArm

        class DryRunOnlyArm(BaseArm):
            name = "paddle"

            def status(self):
                return ArmStatus.READY

            def publish(self, product, dry_run=True):
                assert dry_run is True, "pipeline must default to dry_run=True"
                return self._dry_run_result()

        channel_registry.register(DryRunOnlyArm())
        record = run_publish_pipeline(
            _fake_product(), ledger_path=self.ledger_path, state_path=self.state_path,
            protection_state_path=self.protection_state_path,
        )
        self.assertEqual(record["marketplaces"][0]["publish_status"], "ok")
        self.assertTrue(record["marketplaces"][0]["dry_run"])


class TestRunPublishPipelineRealMode(_FakeArmMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.ledger_path = _temp_path(".jsonl")
        self.state_path = _temp_path(".json")
        self.protection_state_path = _temp_path(".json")

    def tearDown(self):
        super().tearDown()
        for p in (self.ledger_path, self.state_path, self.protection_state_path):
            if os.path.exists(p):
                os.remove(p)

    def test_real_mode_success_reaches_the_ledger_and_revenue_status(self):
        self._register_fake_arm("paddle", status=ArmStatus.READY, publish_result=PublishResult(
            ok=True, platform="paddle", product_id="pdl_real_1", url="http://checkout",
            error=None, dry_run=False,
        ))
        record = run_publish_pipeline(
            _fake_product(), dry_run=False, ledger_path=self.ledger_path, state_path=self.state_path,
            protection_state_path=self.protection_state_path,
        )
        self.assertEqual(record["marketplaces"][0]["marketplace_id"], "pdl_real_1")
        self.assertEqual(record["revenue_status"]["listed_on"], ["paddle"])
        self.assertEqual(len(record["audit_trail"]), 1)

    def test_duplicate_publish_request_is_safely_recorded_not_corrupted(self):
        """Requirement #5: a duplicate publish request (e.g. a retried
        orchestrator cycle) must never corrupt the ledger or crash — each
        real attempt is its own honest, append-only audit_trail entry.
        Per-platform de-duplication (never creating a SECOND real Paddle
        product for the same production_id) is PaddleArm's own real
        concern, already proven in tests/test_paddle_arm.py — this proves
        the pipeline layer stays safe and auditable either way."""
        self._register_fake_arm("paddle", status=ArmStatus.READY, publish_result=PublishResult(
            ok=True, platform="paddle", product_id="pdl_dup_1", url=None, error=None, dry_run=False,
        ))
        product = _fake_product()
        run_publish_pipeline(
            product, dry_run=False, ledger_path=self.ledger_path, state_path=self.state_path,
            protection_state_path=self.protection_state_path,
        )
        second = run_publish_pipeline(
            product, dry_run=False, ledger_path=self.ledger_path, state_path=self.state_path,
            protection_state_path=self.protection_state_path,
        )
        self.assertEqual(len(second["audit_trail"]), 2)  # both real attempts honestly recorded


class TestApiTimeoutRetry(_FakeArmMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.ledger_path = _temp_path(".jsonl")
        self.state_path = _temp_path(".json")
        self.protection_state_path = _temp_path(".json")

    def tearDown(self):
        super().tearDown()
        for p in (self.ledger_path, self.state_path, self.protection_state_path):
            if os.path.exists(p):
                os.remove(p)

    def test_a_real_api_timeout_enqueues_a_retry_matching_the_records_recovery_token(self):
        """Requirement #5 (internet outage/API timeout): distributor.py's
        existing real-failure retry-enqueue is reflected honestly in the
        PublishRecord's own recovery_token/has_pending_retry fields —
        proving they're not decorative, they trace back to a real entry
        in factory_state.json's pending_retries."""
        self._register_fake_arm("paddle", status=ArmStatus.READY, publish_result=PublishResult(
            ok=False, platform="paddle", product_id=None, url=None,
            error="Paddle API request failed: timeout", dry_run=False,
        ))
        with patch.object(factory_state, "DEFAULT_STATE_PATH", Path(self.state_path)):
            record = run_publish_pipeline(
                _fake_product(), dry_run=False, ledger_path=self.ledger_path, state_path=self.state_path,
                protection_state_path=self.protection_state_path,
            )
        m = record["marketplaces"][0]
        self.assertEqual(m["publish_status"], "failed")
        self.assertTrue(m["has_pending_retry"])

        state = factory_state.load_state(self.state_path)
        tokens = [r["task"] for r in state["pending_retries"]]
        self.assertIn(m["recovery_token"], tokens)


if __name__ == "__main__":
    unittest.main()
