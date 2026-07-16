"""
Executive Orchestrator — engine adapters package (ADR-051).

Auto-discovery: every .py file here is imported once at package-import
time (pkgutil), which runs its @register_engine decorator. Adding a new
engine to the company is: drop a new file here, nothing else — this
file, registry.py, and orchestrator.py stay untouched.
"""

import importlib
import pkgutil

for _finder, _module_name, _is_pkg in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_module_name}")
