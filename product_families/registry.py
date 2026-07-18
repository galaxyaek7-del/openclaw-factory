"""OpenClaw Factory — Product Family registry (Packaging Architecture Plan §5).

Same shape as channels/registry.py: an adapter registers itself under
adapter.name at import time; nothing here imports a concrete family
module — orchestrator/engines/production.py only ever calls get()/
all_families(), never a specific family class. Adding a 10th family means
adding one new self-registering file, never touching this module.
"""

_FAMILIES = {}


def register(adapter):
    """Register a family adapter under adapter.name. Re-registering the
    same name is a deliberate override (e.g. a test double), not an error."""
    _FAMILIES[adapter.name] = adapter


def get(name):
    """Return the registered adapter for `name`, or None if not registered —
    the caller (orchestrator/engines/production.py) must fall back safely
    rather than treat None as an error; a family with no adapter yet is
    expected during the phased rollout, not a bug."""
    return _FAMILIES.get(name)


def all_families():
    """Return every currently registered family adapter."""
    return list(_FAMILIES.values())


def clear():
    """Test-only: reset the registry between test cases."""
    _FAMILIES.clear()
