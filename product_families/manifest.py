"""OpenClaw Factory — Product Manifest (Universal Production Engine
Roadmap Step 3, 2026-07-18): the Product Definition Registry.

A ProductManifest is the "configuration, not code" answer for a product
family that reuses existing registry implementations (content
generator, asset builder, packager) — registering one replaces writing
a bespoke `product_families/families/<name>.py` adapter entirely (see
`generic_adapter.py`'s `register_manifest_driven_family()`).

Honesty note on which fields are genuinely live vs. descriptive: this
factory has exactly one real Content Generator/Asset Generator/Packager
implementation per registered name today, and exactly one real QA engine
(`inspectors.py`) and one real recovery engine (`factory_state.py`) —
both already shared, generic, and unconditionally applied to every
family. So:
  - `content_generator`/`asset_builder`/`packager`/`default_sections`/
    `pricing_strategy["price_hint"]` are LIVE — `generic_adapter.py`
    actually reads and applies them.
  - `qa_profile`/`publishing_profile`/`recovery_policy` are ACCURATE
    DOCUMENTATION of the one real, already-fixed behavior every family
    gets today (book_generator.py hardcodes min_pages=4 and
    product_type="techdoc" for this pipeline shape; factory_state's
    recovery queue is generic) — not independently-switchable knobs.
    Claiming otherwise here would be exactly the kind of fabricated
    configurability this factory's own honesty discipline forbids.
  - `supported_marketplaces` is LIVE in the sense that
    `compatible_arms()` below computes a real answer against
    `channels.registry`'s actually-registered arms — but publishing
    itself dispatches identically for every family regardless (channels
    were already generic before this manifest existed).
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProductManifest:
    product_id: str
    family: str
    category: str
    content_generator: str
    asset_builder: str
    packager: str
    default_sections: list = field(default_factory=list)
    qa_profile: dict = field(default_factory=dict)
    publishing_profile: dict = field(default_factory=dict)
    pricing_strategy: dict = field(default_factory=dict)
    supported_marketplaces: list = field(default_factory=list)
    recovery_policy: dict = field(default_factory=dict)
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "family": self.family,
            "category": self.category,
            "content_generator": self.content_generator,
            "asset_builder": self.asset_builder,
            "packager": self.packager,
            "default_sections": self.default_sections,
            "qa_profile": self.qa_profile,
            "publishing_profile": self.publishing_profile,
            "pricing_strategy": self.pricing_strategy,
            "supported_marketplaces": self.supported_marketplaces,
            "recovery_policy": self.recovery_policy,
            "version": self.version,
        }


def compatible_arms(manifest):
    """Real, computed answer (not the manifest's own possibly-stale
    list): intersects `supported_marketplaces` with whichever channel
    arms are ACTUALLY registered right now via channels.registry."""
    from channels import registry as channel_registry
    registered = {arm.name for arm in channel_registry.all_arms()}
    return [m for m in manifest.supported_marketplaces if m in registered]


_MANIFESTS = {}


def register(manifest):
    """Register a manifest under manifest.product_id. Re-registering the
    same product_id is a deliberate override, not an error."""
    _MANIFESTS[manifest.product_id] = manifest


def get(product_id):
    """Return the registered manifest for `product_id`, or None if not
    registered."""
    return _MANIFESTS.get(product_id)


def all_manifests():
    """Return every currently registered manifest."""
    return list(_MANIFESTS.values())


def clear():
    """Test-only: reset the registry between test cases."""
    _MANIFESTS.clear()
