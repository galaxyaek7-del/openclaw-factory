"""Factory Dependency Graph (Factory OS directive, 2026-07-23).

A REAL graph, computed from the actual `import` statements in every real
.py file in this repo via the standard-library `ast` module -- never a
hand-drawn diagram that goes stale the moment the code changes. Same
"parse, don't guess" discipline STRUCTURAL_DIAGNOSIS.md used manually;
this makes it a reusable, re-runnable function instead of a one-time
research pass.

Scope: internal, first-party modules only (stdlib/third-party imports
like `json`, `flask`, `groq` are noise for an architecture map and are
dropped). A module is "internal" if `{name}.py` or `{name}/__init__.py`
exists relative to the repo root.

Excludes venv/, node_modules/, __pycache__/, tests/, .git/ -- the same
exclusion set used throughout this session's audits.

"Changing one module must automatically notify every dependent module"
(Factory OS directive) -- honestly reframed: there is no scheduler in
this factory (CLAUDE.md), so nothing here runs a live notification.
What IS real: dependents_of(module) gives the exact, computed, transitive
set of modules that would need re-checking after a real change, callable
on demand the moment a change is made.
"""

import ast
import json
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent

EXCLUDED_DIRS = {"venv", "node_modules", "__pycache__", "tests", ".git", ".vscode", ".github"}

# STRUCTURAL_DIAGNOSIS.md / prior audits: modules deliberately standalone,
# invoked by a human directly, never imported by anything else in this
# repo by design -- a zero-dependents count for these is NOT dead code.
KNOWN_STANDALONE_ENTRY_POINTS = {
    "audit_seed", "hive_logbook_generator", "seed_english_book",
    "scripts.readiness_certificate", "scripts.process_approved_drafts",
    "scripts.poll_sales", "scripts.check_paddle_checkout_status", "scripts.ops_maintenance",
    "book_generator", "market_hunter", "market_analyzer", "reality",
    "profit_oracle", "distributor", "safety_filter", "executive_quality_gate",
    "enterprise_readiness", "executive_board", "factory_orchestrator", "dependency_graph",
    "mission_control_api", "factory_health_monitor", "chaos_testing_engine",
}


def _iter_real_py_files(root=None):
    root = Path(root) if root else _FACTORY_ROOT
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        yield path, rel


