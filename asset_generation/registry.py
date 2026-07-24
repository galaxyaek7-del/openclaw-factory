"""Galaxy Forge — Asset Generator registry (Universal Production
Engine §3/§6). Same shape as content_generation/registry.py and
channels/registry.py: an implementation registers itself under a name
at import time; callers only ever use get()/all(), never import a
concrete builder module directly.
"""

_BUILDERS = {}


def register(builder):
    """Register an asset builder under builder.name. Re-registering the
    same name is a deliberate override, not an error."""
    _BUILDERS[builder.name] = builder


def get(name):
    """Return the registered builder for `name`, or None if not
    registered."""
    return _BUILDERS.get(name)


def all_builders():
    """Return every currently registered asset builder."""
    return list(_BUILDERS.values())


def clear():
    """Test-only: reset the registry between test cases."""
    _BUILDERS.clear()
