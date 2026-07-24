"""Galaxy Forge — Arm registry (OCTOPUS_ARCHITECTURE.md §5, ADR-4).

Open/Closed: adding a platform means a new arm file that calls register()
on itself at import time — this module and the future distributor never
change. No arm is imported here; each arm module is responsible for
registering itself when it is imported.
"""

_ARMS = {}


def register(arm):
    """Register an arm instance under arm.name. Re-registering the same
    name is a deliberate override (e.g. a test double), not an error."""
    _ARMS[arm.name] = arm


def get(name):
    """Return the registered arm for `name`, or None if not registered."""
    return _ARMS.get(name)


def all_arms():
    """Return every currently registered arm."""
    return list(_ARMS.values())


def clear():
    """Test-only: reset the registry between test cases."""
    _ARMS.clear()
