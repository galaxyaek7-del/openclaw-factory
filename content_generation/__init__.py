"""Galaxy Forge — Content Generation (Universal Production Engine §3/§6,
2026-07-18).

Formalizes the swappable `ContentGenerator` interface: any implementation
is a callable taking a structured request and returning structured
content, registered under a name. Swapping today's real Groq-backed
generator for a future AI model is a registry change, never an
architecture change.

Importing this package registers the real, today implementation.
"""

from . import generators  # noqa: F401 — import triggers self-registration
