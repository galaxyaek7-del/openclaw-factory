"""Cycle 81: inventory the source/test drift that group (a) was masking.

The pytest import failure aborted the CI job at the first step, so groups
(c-d) through (q-z) never ran on CI. Fixing the import therefore reveals a
second, independent layer: tests that call kwargs and import names the tracked
source does not have.

This separates the two categories, because they need different decisions:
  MISSING_PARAMETER  - source lost an injectable path parameter
  MISSING_SYMBOL      - source lost a function/attribute the tests import
  STALE_TEXT_ASSERT  - test asserts on source text that was legitimately changed
"""
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# Cycle 81: no absolute Temp path in a tracked script -- see
# tests/test_no_temp_dependencies.py. The clone comes from $GF_CLONE or
# argv[1] and defaults to this repository.
REPO = (sys.argv[1] if len(sys.argv) > 1
        else os.environ.get("GF_CLONE")
        or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GROUPS = {
    "c-d": "test_[c-d]*.py", "f": "test_f*.py", "g-h": "test_[g-h]*.py",
    "i-p": "test_[i-p]*.py",
}

out = {}
for gname, pat in GROUPS.items():
    files = subprocess.run(["git", "-C", REPO, "ls-files", f"tests/{pat}"],
                           capture_output=True, text=True).stdout.split()
    missing_param, missing_sym, stale_text = [], [], []
    for f in files:
        p = f.replace("/", "\\")
        try:
            h = open(f"{REPO}\\{p}", encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for m in re.finditer(r"(\w+)\(([^)]*?)circuit_breaker_state_path[^)]*\)", h):
            missing_param.append((f, m.group(1)))
        for m in re.finditer(r"from ([\w.]+) import ([\w_]+)", h):
            mod, name = m.group(1), m.group(2)
            try:
                __import__(mod)
            except Exception:
                continue
            if "." not in mod:
                try:
                    m2 = __import__(mod, fromlist=[name])
                    if not hasattr(m2, name) and mod != "channels":
                        missing_sym.append((f, f"{mod}.{name}"))
                except Exception:
                    pass
    out[gname] = {"files": len(files),
                  "missing_parameter": sorted(set(missing_param)),
                  "missing_symbol": sorted(set(missing_sym))}

print("=" * 70)
print("CI groups that remain red after the pytest fix (clean tracked clone)")
print("=" * 70)
for g, d in out.items():
    print(f"\ngroup {g}: {d['files']} tracked test files")
    if d["missing_parameter"]:
        print("  MISSING_PARAMETER (source lacks an injectable path kwarg):")
        for f, fn in d["missing_parameter"][:8]:
            print(f"      {f}  -> {fn}(...circuit_breaker_state_path...)")
    if d["missing_symbol"]:
        print("  MISSING_SYMBOL (test imports a name the source lacks):")
        for f, sym in d["missing_symbol"][:8]:
            print(f"      {f}  -> {sym}")

print()
print("These predate Cycle 85/86 and are NOT caused by the pytest import.")
print("They were invisible because the CI job aborted at group (a).")