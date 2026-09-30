#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical Inventory (V70, Tier-1 safe).

Post-V69: HEAD view != staged view != worktree view != runtime view must
never again be conflated. Read-only classifier over git state + disk:

- COMMITTED: files in HEAD.
- STAGED: index differs from HEAD (staged-new + staged-modified).
- WORKTREE: disk differs from index (unstaged modifications).
- IGNORED: gitignored paths relevant to execution (.env etc.).
- RUNTIME: append-only ledgers/logs that grow while the factory runs
  (data/*.jsonl, logs/) -- real state, not code drift.
- GENERATED: build artifacts with no source meaning (dist zips, PDFs,
  covers, snapshots .bak).
- UNTRACKED: everything else on disk but not in HEAD.

`detect_view_divergence()` is the testable invariant: the runtime entry
points must resolve identically under every view that claims to contain
them, and any STAGED-but-uncommitted runtime dependency is reported
explicitly (the V69 1,372-line class).
"""
import os
import subprocess

_FACTORY_ROOT = os.path.dirname(os.path.abspath(__file__))

RUNTIME_ENTRYPOINTS = [
    "server.js",
    "factory_loop.js",
    "mission_control_api.py",
    "book_generator.py",
]

GENERATED_SUFFIXES = (".zip", ".pdf", ".png", ".bak", ".pyc")
GENERATED_DIRS = ("books/covers", "cohort_GF_BATCH11_2026_09/dist", "seeds")
RUNTIME_LEDGER_DIRS = ("data", "logs")


def _run(args):
    return subprocess.run(args, capture_output=True, text=True,
                          cwd=_FACTORY_ROOT).stdout


def build_inventory():
    """Read-only. Never writes, never executes repo code."""
    head_files = set(_run(["git", "ls-tree", "-r", "--name-only", "HEAD"]).splitlines())
    staged = set()
    for line in _run(["git", "diff", "HEAD", "--name-only", "--cached"]).splitlines():
        if line.strip():
            staged.add(line.strip())
    unstaged = set()
    for line in _run(["git", "diff", "--name-only"]).splitlines():
        if line.strip():
            unstaged.add(line.strip())
    status = _run(["git", "status", "--porcelain"]).splitlines()
    untracked = {l[3:].strip().strip('"') for l in status if l[:2] == "??"}
    ignored = set()
    for line in _run(["git", "status", "--porcelain", "--ignored"]).splitlines():
        if line[:2] == "!!":
            ignored.add(line[3:].strip().strip('"'))

    def classify(path):
        low = path.lower()
        if path in untracked:
            if low.endswith(".jsonl") or low.startswith(RUNTIME_LEDGER_DIRS):
                return "RUNTIME"
            if low.endswith(GENERATED_SUFFIXES) or low.startswith(GENERATED_DIRS):
                return "GENERATED"
            return "UNTRACKED"
        if path in staged and path not in head_files:
            return "STAGED_NEW"
        if path in staged:
            return "STAGED_MODIFIED"
        if path in unstaged:
            return "WORKTREE_MODIFIED"
        if path in head_files:
            return "COMMITTED_CLEAN"
        return "UNKNOWN"

    views = {}
    for p in sorted(head_files | staged | unstaged | untracked):
        views[p] = classify(p)
    return {
        "head": _run(["git", "rev-parse", "HEAD"]).strip(),
        "counts": {v: sum(1 for x in views.values() if x == v) for v in sorted(set(views.values()))},
        "views": views,
        "ignored_relevant": sorted(p for p in ignored
                                   if p == ".env" or "nostr" in p.lower() or p.endswith(".key"))[:20],
        "entrypoints": {e: classify(e) if e in views else "MISSING" for e in RUNTIME_ENTRYPOINTS},
    }


def detect_view_divergence(inventory=None):
    """Testable invariant. Returns findings list (empty = clean)."""
    inv = inventory or build_inventory()
    findings = []
    staged_runtime = [p for p, v in inv["views"].items()
                      if v in ("STAGED_NEW", "STAGED_MODIFIED")
                      and p.endswith((".py", ".js"))]
    if staged_runtime:
        findings.append({
            "kind": "STAGED_UNCOMMITTED_SOURCE",
            "detail": "%d staged-but-uncommitted source files (V69 class)" % len(staged_runtime),
            "files": sorted(staged_runtime)[:20],
        })
    for entry, state in inv["entrypoints"].items():
        if state in ("STAGED_NEW", "STAGED_MODIFIED", "WORKTREE_MODIFIED", "MISSING"):
            findings.append({
                "kind": "ENTRYPOINT_NOT_COMMITTED_CLEAN",
                "detail": "%s is %s -- runtime != HEAD by construction" % (entry, state),
            })
    return findings
