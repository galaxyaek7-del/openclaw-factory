"""Cycle 86: transitive third-party dependency audit for the tracked test_a* chain.

CI installs only requirements.txt on a bare runner. This machine has packages
installed globally, which is why a clean checkout of HEAD passes locally and
fails in CI. Cycle 85's audit only looked at DIRECT imports in the test files;
this walks one level deeper, through the repo modules those tests import, since
a missing transitive package would produce exactly this symptom.
"""
import ast
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CLONE = r"C:\Users\Dell\AppData\Local\Temp\opencode\cycle85ci"
REPO = r"C:\openclaw-dasgboard"

stdlib = set(sys.stdlib_module_names)
third = {}


def scan(path):
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


tracked_tests = subprocess.run(
    ["git", "-C", REPO, "ls-files", "tests/test_a*.py"],
    capture_output=True, text=True).stdout.split()

# repo-local top-level module names
local = {os.path.splitext(f)[0] for f in os.listdir(REPO) if f.endswith(".py")}
for d in os.listdir(REPO):
    p = os.path.join(REPO, d)
    if os.path.isdir(p) and os.path.exists(os.path.join(p, "__init__.py")):
        local.add(d)

queue, seen = set(), set()
for rel in tracked_tests:
    queue |= scan(os.path.join(CLONE, rel))

while queue:
    m = queue.pop()
    if m in seen:
        continue
    seen.add(m)
    if m in stdlib or m in local:
        continue
    if os.path.isdir(os.path.join(REPO, m)):
        for f in os.listdir(os.path.join(REPO, m)):
            if f.endswith(".py"):
                queue |= scan(os.path.join(REPO, m, f))
        continue
    if os.path.isfile(os.path.join(REPO, m + ".py")):
        queue |= scan(os.path.join(REPO, m + ".py"))
        continue
    third[m] = third.get(m, 0) + 1

req = open(os.path.join(CLONE, "requirements.txt"), encoding="utf-8").read()
declared = set()
for line in req.splitlines():
    line = line.split("#")[0].strip()
    if line and not line.startswith("-"):
        import re
        mt = re.match(r"([A-Za-z0-9_.\-]+)", line)
        if mt:
            declared.add(mt.group(1).lower().replace("-", "_"))

print("third-party modules reachable from tracked test_a* files:\n")
unavailable = []
for mod in sorted(third):
    norm = mod.lower().replace("-", "_")
    declared_ok = norm in declared or mod.split("_")[0].lower() in declared
    try:
        __import__(mod)
        here = "importable here"
    except Exception:
        here = "NOT importable here"
        unavailable.append(mod)
    flag = "declared" if declared_ok else "*** NOT in requirements.txt ***"
    if not declared_ok:
        print(f"  {mod:26s} {here:20s} {flag}")

print()
if not any(m.lower().replace('-','_') not in declared and
           m.split('_')[0].lower() not in declared for m in third):
    print("every reachable third-party module IS declared -> requirements.txt is not the gap")
else:
    print("^ candidates for the CI-only failure; confirm against the CI log")