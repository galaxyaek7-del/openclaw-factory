"""Galaxy Forge — Product Families (Packaging Architecture Plan, Phase A).

The modular, multi-product-family Generation layer approved 2026-07-18
(see the Packaging Architecture Plan / ADR pending). Replaces the single
hardcoded "techdoc" dispatch in orchestrator/engines/production.py with a
registry of family adapters — each a thin wrapper over already-tested
book_generator.py functions in Phase A, self-registering on import exactly
like channels/*_arm.py already does for distribution arms.

Importing this package (via `families`) registers every Phase A family:
kdp_books, professional_templates, digital_toolkits, knowledge_bases.
"""

from . import families  # noqa: F401 — import triggers self-registration
