"""Self-registering Phase A family adapters (Packaging Architecture Plan §2/§7).

Importing this package registers all four Phase A families with
product_families.registry — each a thin wrapper over an existing,
already-tested book_generator.py function. No new content-generation
code lives here.
"""

from . import kdp_books  # noqa: F401
from . import professional_templates  # noqa: F401
from . import digital_toolkits  # noqa: F401
from . import knowledge_bases  # noqa: F401
