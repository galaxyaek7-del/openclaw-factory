"""Tests for integration_registry.py (EOS Phase 2, 2026-07-19): the
real, adapter-based extension-point catalog for future integrations.

Runs with stdlib unittest.

    python -m unittest tests.test_integration_registry -v
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import integration_registry as ir


class TestNewVendorEntries(unittest.TestCase):
    def test_credential_present_reports_configured_true(self):
        catalog = [{"name": "TestVendor", "category": "test", "credential_env_var": "TEST_VENDOR_KEY"}]
        with patch.dict(os.environ, {"TEST_VENDOR_KEY": "some-value"}):
            entries = ir._new_vendor_entries(catalog)
        self.assertTrue(entries[0]["configured"])

    def test_credential_missing_reports_configured_false_never_fabricated(self):
        catalog = [{"name": "TestVendor", "category": "test", "credential_env_var": "TEST_VENDOR_KEY_NOT_SET"}]
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEST_VENDOR_KEY_NOT_SET", None)
            entries = ir._new_vendor_entries(catalog)
        self.assertFalse(entries[0]["configured"])

    def test_no_credential_concept_reports_none_not_a_guess(self):
        catalog = [{"name": "LocalTool", "category": "test", "credential_env_var": None}]
        entries = ir._new_vendor_entries(catalog)
        self.assertIsNone(entries[0]["configured"])


class TestAiProviderEntries(unittest.TestCase):
    def test_references_ai_capability_registry_not_a_second_source(self):
        entries = ir._ai_provider_entries()
        self.assertTrue(all(e["source"] == "ai_capability.registry" for e in entries))
        self.assertGreater(len(entries), 0)


class TestCommerceChannelEntries(unittest.TestCase):
    """Explicitly registers a real arm rather than relying on
    `import distributor`'s module-load-time side effect: another test
    file's tearDown() (tests/test_commercial_execution.py's
    _FakeArmMixin) calls channels.registry.clear() without restoring the
    real arms afterward, so channels.registry.all_arms() is NOT
    reliably populated this way across a full-suite run regardless of
    file order -- confirmed live (found via this exact test failing only
    in `python -m unittest discover`, never standalone). Registering a
    real arm directly makes this test correct regardless of what ran
    before it, instead of depending on shared global registry state."""

    def setUp(self):
        from channels import registry as channel_registry
        from channels.paddle_arm import PaddleArm
        self._saved_arms = channel_registry.all_arms()
        channel_registry.register(PaddleArm())

    def tearDown(self):
        from channels import registry as channel_registry
        channel_registry.clear()
        for arm in self._saved_arms:
            channel_registry.register(arm)

    def test_references_channels_registry_not_a_second_source(self):
        entries = ir._commerce_channel_entries()
        self.assertTrue(all(e["source"] == "channels.registry" for e in entries))
        names = {e["name"] for e in entries}
        self.assertIn("paddle", names)


class TestListIntegrations(unittest.TestCase):
    """Same real-arm-registration safety as TestCommerceChannelEntries
    above -- see its docstring for why channels.registry.all_arms()
    can't be relied on to already be populated in a full-suite run."""

    def setUp(self):
        from channels import registry as channel_registry
        from channels.paddle_arm import PaddleArm
        self._saved_arms = channel_registry.all_arms()
        channel_registry.register(PaddleArm())

    def tearDown(self):
        from channels import registry as channel_registry
        channel_registry.clear()
        for arm in self._saved_arms:
            channel_registry.register(arm)

    def test_real_call_never_throws_and_covers_every_named_category(self):
        entries = ir.list_integrations()
        categories = {e["category"] for e in entries}
        for expected in ("ai_provider", "commerce_channel", "communication", "data", "infrastructure"):
            self.assertIn(expected, categories)

    def test_no_duplicate_vendor_names_across_sources(self):
        entries = ir.list_integrations()
        names = [e["name"] for e in entries]
        self.assertEqual(len(names), len(set(names)), "a vendor must never appear twice from two different sources")


if __name__ == "__main__":
    unittest.main()
