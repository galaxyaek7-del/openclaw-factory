"""
Multi-Source Market Intelligence — connectors package (ADR-059).

Auto-discovery: every .py file here is imported once at package-import
time (pkgutil), which runs its @register_connector decorator. Adding an
11th source is: drop a new file here, nothing else.
"""

import importlib
import pkgutil

for _finder, _module_name, _is_pkg in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_module_name}")
