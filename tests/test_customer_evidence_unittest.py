"""Runs tests/test_customer_evidence.py under unittest, the CI runner.

That file is written as pytest functions taking a `tmp_path` fixture, so
`unittest discover` (scripts/run_python_group.py) collected none of its 13
tests. This adapter turns each test function into a unittest method with a
fresh temporary directory; the original file is left unchanged.
"""
import importlib.util
import inspect
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "test_customer_evidence.py"
_spec = importlib.util.spec_from_file_location("_customer_evidence_pytest_tests", _SRC)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def _wrap(fn):
    params = list(inspect.signature(fn).parameters)

    def method(self):
        if params == ["tmp_path"]:
            with tempfile.TemporaryDirectory() as d:
                fn(Path(d))
        elif not params:
            fn()
        else:
            self.skipTest("needs pytest fixtures %s" % params)
    method.__doc__ = fn.__doc__
    return method


class CustomerEvidence(unittest.TestCase):
    pass


for _name, _fn in sorted(vars(_mod).items()):
    if _name.startswith("test_") and inspect.isfunction(_fn):
        setattr(CustomerEvidence, _name, _wrap(_fn))


if __name__ == "__main__":
    unittest.main()
