"""Tests for product_families/manifest.py + generic_adapter.py
(Universal Production Engine Roadmap Step 3, 2026-07-18): the Product
Definition Registry.

The `TestConfigOnlyFamilyAddition` class is the rigorous proof for
requirement #4 ("adding a new product family requires only
configuration, no engine changes"): it registers a brand-new demo
family using ONLY a ProductManifest + one register_manifest_driven_family()
call — no new adapter class, no new registry module, no orchestrator
change — and proves it generates a real product through the exact same
pipeline a hand-written family adapter uses.

    python -m unittest tests.test_product_manifest -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import book_generator as bg
import factory_state
from product_families.manifest import ProductManifest, compatible_arms
from product_families import manifest as manifest_registry
from product_families.generic_adapter import register_manifest_driven_family
from product_families import registry as family_registry
from product_families.spec import build_product_specification
from channels import registry as channel_registry
from channels.paddle_arm import PaddleArm
from channels.gumroad_arm import GumroadArm


def _fake_generated(title, topic, titles):
    return [{"title": t, "content": f"real content for {t}"} for t in titles]


class TestProductManifest(unittest.TestCase):
    def test_to_dict_carries_every_required_field(self):
        m = ProductManifest(
            product_id="x", family="x", category="c",
            content_generator="groq_techdoc", asset_builder="techdoc_package", packager="single_file",
        )
        d = m.to_dict()
        for key in ("product_id", "family", "category", "content_generator", "asset_builder",
                    "packager", "default_sections", "qa_profile", "publishing_profile",
                    "pricing_strategy", "supported_marketplaces", "recovery_policy", "version"):
            self.assertIn(key, d)

    def test_defaults_are_honestly_empty_not_guessed(self):
        m = ProductManifest(
            product_id="x", family="x", category="c",
            content_generator="groq_techdoc", asset_builder="techdoc_package", packager="single_file",
        )
        self.assertEqual(m.default_sections, [])
        self.assertEqual(m.qa_profile, {})
        self.assertEqual(m.supported_marketplaces, [])
        self.assertEqual(m.version, "1.0")


class TestManifestRegistry(unittest.TestCase):
    def setUp(self):
        self._saved = manifest_registry.all_manifests()

    def tearDown(self):
        manifest_registry.clear()
        for m in self._saved:
            manifest_registry.register(m)

    def test_real_manifests_are_registered_for_converted_families(self):
        import product_families  # noqa: F401 — self-registers
        names = {m.product_id for m in manifest_registry.all_manifests()}
        self.assertEqual(
            names, {"automation_systems", "professional_templates", "digital_toolkits"},
        )

    def test_unregistered_manifest_returns_none_not_a_guess(self):
        manifest_registry.clear()
        self.assertIsNone(manifest_registry.get("automation_systems"))

    def test_register_overrides_same_id_deliberately(self):
        m1 = ProductManifest(product_id="x", family="x", category="c",
                              content_generator="a", asset_builder="b", packager="c")
        m2 = ProductManifest(product_id="x", family="x", category="c2",
                              content_generator="a", asset_builder="b", packager="c")
        manifest_registry.register(m1)
        manifest_registry.register(m2)
        self.assertEqual(manifest_registry.get("x").category, "c2")


class TestCompatibleArms(unittest.TestCase):
    def setUp(self):
        channel_registry.clear()
        channel_registry.register(PaddleArm())
        channel_registry.register(GumroadArm())

    def test_intersects_declared_marketplaces_with_actually_registered_arms(self):
        m = ProductManifest(
            product_id="x", family="x", category="c",
            content_generator="a", asset_builder="b", packager="c",
            supported_marketplaces=["paddle", "gumroad", "shopify"],
        )
        # "shopify" is declared but has no registered arm today (future,
        # not built) — a real, computed answer excludes it honestly.
        self.assertEqual(sorted(compatible_arms(m)), ["gumroad", "paddle"])

    def test_empty_declaration_is_honestly_empty(self):
        m = ProductManifest(product_id="x", family="x", category="c",
                             content_generator="a", asset_builder="b", packager="c")
        self.assertEqual(compatible_arms(m), [])


class _CleanupMixin:
    def setUp(self):
        self._created_paths = []
        self._family_saved = family_registry.all_families()
        self._manifest_saved = manifest_registry.all_manifests()

    def tearDown(self):
        family_registry.clear()
        for a in self._family_saved:
            family_registry.register(a)
        manifest_registry.clear()
        for m in self._manifest_saved:
            manifest_registry.register(m)
        for p in self._created_paths:
            if p and os.path.exists(p):
                os.remove(p)

    def _track(self, result):
        if result.get("path"):
            self._created_paths.append(result["path"])
        if result.get("cover") and result["cover"].get("path"):
            self._created_paths.append(result["cover"]["path"])
        return result


class TestConfigOnlyFamilyAddition(_CleanupMixin, unittest.TestCase):
    """Requirement #4's rigorous proof: a brand-new family, added with
    ZERO new Python beyond a ProductManifest object and one registration
    call — no adapter class, no new module, no orchestrator/engine
    change — dispatches and generates identically to a hand-written
    family adapter."""

    def test_a_demo_family_needs_only_a_manifest_to_work(self):
        demo_manifest = ProductManifest(
            product_id="demo_config_only_family",
            family="demo_config_only_family",
            category="proof_of_concept",
            content_generator="groq_techdoc",   # reuses the EXISTING registered generator
            asset_builder="techdoc_package",     # reuses the EXISTING registered builder
            packager="single_file",              # reuses the EXISTING registered packager
            default_sections=["Intro", "Details"],
            pricing_strategy={"price_hint": 149.0},
            supported_marketplaces=["paddle", "gumroad"],
        )
        register_manifest_driven_family(demo_manifest)  # <-- the ONE call

        self.assertIn("demo_config_only_family", {a.name for a in family_registry.all_families()})
        self.assertIs(manifest_registry.get("demo_config_only_family"), demo_manifest)

        tmp_changelog = tempfile.mktemp(suffix=".jsonl")
        tmp_state = tempfile.mktemp(suffix=".json")
        self.addCleanup(lambda: os.path.exists(tmp_changelog) and os.remove(tmp_changelog))
        self.addCleanup(lambda: os.path.exists(tmp_state) and os.remove(tmp_state))

        with patch.object(bg, "ai_generate_techdoc_content", side_effect=_fake_generated), \
             patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch.object(bg, "_record_rejected_niche"), \
             patch.object(bg.INSPECTORS, "_log_quarantine"):
            spec = build_product_specification(
                niche="test config only demo niche", product_family="demo_config_only_family",
                production_id="PROD-demo-config-only",
                family_config={
                    "output": "test_demo_config_only_family.pdf",
                    "changelog_path": tmp_changelog, "state_path": tmp_state,
                },
            )
            result = self._track(family_registry.get("demo_config_only_family").generate(spec))

        self.assertTrue(result["success"])
        self.assertEqual(result["price"], 149.0)  # from the manifest's pricing_strategy, never hardcoded here
        self.assertEqual(len(result["components"]), 2)  # from the manifest's default_sections
        self.assertEqual(result["package"]["method"], "single_file")
        self.assertEqual(result["dossier_bundle"]["build_manifest"]["content_generator"], "groq_techdoc")
        self.assertEqual(result["dossier_bundle"]["production_id"], "PROD-demo-config-only")


class TestManifestDrivenRecovery(_CleanupMixin, unittest.TestCase):
    """Requirement #7: automatic recovery must hold for ANY manifest-
    driven family, not just automation_systems (already proven in
    tests/test_automation_systems_e2e.py) — this is a property of
    ManifestDrivenFamily/content_generation itself, exercised here
    against a brand-new demo manifest to prove it's structural, not
    incidental to one hand-tuned family."""

    def test_a_content_generation_interruption_enqueues_a_real_traceable_retry(self):
        demo_manifest = ProductManifest(
            product_id="demo_recovery_family", family="demo_recovery_family", category="proof_of_concept",
            content_generator="groq_techdoc", asset_builder="techdoc_package", packager="single_file",
            default_sections=["Intro"],
        )
        register_manifest_driven_family(demo_manifest)

        tmp_changelog = tempfile.mktemp(suffix=".jsonl")
        tmp_state = tempfile.mktemp(suffix=".json")
        self.addCleanup(lambda: os.path.exists(tmp_changelog) and os.remove(tmp_changelog))
        self.addCleanup(lambda: os.path.exists(tmp_state) and os.remove(tmp_state))

        # content_generation/generators/groq_generator.py's enqueue_retry()
        # call has no per-call path override (unlike dossier_bundle's own
        # state_path param) — it always resolves factory_state's module-
        # level DEFAULT_STATE_PATH. Patching it here is the only way to
        # keep this failure-path test from writing a real retry into the
        # real data/factory_state.json (found live, 2026-07-18: an earlier
        # version of this test did exactly that).
        with patch.object(bg, "ai_generate_techdoc_content", side_effect=RuntimeError("groq unreachable")), \
             patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch.object(bg, "_record_rejected_niche"), \
             patch.object(bg.INSPECTORS, "_log_quarantine"), \
             patch.object(factory_state, "DEFAULT_STATE_PATH", Path(tmp_state)):
            spec = build_product_specification(
                niche="test recovery demo niche", product_family="demo_recovery_family",
                production_id="PROD-demo-recovery",
                family_config={
                    "output": "test_demo_recovery_family.pdf",
                    "changelog_path": tmp_changelog, "state_path": tmp_state,
                },
            )
            result = self._track(family_registry.get("demo_recovery_family").generate(spec))

        self.assertTrue(result["success"], "a real interruption must degrade to honest fallback content, never crash")

        state = factory_state.load_state(tmp_state)
        matching = [
            r for r in state["pending_retries"]
            if isinstance(r.get("context"), dict) and r["context"].get("production_id") == "PROD-demo-recovery"
        ]
        self.assertTrue(matching, "any manifest-driven family's Content Generation failure must enqueue a real, traceable retry")


if __name__ == "__main__":
    unittest.main()
