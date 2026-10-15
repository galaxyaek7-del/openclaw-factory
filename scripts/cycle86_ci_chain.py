"""Which tracked test_a* file actually pulls openpyxl / PyPDF2 / yaml into CI group (a)?

If a test in that group needs a package requirements.txt does not declare, CI
fails on a bare runner while passing on this machine, which has it installed
globally. That is the exact asymmetry observed.
"""
import ast
import os
import subprocess
import sys
from collections import deque

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = r"C:\openclaw-dasgboard"
TARGETS = {"openpyxl", "PyPDF2", "yaml", "nostr_direct"}
stdlib = set(sys.stdlib_module_names)


def resolve(name):
    p = os.path.join(REPO, name + ".py")
    if os.path.isfile(p):
        return p
    p = os.path.join(REPO, name, "__init__.py")
    if os.path.isfile(p):
        return p
    for d in os.listdir(REPO):
        cand = os.path.join(REPO, d, name + ".py")
        if os.path.isfile(cand):
            return cand
    return None


def imports_of(path):
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    except Exception:
        return set()
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                mods.add(node.module.split(".")[0])
    return mods


tests = subprocess.run(["git", "-C", REPO, "ls-files", "tests/test_a*.py"],
                       capture_output=True, text=True).stdout.split()

found = {}
for t in tests:
    seen, q = set(), deque([(t, [])])
    while q:
        cur, path = q.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        if cur in TARGETS:
            found.setdefault(cur, (t, path))
            continue
        f = resolve(cur)
        if f:
            for m in imports_of(f):
                if m not in seen:
                    q.append((m, path + [cur]))
        # scripts/ helpers are imported by name too
        s = os.path.join(REPO, "scripts", cur + ".py")
        if os.path.isfile(s) and cur not in seen:
            for m in imports_of(s):
                if m not in seen:
                    q.append((m, path + [cur]))

print(f"tracked test_a files scanned: {len(tests)}\n")
if not found:
    print("NONE of the undeclared packages is reachable from group (a)")
    print("=> requirements.txt is NOT the cause of the CI failure in this group")
else:
    for pkg, (test, chain) in sorted(found.items()):
        print(f"  {pkg:14s} reached from {test}")
        print(f"       chain: {' -> '.join(chain) if chain else '(direct)'}")