"""Tests for dependency_graph.py's import-resolution correctness
(2026-07-23 audit): built against small, real, throwaway package trees
in a temp directory -- never mocks ast parsing itself, since the whole
point is verifying the real parser+resolver behaves correctly.

    python -m unittest tests.test_dependency_graph -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import dependency_graph as dg


class _TempRepo:
    def __init__(self, files):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel_path, content in files.items():
            path = self.root / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def cleanup(self):
        self._tmp.cleanup()


class TestSubmodulePrecision(unittest.TestCase):
    """`from pkg import sub` must register both pkg AND pkg.sub as
    dependencies when pkg.sub is a real file -- previously only the
    top-level package name (via .split(".")[0]) was ever recorded."""

    def setUp(self):
        self.repo = _TempRepo({
            "pkg/__init__.py": "",
            "pkg/sub.py": "",
            "user.py": "from pkg import sub\n",
        })

    def tearDown(self):
        self.repo.cleanup()

    def test_both_package_and_submodule_are_recorded(self):
        result = dg.build_graph(root=self.repo.root)
        self.assertEqual(set(result["graph"]["user"]), {"pkg", "pkg.sub"})


class TestRelativeImportResolution(unittest.TestCase):
    """`from . import b` inside pkg/a.py must resolve to `pkg.b` -- these
    were previously skipped entirely (node.level > 0 was treated as
    unresolvable), silently dropping every intra-package edge."""

    def setUp(self):
        self.repo = _TempRepo({
            "pkg/__init__.py": "",
            "pkg/a.py": "from . import b\n",
            "pkg/b.py": "",
        })

    def tearDown(self):
        self.repo.cleanup()

    def test_relative_import_resolves_to_real_submodule(self):
        result = dg.build_graph(root=self.repo.root)
        self.assertIn("pkg.b", result["graph"]["pkg.a"])

    def test_dependents_of_finds_the_relative_importer(self):
        result = dg.build_graph(root=self.repo.root)
        self.assertIn("pkg.a", dg.dependents_of("pkg.b", graph_result=result))


class TestDeferredVsEagerImports(unittest.TestCase):
    """A function-body import is a real dependency (for change-impact
    purposes) but must NOT count toward cycle detection, since it's a
    common, deliberate way to break an otherwise-real circular import."""

    def setUp(self):
        self.repo = _TempRepo({
            "a.py": "import b\n",
            "b.py": "def f():\n    import a\n    return a\n",
        })

    def tearDown(self):
        self.repo.cleanup()

    def test_full_graph_includes_the_deferred_edge(self):
        result = dg.build_graph(root=self.repo.root)
        self.assertIn("a", result["graph"]["b"])

    def test_eager_graph_excludes_the_deferred_edge(self):
        result = dg.build_graph(root=self.repo.root, module_level_only=True)
        self.assertNotIn("a", result["graph"]["b"])

    def test_cycle_detection_uses_eager_graph_by_default(self):
        self.assertEqual(dg.find_cycles(dg.build_graph(root=self.repo.root, module_level_only=True)), [])


class TestAncestorPackageEdges(unittest.TestCase):
    """Importing `a.b.c` always executes a/__init__.py and a/b/__init__.py
    first (real Python semantics) -- a change to either really does
    affect the importer, so both must appear as dependencies."""

    def setUp(self):
        self.repo = _TempRepo({
            "a/__init__.py": "",
            "a/b/__init__.py": "",
            "a/b/c.py": "",
            "user.py": "from a.b.c import x\n",
        })

    def tearDown(self):
        self.repo.cleanup()

    def test_all_ancestor_packages_are_recorded(self):
        result = dg.build_graph(root=self.repo.root)
        self.assertEqual(set(result["graph"]["user"]), {"a", "a.b", "a.b.c"})

    def test_ancestor_package_is_not_a_false_orphan(self):
        result = dg.build_graph(root=self.repo.root)
        zero_dep = dg.find_zero_dependent_modules(result)
        self.assertNotIn("a", zero_dep)
        self.assertNotIn("a.b", zero_dep)


if __name__ == "__main__":
    unittest.main()
