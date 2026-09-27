#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — targeted test runner (P10).

Maps changed files (git diff vs origin/main, uncommitted included) to
their test files and runs only those. Core security/crypto/infra changes
escalate to the full related suite automatically.

Usage: python scripts/test_changed.py [--base origin/main]
"""
import os
import subprocess
import sys

F = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = ("channels/", "lib/", "scripts/nostr_direct.py", "server.js",
        "factory_loop.js", "mission_control_api.py")


def run(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=120,
                       cwd=F)
    return p.stdout.strip()


def main():
    base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else "origin/main"
    changed = run(["git", "diff", "--name-only", base]) + "\n" + \
        run(["git", "diff", "--name-only"])
    files = sorted({l.strip() for l in changed.splitlines() if l.strip()})
    targets, escalate = [], False
    for f in files:
        name = os.path.basename(f)
        stem = os.path.splitext(name)[0]
        cand = os.path.join("tests", "test_" + stem + ".py")
        if os.path.isfile(os.path.join(F, cand)):
            targets.append(cand)
        if f.startswith(CORE) or f == ".env":
            escalate = True
    targets = sorted(set(targets))
    print("changed=%d tests=%s escalate=%s" % (len(files), targets, escalate))
    if escalate:
        print("CORE_TOUCHED: run the full related suites, not just these")
        return 2
    if not targets:
        print("NO_MATCHING_TESTS")
        return 0
    fails = 0
    for t in targets:
        p = subprocess.run([sys.executable, t], capture_output=True,
                           text=True, timeout=600, cwd=F)
        tail = (p.stdout or "")[-300:]
        print("---", t, "rc=", p.returncode)
        print(tail)
        fails += p.returncode != 0
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
