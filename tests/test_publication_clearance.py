"""Backlog B4: creating a paid listing needs publication clearance.

channels/publication_clearance.py accepts only a valid per-product founder
approval bound to the exact listing, or an allowed central Quality Gate
decision. gumroad_publisher.create_product() checks it before any upload,
and the Gumroad arm passes on the distributor's gate decision. No network.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from channels import gumroad_publisher as gp  # noqa: E402
from channels.publication_clearance import PublicationNotCleared, require_clearance  # noqa: E402
from test_publish_batch14 import approval_for, manifest  # noqa: E402

ALLOWED = {"allowed": True, "source_id": "x", "gate1": {"passed": True}, "gate2": {"passed": True}}


def _spec(man):
    return {"title": man["title"], "price_cents": man["price_cents"],
            "file_path": man["files"]["bundle"]["path"],
            "description": man["qa"]["listing"]["description_html"]}


class FounderApproval(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.man = manifest(self.tmp.name)
        self.approvals = [approval_for(self.man)]

    def tearDown(self):
        self.tmp.cleanup()

    def clearance(self, approvals=None):
        return {"kind": "founder_approval", "product": self.man,
                "approvals": self.approvals if approvals is None else approvals}

    def test_matching_listing_is_cleared(self):
        out = require_clearance(self.clearance(), _spec(self.man))
        self.assertEqual(out["kind"], "founder_approval")
        self.assertEqual(out["approval_id"], "GF-TEST-01")

    def test_no_approval_record_is_refused(self):
        with self.assertRaises(PublicationNotCleared):
            require_clearance(self.clearance(approvals=[]), _spec(self.man))

    def test_expired_approval_is_refused(self):
        expired = approval_for(self.man, expires_at="2020-01-01T00:00:00+00:00")
        with self.assertRaises(PublicationNotCleared):
            require_clearance(self.clearance(approvals=[expired]), _spec(self.man))

    def test_listing_that_differs_from_the_approval_is_refused(self):
        for field, value in (("title", "Another Tool"), ("price_cents", 9900),
                             ("description", "<p>changed</p>")):
            spec = dict(_spec(self.man), **{field: value})
            with self.subTest(field=field), self.assertRaises(PublicationNotCleared):
                require_clearance(self.clearance(), spec)

    def test_a_different_file_is_refused(self):
        other = Path(self.tmp.name) / "other.zip"
        other.write_bytes(b"not the approved bundle")
        spec = dict(_spec(self.man), file_path=str(other))
        with self.assertRaises(PublicationNotCleared):
            require_clearance(self.clearance(), spec)


class QualityGate(unittest.TestCase):
    def test_allowed_decision_is_cleared(self):
        self.assertEqual(require_clearance({"kind": "quality_gate", "decision": ALLOWED}, {})["kind"],
                         "quality_gate")

    def test_denied_or_partial_decisions_are_refused(self):
        for decision in (None, {}, dict(ALLOWED, allowed=False),
                         dict(ALLOWED, gate1={"passed": False}), dict(ALLOWED, gate2={})):
            with self.subTest(decision=decision), self.assertRaises(PublicationNotCleared):
                require_clearance({"kind": "quality_gate", "decision": decision}, {})

    def test_missing_or_unknown_clearance_is_refused(self):
        for clearance in (None, "yes", {"kind": "override"}, {}):
            with self.subTest(clearance=clearance), self.assertRaises(PublicationNotCleared):
                require_clearance(clearance, {})


class CreateProductRefusesBeforeUpload(unittest.TestCase):
    def test_no_clearance_stops_before_any_upload_or_network(self):
        with mock.patch.object(gp, "_require_write_authorization"), \
                mock.patch.object(gp, "_upload_file") as upload, \
                mock.patch.object(gp, "_find_duplicate_listing") as dup:
            with self.assertRaises(PublicationNotCleared):
                gp.create_product("tok", {"title": "T", "price_cents": 900, "file_path": __file__})
        upload.assert_not_called()
        dup.assert_not_called()


class GumroadArmPassesTheGateDecision(unittest.TestCase):
    def _product(self, **extra):
        return SimpleNamespace(title="T", description="d", price_usd=9.0, file_path=__file__,
                               product_type="pdf", source_id="s", **extra)

    def _publish(self, product):
        from channels import gumroad_arm
        arm = gumroad_arm.GumroadArm()
        with mock.patch.object(arm, "supports", return_value=True), \
                mock.patch.object(gumroad_arm.gumroad_publisher, "load_token", return_value="tok"), \
                mock.patch.object(gumroad_arm.gumroad_publisher, "create_product",
                                  return_value={"id": "p", "short_url": "u"}) as create:
            result = arm.publish(product, dry_run=False)
        return result, create

    def test_arm_forwards_the_decision_as_clearance(self):
        _, create = self._publish(self._product(quality_gate_decision=ALLOWED))
        clearance = create.call_args.kwargs["publication_clearance"]
        self.assertEqual(clearance, {"kind": "quality_gate", "decision": ALLOWED})
        require_clearance(clearance, {})

    def test_without_a_decision_the_clearance_is_refused(self):
        _, create = self._publish(self._product())
        with self.assertRaises(PublicationNotCleared):
            require_clearance(create.call_args.kwargs["publication_clearance"], {})


@mock.patch.dict("os.environ", {"FACTORY_LIVE_PUBLISH": "true"})
class DistributorAttachesTheGateDecision(unittest.TestCase):
    def test_allowed_gate_decision_reaches_the_arm(self):
        import os
        import distributor
        from channels import registry
        from channels.base_arm import PublishResult
        from test_distributor import _fake_product, _temp_path
        saved = registry.all_arms()
        registry.clear()
        ledger_path, state_path = _temp_path(".jsonl"), _temp_path(".json")
        try:
            arm = mock.MagicMock()
            arm.name = "gumroad"
            arm.supports.return_value = True
            arm.publish.return_value = PublishResult(ok=True, platform="gumroad", product_id="p",
                                                     url="u", error=None, dry_run=False)
            registry.register(arm)
            distributor.distribute(_fake_product(), dry_run=False, ledger_path=ledger_path,
                                   protection_state_path=state_path,
                                   quality_gate=lambda *a, **k: dict(ALLOWED))
            arm.publish.assert_called_once()
            sent = arm.publish.call_args.args[0]
            self.assertEqual(sent.quality_gate_decision["allowed"], True)
        finally:
            registry.clear()
            for a in saved:
                registry.register(a)
            for p in (ledger_path, state_path):
                if os.path.exists(p):
                    os.remove(p)


if __name__ == "__main__":
    unittest.main()
