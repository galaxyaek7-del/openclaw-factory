"""
Market Intelligence Core — scoring package (ADR-049).

Auto-discovery: every .py file in this package is imported once at
package-import time, which runs its @register_scorer /
@register_meta_scorer decorator and adds it to the pipeline. Adding a
new scoring dimension is: drop a new file here, nothing else — this
file, pipeline.py, and every existing scorer stay untouched. This is
the actual mechanism behind the requirement "the pipeline must allow
adding future scoring modules without modifying existing ones."
"""

import importlib
import pkgutil

for _finder, _module_name, _is_pkg in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_module_name}")
