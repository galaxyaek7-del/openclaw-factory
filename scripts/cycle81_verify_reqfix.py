"""Verify the requirements fix covers every module that imports pytest."""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

files = subprocess.run(["git", "ls-files", "tests/*.py"],
                       capture_output=True, text=True).stdout.split()
req = open("requirements.txt", encoding="utf-8").read()

need = []
for f in files:
    try:
        h = open(f, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    if re.search(r"(?m)^\s*import pytest\s*$", h):
        need.append(f)

declared = bool(re.search(r"(?m)^pytest==", req))
print(f"tracked test modules importing pytest : {len(need)}")
for m in need:
    print(f"    {m}")
print(f"pytest pinned in requirements.txt     : {declared}")
print()
print("VERDICT:", "root cause addressed" if declared else "STILL MISSING")

# Sanity: the file must remain parseable by pip's requirement parser shape.
bad = [ln for ln in req.splitlines()
       if ln.strip() and not ln.strip().startswith(("#", "-"))
       and "==" not in ln and not re.match(r"^[A-Za-z0-9_.\-]+$", ln.strip())]
print("malformed requirement lines:", bad if bad else "none")