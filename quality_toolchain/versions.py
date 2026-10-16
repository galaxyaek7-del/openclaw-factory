# -*- coding: utf-8 -*-
"""Deterministic tool version identification + environment capability
fingerprint. Every adapter must be able to report *which* version produced a
result so evidence records are auditable and reproducible.

Honesty rule: a version/availability string is only ever reported as
OBSERVED by actually importing the module at call time (or confirming the
pure-stdlib marker). Nothing here guesses an installed version from PyPI.
"""

import importlib
import sys


# Stdlib canonical version — no third-party package to pin. Used by
# zero-dependency adapters so evidence records still carry a stable
# "version" field even when the capability is the Python runtime itself.
STDLIB_VERSION_MARKER = "python-stdlib:" + ".".join(
    str(p) for p in (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
)


def version_of_textstat():
    """OBSERVED version of the textstat package if importable; else None."""
    try:
        import textstat
        v = getattr(textstat, "__version__", None)
        if isinstance(v, tuple):
            return ".".join(str(x) for x in v)
        return str(v) if v else "unknown"
    except Exception:
        return None


def capability_fingerprint():
    """A JSON-serializable dict describing which tool capabilities are
    actually present in this environment, each labeled OBSERVED vs UNKNOWN.
    Facility to detect the tool is available *before* a quality decision runs,
    and to reflect availability honestly in evidence records."""
    import importlib.util as _u

    def _probe(module):
        try:
            return bool(_u.find_spec(module))
        except Exception:
            return False

    return {
        "python": STDLIB_VERSION_MARKER,
        "textstat": {"available": _probe("textstat"), "version": version_of_textstat()},
    }