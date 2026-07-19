"""
Capability Gap Scanner (EOS Phase 1, 2026-07-19) — "Company Evolution
Engine" §"detect missing capabilities". Real, narrowly-scoped: reads
config/capability_registry.json's `capabilities` list (ADR-040's REAL/
ESTIMATED/DISCOVERY schema) and flags every entry not yet REAL.

Deliberately no staleness/age filter: the registry has no per-entry
timestamp (only a file-level `last_updated`), so an age-based "this gap
has been open for N days" signal would be fabricated — this factory's
own capability-maturity discipline (this exact file) forbids inventing
a number the data doesn't support. Level-based filtering only.
"""

import json
import os

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
CAPABILITY_REGISTRY_PATH = os.path.join(FACTORY_DIR, 'config', 'capability_registry.json')


def find_capability_gaps(registry_path=None, include_estimated=True):
    """Returns every capability at DISCOVERY level (a real, unmeasured
    gap), and optionally ESTIMATED level (a lower-priority, partially-
    measured gap) too. REAL-level capabilities are never flagged."""
    path = registry_path or CAPABILITY_REGISTRY_PATH
    if not os.path.exists(path):
        return {
            "discovery_level": [],
            "estimated_level": [],
            "reason": "لا ملف config/capability_registry.json موجود",
        }

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    capabilities = data.get("capabilities", [])
    discovery = [c for c in capabilities if c.get("level") == "DISCOVERY"]
    estimated = [c for c in capabilities if c.get("level") == "ESTIMATED"] if include_estimated else []

    return {
        "discovery_level": discovery,
        "estimated_level": estimated,
        "total_capabilities": len(capabilities),
        "last_updated": data.get("last_updated"),
        "source": "config/capability_registry.json",
    }
