"""Every third-party module imported by TRACKED code, checked against what
requirements.txt actually declares.

Why this exists: undeclared dependencies are invisible on this machine (it has
everything installed) and break only on a clean CI runner. requests,
beautifulsoup4, oauthlib, pytest, and on 2026-10-16 openpyxl, numpy and
python-docx were each found one CI round trip at a time.

Rewritten 2026-10-16. The first version could not be used as a gate: it
derived local package names as `"golden_hunter/hunt.py".split("/")[0][:-3]`
("golden_hun"), so every local package was reported as a missing third-party
dependency, and the real gaps drowned in ~60 false alarms.

Classification:
  HARD  a module-level import that is not inside a try/except that catches
        ImportError (or a broader class). A clean environment without the
        package fails at import time -> exit code 1.
  SOFT  an import inside a function, or guarded by such a try/except. It only
        breaks when that code path runs; reported, not failing.

Usage:
    python scripts/audit_requirements.py            # report; exit 1 on HARD gaps
    python scripts/audit_requirements.py --json     # machine-readable
"""
import ast
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STD = set(sys.stdlib_module_names)

# Distribution name -> import name(s), for the ones that differ. Used in
# addition to the installed packages' own metadata.
DIST_TO_IMPORT = {
    "pillow": ["PIL"],
    "beautifulsoup4": ["bs4"],
    "python-bidi": ["bidi"],
    "arabic-reshaper": ["arabic_reshaper"],
    "pyyaml": ["yaml"],
    "python-dateutil": ["dateutil"],
    "google-api-python-client": ["googleapiclient"],
    "opentelemetry-api": ["opentelemetry"],
    "python-docx": ["docx"],
    "pymupdf": ["fitz", "pymupdf"],
    "imageio-ffmpeg": ["imageio_ffmpeg"],
    "et-xmlfile": ["et_xmlfile"],
}

GUARD_EXCEPTIONS = {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}


def declared_import_names(req_path):
    names = set()
    dist_names = []
    for line in open(req_path, encoding="utf-8"):
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        dist_names.append(re.split(r"[=<>\[~!; ]", line)[0].strip().lower())
    try:
        from importlib.metadata import packages_distributions
        reverse = {}
        for imp, dists in packages_distributions().items():
            for d in dists:
                reverse.setdefault(d.lower().replace("_", "-"), []).append(imp)
    except Exception:  # noqa: BLE001 -- metadata is a bonus, the table still works
        reverse = {}
    for d in dist_names:
        names.add(d.replace("-", "_"))
        names.update(DIST_TO_IMPORT.get(d, []))
        names.update(reverse.get(d, []))
    return {n.lower() for n in names}


def local_names(tracked):
    """Top-level folders, plus the stem of every tracked .py file at any depth
    (many scripts put a folder on sys.path and import its modules bare), plus
    the folder holding each tracked .py file. The last one covers the src/
    layout: a script that puts src/ on sys.path imports src/quality/ as the
    package `quality`, which the first two rules never named."""
    out = set()
    for f in tracked:
        parts = f.split("/")
        out.add(parts[0][:-3] if len(parts) == 1 and parts[0].endswith(".py") else parts[0])
        if f.endswith(".py"):
            out.add(parts[-1][:-3])
            if len(parts) >= 2:
                out.add(parts[-2])
    return out


def _guarded(handlers):
    for h in handlers:
        if h.type is None:
            return True
        types = h.type.elts if isinstance(h.type, ast.Tuple) else [h.type]
        for t in types:
            name = t.id if isinstance(t, ast.Name) else getattr(t, "attr", "")
            if name in GUARD_EXCEPTIONS:
                return True
    return False


def imports_with_kind(source):
    """Yield (module_root, 'HARD'|'SOFT') for every absolute import."""
    tree = ast.parse(source)
    out = []

    def visit(node, in_func, in_guard):
        for child in ast.iter_child_nodes(node):
            func = in_func or isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
            guard = in_guard
            if isinstance(child, ast.Try) and _guarded(child.handlers):
                for stmt in child.body:
                    visit_stmt(stmt, func, True)
                # An import inside the except handler is the fallback that
                # only runs when the first import failed (e.g. pypdf ->
                # PyPDF2): optional by construction, so SOFT as well.
                for handler in child.handlers:
                    for stmt in handler.body:
                        visit_stmt(stmt, func, True)
                for part in (child.orelse, child.finalbody):
                    for stmt in part:
                        visit_stmt(stmt, func, in_guard)
                continue
            visit_stmt(child, func, guard)

    def visit_stmt(child, in_func, in_guard):
        names = []
        if isinstance(child, ast.Import):
            names = [a.name.split(".")[0] for a in child.names]
        elif isinstance(child, ast.ImportFrom) and child.level == 0 and child.module:
            names = [child.module.split(".")[0]]
        for n in names:
            out.append((n, "SOFT" if (in_func or in_guard) else "HARD"))
        if not isinstance(child, (ast.Import, ast.ImportFrom)):
            visit(child, in_func or isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)), in_guard)

    visit(tree, False, False)
    return out


def audit(root=ROOT, tracked=None, req_path=None):
    if tracked is None:
        tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                                 cwd=root, check=True).stdout.split()
    declared = declared_import_names(req_path or os.path.join(root, "requirements.txt"))
    local = local_names(tracked)
    hard, soft = {}, {}
    for rel in (f for f in tracked if f.endswith(".py")):
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                pairs = imports_with_kind(fh.read())
        except (SyntaxError, OSError, ValueError):
            continue
        for mod, kind in pairs:
            if mod in STD or mod in local or mod.startswith("_") or mod.lower() in declared:
                continue
            (hard if kind == "HARD" else soft).setdefault(mod, set()).add(rel)
    soft = {m: v for m, v in soft.items() if m not in hard}
    # A name that exists on disk as a local module/package but is not tracked
    # is not a missing *library*: it is code missing from the repository
    # (a fresh clone breaks). Named separately so the fix is obvious.
    on_disk = {m for m in set(hard) | set(soft)
               if os.path.isdir(os.path.join(root, m)) or os.path.isfile(os.path.join(root, m + ".py"))}
    return {"hard": {m: sorted(v) for m, v in sorted(hard.items())},
            "soft": {m: sorted(v) for m, v in sorted(soft.items())},
            "untracked_local": sorted(on_disk)}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    r = audit()
    if "--json" in argv:
        print(json.dumps(r, indent=2))
    else:
        print("=== HARD: module-level third-party imports NOT declared (fail a clean install) ===")
        for m, users in r["hard"].items():
            print("  %-22s <- %d file(s): %s" % (m, len(users), ", ".join(users[:3])))
        if not r["hard"]:
            print("  none")
        print("=== SOFT: undeclared but lazy/guarded (break only when that path runs) ===")
        for m, users in r["soft"].items():
            print("  %-22s <- %d file(s): %s" % (m, len(users), ", ".join(users[:3])))
        if not r["soft"]:
            print("  none")
        if r["untracked_local"]:
            print("=== of these, LOCAL code present on disk but NOT in git (a fresh clone lacks it) ===")
            print("  " + ", ".join(r["untracked_local"]))
    return 1 if r["hard"] else 0


if __name__ == "__main__":
    sys.exit(main())
