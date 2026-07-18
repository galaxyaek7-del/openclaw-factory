"""Manifest-driven family adapter (Universal Production Engine Roadmap
Step 3, 2026-07-18) — the Product Definition Registry's generic
dispatcher. Runs the exact same 4-stage pipeline
automation_systems.py's adapter established in Roadmap Step 2 (Content
Generation -> Asset Generation -> Packaging -> Dossier Bundle), but every
registry lookup name and default content skeleton comes from a
ProductManifest instead of being hardcoded per family.

A new family that reuses existing registry implementations needs ONLY a
ProductManifest and one register_manifest_driven_family() call — zero
new engine code, zero new adapter file. A family that genuinely needs a
different generator/builder/packager still just needs a new
self-registering module under content_generation/asset_generation/
product_packaging — this file itself never changes either way.
"""

import content_generation.generators  # noqa: F401 — self-registers
import asset_generation.builders  # noqa: F401 — self-registers
import product_packaging  # noqa: F401 — self-registers
from content_generation import registry as content_registry
from asset_generation import registry as asset_registry
from product_packaging import registry as packaging_registry
from dossier_bundle.build_bundle import build_product_dossier_bundle

from . import registry as family_registry
from . import manifest as manifest_registry
from .spec import components_to_sections


class ManifestDrivenFamily:
    """The Product Definition Registry's one generic adapter — behavior
    is entirely a function of the ProductManifest it's constructed with,
    never a hardcoded per-family branch in this class."""

    def __init__(self, manifest):
        self.manifest = manifest
        self.name = manifest.product_id

    def generate(self, spec):
        manifest = self.manifest
        title = spec.get("title") or f"Untitled {manifest.category}"
        topic = spec.get("topic") or spec.get("niche") or ""
        production_id = spec.get("production_id")

        # Stage 1: Content Generation — via content_generation.registry,
        # looked up by the manifest's declared name, never hardcoded.
        # A component already carrying real content (verbatim) is never
        # regenerated; only plain-string section titles go through Groq.
        sections = components_to_sections(spec.get("components")) or list(manifest.default_sections)
        verbatim = [s for s in sections if isinstance(s, dict)]
        to_generate = [s for s in sections if not isinstance(s, dict)]

        generated_components = []
        if to_generate:
            content_gen = content_registry.get(manifest.content_generator)
            content_result = content_gen.generate({
                "title": title, "topic": topic, "section_titles": to_generate,
                "production_id": production_id,
            })
            generated_components = content_result["components"]

        all_components = verbatim + generated_components

        # Stage 2: Asset Generation — via asset_generation.registry,
        # looked up by the manifest's declared name. Every component here
        # already carries real content, so the builder's own internal
        # components_to_sections() pass treats all of them as verbatim —
        # zero duplicate Groq calls for the same content.
        asset_spec = dict(spec)
        asset_spec["components"] = all_components
        price_hint = manifest.pricing_strategy.get("price_hint")
        if asset_spec.get("price_hint") is None and price_hint is not None:
            asset_spec["price_hint"] = price_hint
        asset_builder = asset_registry.get(manifest.asset_builder)
        build_result = asset_builder.build(asset_spec)

        # Stage 3: Packaging — via product_packaging.registry, looked up
        # by the manifest's declared name.
        packager = packaging_registry.get(manifest.packager)
        package_result = packager.package(asset_spec, build_result)

        # Stage 4: Dossier Bundle — mandatory per-product artifacts,
        # crediting the manifest-declared registry names in the real
        # build manifest. family_config's changelog_path/state_path are
        # test-isolation overrides only (same convention every family
        # adapter already uses) — omitted in every real run.
        family_config = spec.get("family_config") or {}
        dossier = build_product_dossier_bundle(
            asset_spec, build_result,
            changelog_path=family_config.get("changelog_path"),
            state_path=family_config.get("state_path"),
            content_generator=manifest.content_generator if to_generate else None,
            asset_builder=asset_builder.name,
            packager=packager.name,
        )

        return {
            **build_result,
            "components": all_components,
            "package": package_result,
            "dossier_bundle": dossier,
        }


def register_manifest_driven_family(manifest):
    """The one call a config-only family needs: registers the manifest
    itself (Product Definition Registry) AND a ManifestDrivenFamily
    instance under the same name in product_families.registry (so
    orchestrator/engines/production.py's existing dispatch needs zero
    changes to find it)."""
    manifest_registry.register(manifest)
    family_registry.register(ManifestDrivenFamily(manifest))
