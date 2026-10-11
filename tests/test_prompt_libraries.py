"""Tests for product_families/families/prompt_libraries.py (Cycle 80,
Priority B special task).

Context: this module is one of the ~168+ real files found sitting
uncommitted in the working tree since 2026-09-21 (see
docs/FACTORY_AUTOMATION_AUDIT.md section I / docs/CYCLE_80_FINAL_REPORT.md
section C). It is NOT imported by product_families/families/__init__.py
(confirmed: production_factory.dossier._product_type_capability()
reports "prompt_libraries: NOT YET BUILT" because nothing ever imports
it) -- this cycle tests the file as the real, standalone unit it is,
without wiring it into the live registry (that integration decision is
explicitly out of this task's scope).

Isolation discipline (load-bearing, not cosmetic): importing this
module registers it into the SHARED, module-level
product_families.registry / product_families.manifest registries as a
side effect. tests/test_product_families.py's own
TestRegistry.test_phase_a_families_are_all_registered asserts the
registry contains EXACTLY the 5 real families
{"kdp_books", "professional_templates", "digital_toolkits",
"knowledge_bases", "automation_systems"} -- both test files fall in the
same CI group (test_[i-p]*.py) and run in the same Python process via
unittest discovery, so a leaked 6th registration here would break that
tracked, existing assertion. Every test below saves the real registry
state before importing/registering prompt_libraries and restores it
exactly in tearDown, mirroring tests/test_product_families.py::
TestRegistry's own established save/clear/restore convention.

    python -m unittest tests.test_prompt_libraries -v
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import book_generator as bg
from product_families import registry
from product_families import manifest as manifest_registry


class _IsolatedRegistryMixin:
    """Save/restore both registries around each test so this file's
    import-time registration of prompt_libraries never leaks into any
    other test file's assertions, regardless of discovery/run order."""

    def setUp(self):
        self._saved_families = registry.all_families()
        self._saved_manifests = manifest_registry.all_manifests()
        # Importing here (not at module top-level) keeps the
        # registration side effect scoped to tests that actually need
        # it -- the import is cached in sys.modules after the first
        # test, which is fine: re-importing re-registers idempotently
        # (register() is a deliberate override, per manifest.py's own
        # docstring), and tearDown always restores the pre-test state
        # regardless of caching.
        from product_families.families import prompt_libraries
        self.prompt_libraries = prompt_libraries
        # The module's top-level register_manifest_driven_family() call
        # only ever runs ONCE per process (Python caches the import) --
        # a prior test's tearDown may have already wiped that one real
        # registration out of the shared registry. Re-register
        # explicitly and idempotently every time (register() is a
        # deliberate override per manifest.py's own docstring), so each
        # test gets a real, present registration regardless of import
        # order/caching.
        prompt_libraries.register_manifest_driven_family(prompt_libraries.MANIFEST)

    def tearDown(self):
        registry.clear()
        manifest_registry.clear()
        for adapter in self._saved_families:
            registry.register(adapter)
        for manifest in self._saved_manifests:
            manifest_registry.register(manifest)


class TestPromptLibrariesManifestShape(_IsolatedRegistryMixin, unittest.TestCase):
    """The manifest itself -- no generation, no registry isolation risk
    beyond the import, but still wrapped for consistency."""

    def test_manifest_fields_match_the_real_file(self):
        m = self.prompt_libraries.MANIFEST
        self.assertEqual(m.product_id, "prompt_libraries")
        self.assertEqual(m.family, "prompt_libraries")
        self.assertEqual(m.content_generator, "groq_techdoc")
        self.assertEqual(m.asset_builder, "techdoc_package")
        self.assertEqual(m.packager, "single_file")
        self.assertEqual(m.pricing_strategy.get("price_hint"), 29.0)
        self.assertEqual(m.supported_marketplaces, ["gumroad", "etsy"])

    def test_default_sections_match_the_real_file(self):
        self.assertEqual(
            self.prompt_libraries.DEFAULT_PROMPT_SECTIONS,
            [
                "Prompt Library Overview", "Prompt Categories & Use Cases",
                "Prompt Engineering Guide", "Customization & Variables",
                "Best Practices & Tips", "Updates & Expansion",
            ],
        )

    def test_registering_is_present_and_idempotent_never_duplicated(self):
        # setUp already registered it once (real, not a test shortcut --
        # the module's own top-level call only ever fires once per
        # process, so this file re-registers explicitly every setUp).
        # Registering again here must not produce a second entry:
        # register() is a deliberate override of the same product_id,
        # not an append, per manifest.py's own docstring.
        count_families = len(registry.all_families())
        count_manifests = len(manifest_registry.all_manifests())
        self.prompt_libraries.register_manifest_driven_family(self.prompt_libraries.MANIFEST)
        self.assertEqual(len(registry.all_families()), count_families)
        self.assertEqual(len(manifest_registry.all_manifests()), count_manifests)
        self.assertIsNotNone(registry.get("prompt_libraries"))
        self.assertIsNotNone(manifest_registry.get("prompt_libraries"))

    def test_compatible_arms_computes_the_real_intersection_not_the_manifest_list(self):
        """manifest.py's own compatible_arms() docstring: 'the REAL
        computed answer... not the manifest's own possibly-stale list'
        -- this is the one meaningfully different edge case none of the
        sibling families' tests in test_product_families.py exercise
        for this specific manifest's declared marketplaces."""
        from product_families.manifest import compatible_arms
        from channels import registry as channel_registry
        registered_arm_names = {arm.name for arm in channel_registry.all_arms()}
        result = compatible_arms(self.prompt_libraries.MANIFEST)
        # Every returned name really is both in the manifest's own list
        # AND actually registered right now -- never just echoed back.
        for name in result:
            self.assertIn(name, self.prompt_libraries.MANIFEST.supported_marketplaces)
            self.assertIn(name, registered_arm_names)
        # Nothing claimed-but-unregistered silently passes through.
        for name in self.prompt_libraries.MANIFEST.supported_marketplaces:
            if name not in registered_arm_names:
                self.assertNotIn(name, result)


