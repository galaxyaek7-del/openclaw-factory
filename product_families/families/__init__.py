"""Self-registering family definitions (Packaging Architecture Plan
§2/§7; Universal Production Engine Roadmap Steps 2-3, 2026-07-18).

Importing this package registers every real family with
product_families.registry. Three families (automation_systems,
professional_templates, digital_toolkits) are now Product Manifests —
plain configuration, registered via generic_adapter.py's
register_manifest_driven_family(), with no bespoke Python at all (see
product_families/manifest.py). kdp_books and knowledge_bases stay
bespoke Python modules because their real logic genuinely differs
(generate_book() rather than generate_product_package();
knowledge_bases enforces verbatim-only content) — not because they
weren't converted, but because there's nothing generic to configure.
"""

from . import kdp_books  # noqa: F401
from . import professional_templates  # noqa: F401
from . import digital_toolkits  # noqa: F401
from . import knowledge_bases  # noqa: F401
from . import automation_systems  # noqa: F401
