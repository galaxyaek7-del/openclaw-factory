"""Self-registering family adapters (Packaging Architecture Plan §2/§7;
Universal Production Engine Roadmap Step 2, 2026-07-18).

Importing this package registers every real family with
product_families.registry. The 4 Phase A families are thin wrappers over
an existing, already-tested book_generator.py function (no new content-
generation code); automation_systems (Roadmap Step 2) is the first
family built through the new content_generation/asset_generation/
product_packaging registries — the reference implementation for every
family after it.
"""

from . import kdp_books  # noqa: F401
from . import professional_templates  # noqa: F401
from . import digital_toolkits  # noqa: F401
from . import knowledge_bases  # noqa: F401
from . import automation_systems  # noqa: F401
