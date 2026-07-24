"""Galaxy Forge — Content Generator registry (Universal Production
Engine §3/§6). Same shape as channels/registry.py: an implementation
registers itself under a name at import time; the pipeline only ever
calls get()/all(), never imports a concrete generator module directly.

A future AI model replacing today's Groq calls means adding one new
self-registering module here — never touching product_families/ or any
pipeline code that consumes a ContentGenerator.
"""

_GENERATORS = {}


def register(generator):
    """Register a content generator under generator.name. Re-registering
    the same name is a deliberate override (e.g. a future model
    replacing today's Groq generator), not an error."""
    _GENERATORS[generator.name] = generator


def get(name):
    """Return the registered generator for `name`, or None if not
    registered."""
    return _GENERATORS.get(name)


def all_generators():
    """Return every currently registered content generator."""
    return list(_GENERATORS.values())


def clear():
    """Test-only: reset the registry between test cases."""
    _GENERATORS.clear()
