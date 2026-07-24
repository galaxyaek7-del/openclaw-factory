"""Galaxy Forge — Asset Generation (Universal Production Engine §3/§6,
2026-07-18).

Formalizes the swappable `AssetGenerator` interface: any implementation
is a callable taking a structured spec and returning a structured build
result, registered under a name — the "what the product is made of"
counterpart to content_generation's "what it says".

Importing this package registers the real, today implementations.
"""

from . import builders  # noqa: F401 — import triggers self-registration
