"""Install tests/write_guard.py in Python subprocesses started during a test run.

tests/write_guard.install() (in the parent test process) puts this directory on
PYTHONPATH and sets GF_WRITE_GUARD_OVERLAY. Python imports `sitecustomize` at
start-up, so every child Python process redirects its writes into the same
overlay the parent reads. Outside a test run neither variable is set and this
file is never on the path, so it does nothing.
"""
import importlib.util
import os
import sys

if os.environ.get("GF_WRITE_GUARD_OVERLAY") and "write_guard" not in sys.modules:
    _path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "write_guard.py")
    try:
        _spec = importlib.util.spec_from_file_location("write_guard", _path)
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules["write_guard"] = _mod
        _spec.loader.exec_module(_mod)
        _mod.install()
    except Exception as _e:  # a broken guard must never stop the child program
        sys.stderr.write(f"write_guard: not installed in subprocess ({type(_e).__name__})\n")
