"""automation_systems family adapter (Universal Production Engine
Roadmap Step 2, 2026-07-18) — the reference implementation for every
future family. Unlike the 4 Phase A adapters (kdp_books/
professional_templates/digital_toolkits/knowledge_bases, left unchanged
per Roadmap Step 1's "zero behavior change" scope, which still call
book_generator.py directly), this adapter explicitly runs the full UPE
pipeline through the new registries — Content Generation, then Asset
Generation, then Packaging, then the Dossier Bundle — so a future family
needs configuration (a components list + a family_config dict) rather
than a rewrite of this method.

Real, distinct content shape: a business-automation-system product's own
section skeleton (not a renamed copy of professional_templates/
digital_toolkits, which share this same underlying PDF engine but with
the generic techdoc skeleton).
"""

import content_generation.generators  # noqa: F401 — self-registers
import asset_generation.builders  # noqa: F401 — self-registers
import product_packaging  # noqa: F401 — self-registers
from content_generation import registry as content_registry
from asset_generation import registry as asset_registry
from product_packaging import registry as packaging_registry
from dossier_bundle.build_bundle import build_product_dossier_bundle

from .. import registry
from ..spec import components_to_sections

DEFAULT_AUTOMATION_SECTIONS = [
    "System Overview",
    "Workflow Architecture",
    "Setup & Integration Guide",
    "Automation Triggers & Logic",
    "Maintenance & Troubleshooting",
    "ROI & Time Savings",
]


class AutomationSystemsFamily:
    name = "automation_systems"

    def generate(self, spec):
        title = spec.get("title") or "Untitled Automation System"
        topic = spec.get("topic") or spec.get("niche") or ""
        production_id = spec.get("production_id")

        # Stage 1: Content Generation — via content_generation.registry,
        # never book_generator directly. A component already carrying
        # real content (verbatim, human/Claude-authored) is never
        # regenerated; only plain-string section titles go through Groq.
        sections = components_to_sections(spec.get("components")) or list(DEFAULT_AUTOMATION_SECTIONS)
        verbatim = [s for s in sections if isinstance(s, dict)]
        to_generate = [s for s in sections if not isinstance(s, dict)]

        generated_components = []
        if to_generate:
            content_gen = content_registry.get("groq_techdoc")
            content_result = content_gen.generate({
                "title": title, "topic": topic, "section_titles": to_generate,
                "production_id": production_id,
            })
            generated_components = content_result["components"]

        all_components = verbatim + generated_components

        # Stage 2: Asset Generation — via asset_generation.registry. Every
        # component here already carries real content, so the builder's
        # own internal components_to_sections() pass treats all of them
        # as verbatim — zero duplicate Groq calls for the same content.
        asset_spec = dict(spec)
        asset_spec["components"] = all_components
        asset_builder = asset_registry.get("techdoc_package")
        build_result = asset_builder.build(asset_spec)

        # Stage 3: Packaging — via product_packaging.registry. A single
        # PDF today (single_file passthrough); a future multi-file
        # revision of this family registers a real bundling packager
        # without this method changing.
        packager = packaging_registry.get("single_file")
        package_result = packager.package(asset_spec, build_result)

        # Stage 4: Dossier Bundle — mandatory per-product artifacts
        # (documentation/metadata/marketing/support/changelog/version/
        # build manifest/QA report/recovery metadata), via dossier_bundle.
        # Real registry names are passed through for an honest, accurate
        # build manifest. family_config's changelog_path/state_path are
        # test-isolation overrides only (same convention as
        # family_config["output"] above) — omitted in every real run,
        # which targets the real data/product_changelog.jsonl and
        # data/factory_state.json.
        family_config = spec.get("family_config") or {}
        dossier = build_product_dossier_bundle(
            asset_spec, build_result,
            changelog_path=family_config.get("changelog_path"),
            state_path=family_config.get("state_path"),
            content_generator="groq_techdoc" if to_generate else None,
            asset_builder=asset_builder.name,
            packager=packager.name,
        )

        return {
            **build_result,
            "components": all_components,
            "package": package_result,
            "dossier_bundle": dossier,
        }


registry.register(AutomationSystemsFamily())
