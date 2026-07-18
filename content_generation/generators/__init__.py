"""Self-registering content generators (Universal Production Engine).

Importing this package registers today's real implementations — both
thin wrappers over book_generator.py's already-tested, already-separate
content-only functions (no PDF/asset writing happens here, matching the
factory's existing separation between "get content" and "render it").
"""

from . import groq_generator  # noqa: F401