class TestPromptLibrariesAdapter(_IsolatedRegistryMixin, unittest.TestCase):
    """Mirrors tests/test_product_families.py::TestAutomationSystemsAdapter's
    established convention exactly (same manifest shape: groq_techdoc /
    techdoc_package / single_file) -- same mocks, same isolation."""

    def setUp(self):
        super().setUp()
        self._created_paths = []

    def tearDown(self):
        for p in self._created_paths:
            try:
                os.remove(p)
            except OSError:
                pass
        super().tearDown()

    def _track(self, result):
        if result.get("path"):
            self._created_paths.append(result["path"])
        return result

    def _isolated_path(self, suffix):
        import tempfile
        path = tempfile.mktemp(suffix=suffix)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_generates_a_real_pdf_via_the_upe_registries(self):
        from product_families.spec import build_product_specification

        def _fake_generated(title, topic, titles):
            return [{"title": t, "content": f"real content for {t}"} for t in titles]

        with patch.object(bg, "ai_generate_techdoc_content", side_effect=_fake_generated), \
             patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch.object(bg, "_record_rejected_niche"), \
             patch.object(bg.INSPECTORS, "_log_quarantine"):
            spec = build_product_specification(
                niche="test prompt library niche",
                product_family="prompt_libraries",
                production_id="PROD-prompt-libraries-test-1",
                family_config={
                    "output": "test_family_prompt_libraries.pdf",
                    "changelog_path": self._isolated_path(".jsonl"),
                    "state_path": self._isolated_path(".json"),
                },
            )
            result = self._track(registry.get("prompt_libraries").generate(spec))

        self.assertTrue(result["success"])
        self.assertEqual(result["product_type"], "techdoc")
        self.assertEqual(len(result["components"]), 6)  # DEFAULT_PROMPT_SECTIONS
        self.assertEqual(result["package"], {
            "artifact_path": result["path"], "method": "single_file", "file_count": 1,
        })
        self.assertEqual(result["dossier_bundle"]["production_id"], "PROD-prompt-libraries-test-1")
        self.assertEqual(result["dossier_bundle"]["build_manifest"]["content_generator"], "groq_techdoc")
        self.assertEqual(result["dossier_bundle"]["build_manifest"]["asset_builder"], "techdoc_package")
        self.assertEqual(result["dossier_bundle"]["build_manifest"]["packager"], "single_file")
        self.assertIsNotNone(result["dossier_bundle"]["qa_report"])

    def test_verbatim_components_are_never_regenerated(self):
        from product_families.spec import build_product_specification

        with patch.object(bg, "ai_generate_techdoc_content") as mocked, \
             patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch.object(bg, "_record_rejected_niche"), \
             patch.object(bg.INSPECTORS, "_log_quarantine"):
            spec = build_product_specification(
                niche="test prompt library verbatim niche",
                product_family="prompt_libraries",
                components=[{"title": "Custom Prompt Set", "content": "Already-written real content."}],
                family_config={
                    "output": "test_family_prompt_libraries_verbatim.pdf",
                    "changelog_path": self._isolated_path(".jsonl"),
                    "state_path": self._isolated_path(".json"),
                },
            )
            result = self._track(registry.get("prompt_libraries").generate(spec))
        mocked.assert_not_called()
        self.assertEqual(
            result["components"],
            [{"title": "Custom Prompt Set", "content": "Already-written real content."}],
        )

    def test_price_hint_from_manifest_is_applied_when_spec_omits_it(self):
        """Edge case none of the sibling families' tests in
        test_product_families.py exercise: generic_adapter.py's
        ManifestDrivenFamily.generate() explicitly copies
        manifest.pricing_strategy['price_hint'] into asset_spec only
        when the spec itself didn't already set one. Verified here by
        patching the asset builder actually invoked (techdoc_package)
        and inspecting the spec it was called with -- not inferring
        this from the final PDF, which doesn't surface price_hint."""
        from asset_generation import registry as asset_registry
        from product_families.spec import build_product_specification

        real_builder = asset_registry.get("techdoc_package")
        original_build = real_builder.build  # captured BEFORE patching -- the patched
        captured = {}                         # attribute would otherwise recurse into itself

        def _spy_build(spec):
            captured["price_hint"] = spec.get("price_hint")
            return original_build(spec)

        with patch.object(bg, "ai_generate_techdoc_content", side_effect=lambda title, topic, titles: [
                {"title": t, "content": f"real content for {t}"} for t in titles]), \
             patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch.object(bg, "_record_rejected_niche"), \
             patch.object(bg.INSPECTORS, "_log_quarantine"), \
             patch.object(real_builder, "build", side_effect=_spy_build):
            spec = build_product_specification(
                niche="test prompt library price hint niche",
                product_family="prompt_libraries",
                family_config={
                    "output": "test_family_prompt_libraries_price.pdf",
                    "changelog_path": self._isolated_path(".jsonl"),
                    "state_path": self._isolated_path(".json"),
                },
            )
            result = self._track(registry.get("prompt_libraries").generate(spec))

        self.assertTrue(result["success"])
        self.assertEqual(captured.get("price_hint"), 29.0)


if __name__ == "__main__":
    unittest.main()
