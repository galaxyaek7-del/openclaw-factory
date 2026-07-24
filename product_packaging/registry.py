"""Galaxy Forge — Packager registry (Universal Production Engine
§3/§6). Same shape as content_generation/registry.py and
asset_generation/registry.py: an implementation registers itself under
a name at import time; callers only ever use get()/all(), never import
a concrete packager module directly.
"""

_PACKAGERS = {}


def register(packager):
    """Register a packager under packager.name. Re-registering the same
    name is a deliberate override, not an error."""
    _PACKAGERS[packager.name] = packager


def get(name):
    """Return the registered packager for `name`, or None if not
    registered."""
    return _PACKAGERS.get(name)


def all_packagers():
    """Return every currently registered packager."""
    return list(_PACKAGERS.values())


def clear():
    """Test-only: reset the registry between test cases."""
    _PACKAGERS.clear()
