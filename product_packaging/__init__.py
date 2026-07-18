"""OpenClaw Factory — Packaging (Universal Production Engine §3/§6,
2026-07-18): bundles Asset Generation's output into ONE distributable
artifact per product.

Named `product_packaging` (not `packaging`) to avoid shadowing the
installed pip `packaging` library (version parsing, used by
pip/setuptools) — this factory's root directory is on sys.path, so a
same-named top-level package here would break every import of the real
one.

Importing this package registers the real, today implementation.
"""

from . import bundle  # noqa: F401 — import triggers self-registration