def _module_name(rel_path):
    parts = list(rel_path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _internal_modules(root=None):
    root = Path(root) if root else _FACTORY_ROOT
    names = set()
    for _, rel in _iter_real_py_files(root):
        names.add(_module_name(rel))
        # also register the top-level package name (e.g. "channels" for channels/registry.py)
        if len(rel.parts) > 1:
            names.add(rel.parts[0])
    return names


def _current_package(module_name, is_init):
    """The package a module's relative imports are resolved against.
    An __init__.py's own module name IS the package; a plain submodule's
    package is its dotted name minus its own last component."""
    if is_init:
        return module_name
    return module_name.rsplit(".", 1)[0] if "." in module_name else ""


def _resolve_relative_base(current_package, level):
    """level=1 ("from . import x") resolves against current_package
    itself; level=2 ("from .. import x") against its parent, etc. --
    the same rule Python's own import system uses (PEP 328)."""
    if level <= 1:
        return current_package
    parts = current_package.split(".") if current_package else []
    climb = level - 1
    if climb >= len(parts):
        return ""
    return ".".join(parts[: len(parts) - climb])


class _ModuleLevelImportCollector(ast.NodeVisitor):
    """Visits only import statements reachable at module *load* time --
    does not descend into function/method bodies, where a deferred
    import is a real, common, deliberate technique for breaking an
    actual circular dependency (see dossier_bundle/build_bundle.py's own
    comment: "a module-level import here would be circular"). Treating
    those the same as a top-level import makes a cycle detector report
    cycles that don't actually fail at import time -- noise that erodes
    trust in every other real cycle it finds."""

    def __init__(self):
        self.nodes = []

    def visit_Import(self, node):
        self.nodes.append(node)

    def visit_ImportFrom(self, node):
        self.nodes.append(node)

    def visit_FunctionDef(self, node):
        pass  # deliberately don't descend

    def visit_AsyncFunctionDef(self, node):
        pass  # deliberately don't descend

    def visit_Lambda(self, node):
        pass  # can't contain a statement anyway, but stay consistent


def _extract_imports(tree, module_name, is_init, module_level_only=False):
    """Returns raw (kind, module_or_alias, names) tuples -- unresolved
    against the real internal-module set, which only build_graph has.
    Relative imports (`from . import x`, `from .. import x`) ARE
    statically resolvable to a real dotted module name given the
    importing file's own package -- they were previously skipped
    entirely on the mistaken assumption that they weren't (found
    auditing this module's own output, 2026-07-23), which silently
    dropped every intra-package edge in packages that use them
    (e.g. channels/etsy_arm.py's `from . import etsy_publisher`).

    module_level_only=True restricts to imports reachable at import
    time (see _ModuleLevelImportCollector) -- used for cycle detection,
    where a deferred import legitimately breaks a real cycle."""
    imports = []
    current_package = _current_package(module_name, is_init)
    if module_level_only:
        collector = _ModuleLevelImportCollector()
        collector.visit(tree)
        raw_nodes = collector.nodes
    else:
        raw_nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    for node in raw_nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(("import", alias.name, None))
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                base = _resolve_relative_base(current_package, node.level)
                target = f"{base}.{node.module}" if node.module else base
                if target:
                    imports.append(("from", target, [alias.name for alias in node.names]))
            elif node.module:
                imports.append(("from", node.module, [alias.name for alias in node.names]))
    return imports


def _resolve_imports(raw_imports, internal):
    """Resolves raw import tuples against the real internal-module set,
    preferring the most specific real submodule. Without this, `from
    decision_engine import ranking` only ever registered a dependency on
    the top-level `decision_engine` package -- `decision_engine.ranking`
    (a real file) never appeared as a target, so every submodule of every
    multi-file package looked like a zero-dependent orphan regardless of
    real usage (found auditing this module's own output, 2026-07-23)."""
    modules = set()
    for kind, mod, names in raw_imports:
        if kind == "import":
            if mod in internal:
                modules.add(mod)
            else:
                top = mod.split(".")[0]
                if top in internal:
                    modules.add(top)
        else:  # "from"
            if mod in internal:
                modules.add(mod)
                for n in names or []:
                    candidate = f"{mod}.{n}"
                    if candidate in internal:
                        modules.add(candidate)
            else:
                top = mod.split(".")[0]
                if top in internal:
                    modules.add(top)
    return _with_ancestor_packages(modules, internal)


def _with_ancestor_packages(modules, internal):
    """Importing `a.b.c` always executes `a/__init__.py` then
    `a/b/__init__.py` first -- real Python import semantics, not an
    edge case. Without this, a package whose __init__.py has no
    dependents of its OWN but whose submodules are imported directly
    (e.g. `from dossier_bundle.build_bundle import x`) looked like a
    zero-dependent orphan even though changing dossier_bundle/__init__.py
    really would affect that importer (found auditing this module's own
    output, 2026-07-23)."""
    expanded = set(modules)
    for m in modules:
        parts = m.split(".")
        for i in range(1, len(parts)):
            ancestor = ".".join(parts[:i])
            if ancestor in internal:
                expanded.add(ancestor)
    return expanded


def build_graph(root=None, module_level_only=False):
    """Returns {module_name: sorted [modules it really imports]} --
    internal, first-party dependencies only. Recomputed fresh every call
    -- never cached, never assumed stale-safe.

    module_level_only=True builds the import-time-only graph (see
    _ModuleLevelImportCollector) -- pass this for cycle detection.
    Leave False (the default) for dependents_of/orphan detection, where
    a deferred import is still a real dependency a change must account
    for, just not one that can fail at import time."""
    root = Path(root) if root else _FACTORY_ROOT
    internal = _internal_modules(root)
    graph = {}
    errors = []

    for path, rel in _iter_real_py_files(root):
        name = _module_name(rel)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as e:
            errors.append({"file": str(rel), "error": str(e)})
            graph.setdefault(name, [])
            continue
        raw_imports = _extract_imports(tree, name, rel.name == "__init__.py",
                                        module_level_only=module_level_only)
        imported = _resolve_imports(raw_imports, internal)
        imported.discard(name)
        imported.discard(name.split(".")[0])  # never a self-edge from package-name collision
        graph[name] = sorted(imported)

    return {"graph": graph, "parse_errors": errors, "module_count": len(graph)}


def dependents_of(module_name, graph_result=None):
    """Real, transitive closure: every module that (directly or
    indirectly) imports `module_name`. This is the honest, on-demand
    version of "notify every dependent module" -- callable the moment a
    real change is made, not a live background push."""
    graph_result = graph_result or build_graph()
    graph = graph_result["graph"]

    reverse = {name: set() for name in graph}
    for name, deps in graph.items():
        for dep in deps:
            reverse.setdefault(dep, set()).add(name)

    seen = set()
    frontier = {module_name}
    while frontier:
        next_frontier = set()
        for m in frontier:
            for dependent in reverse.get(m, set()):
                if dependent not in seen:
                    seen.add(dependent)
                    next_frontier.add(dependent)
        frontier = next_frontier
    return sorted(seen)


def find_cycles(graph_result=None):
    """Real DFS-based cycle detection over the import-time-only graph
    (module_level_only=True) -- a cycle only means something as "this
    would raise ImportError" if it's built from imports that actually
    execute at import time. A deferred (function-body) import is a real,
    common way this codebase already breaks an otherwise-real cycle (see
    dossier_bundle/build_bundle.py); counting it as a live edge would
    report a cycle Python itself would never hit. Returns a list of real
    cycles (each a list of module names) -- empty list is an honest,
    computed "none found," never assumed.

    If you pass an explicit graph_result built with module_level_only=
    False (e.g. reusing the graph from find_zero_dependent_modules), you
    are opting into the noisier "logical cycle" reading yourself.

    Caveat (found auditing this module, 2026-07-23, verified by actually
    importing the reported cycle -- both `import product_families` and
    `import asset_generation.builders.pdf_builder` succeed today with no
    ImportError): a module-level `from pkg.sub import x` only needs `pkg`
    present in sys.modules, not fully executed, so package-to-package
    submodule cycles are frequently safe in real Python even though the
    graph is genuinely cyclic. Treat every reported cycle as "worth a
    human look," never as "confirmed broken," unless independently
    verified by actually importing it."""
    graph_result = graph_result or build_graph(module_level_only=True)
    graph = graph_result["graph"]

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {name: WHITE for name in graph}
    cycles = []
    path_stack = []

    def visit(node):
        color[node] = GRAY
        path_stack.append(node)
        for dep in graph.get(node, []):
            if dep not in color:
                continue
            if color[dep] == GRAY:
                idx = path_stack.index(dep)
                cycles.append(path_stack[idx:] + [dep])
            elif color[dep] == WHITE:
                visit(dep)
        path_stack.pop()
        color[node] = BLACK

    for name in graph:
        if color[name] == WHITE:
            visit(name)

    return cycles


def find_zero_dependent_modules(graph_result=None):
    """Real modules with zero real internal dependents -- candidates for
    "unused/orphaned," EXCEPT known standalone entry points (a human-run
    CLI tool with zero importers is a deliberate design, not dead code --
    matches the corrected methodology from the prior Full Factory
    Integrity Audit's duplication/orphans fork)."""
    graph_result = graph_result or build_graph()
    graph = graph_result["graph"]
    all_deps = set()
    for deps in graph.values():
        all_deps.update(deps)

    candidates = []
    for name in graph:
        if name in all_deps:
            continue
        if name in KNOWN_STANDALONE_ENTRY_POINTS:
            continue
        candidates.append(name)
    return sorted(candidates)


def main():
    result = build_graph()
    cycles = find_cycles(build_graph(module_level_only=True))
    zero_dep = find_zero_dependent_modules(result)
    print(json.dumps({
        "module_count": result["module_count"],
        "parse_errors": result["parse_errors"],
        "cycles_found": cycles,
        "zero_dependent_candidates": zero_dep,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
