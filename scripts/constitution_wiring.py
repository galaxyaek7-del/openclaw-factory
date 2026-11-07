#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which modules the constitution cites are actually ACTIVE? (2026-11-07). Read-only.

    python scripts/constitution_wiring.py [--json]

The Master Operating Constitution and the Permanent Operating Doctrine are citation indexes: every article names the real module that
enforces it. A cited module can be (a) missing, (b) present but never called by the running factory (dormant), (c) called by the loop
or the server (wired), (d) reachable only by a human-run script (manual). For each cited module this reports where it is referenced
from, so "dormant" is a measured statement and not an impression.

  WIRED     required/spawned by factory_loop.js, server.js, a lib/ module that they load, or a loop-step script
  MANUAL    only a scripts/ tool or tests reference it
  DORMANT   nothing outside its own file and its tests references it
  MISSING   cited, but the file does not exist
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = [ROOT / "OpenClaw_Brain" / "00_Governance" / n for n in ("MASTER_OPERATING_CONSTITUTION.md", "PERMANENT_OPERATING_DOCTRINE.md",
                                                                 "GALAXY_FORGE_EXECUTIVE_CONSTITUTION.md")]
CITE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|js))`")
SKIP_DIRS = {"node_modules", ".git", "archive", "backups", "books", "__pycache__", "drafts", "reports"}


def cited(docs=DOCS):
    out = {}
    for d in docs:
        try:
            t = d.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in CITE.findall(t):
            out.setdefault(m, set()).add(d.name.split("_")[0].title())
    return out


def resolve(rel, root=ROOT):
    p = root / rel
    if p.exists():
        return p
    base = Path(rel).name
    hits = [h for h in root.rglob(base) if not (set(h.relative_to(root).parts) & SKIP_DIRS)]
    return hits[0] if len(hits) == 1 else None


def corpus(root=ROOT):
    """(path, text) for every source file that could call a module."""
    for ext in ("*.py", "*.js"):
        for f in root.rglob(ext):
            parts = set(f.relative_to(root).parts)
            if parts & SKIP_DIRS:
                continue
            try:
                yield f, f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue


LOOP_ROOTS = ("factory_loop.js", "server.js")
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def reachability(root=ROOT):
    """Stems reachable from the two running processes (factory_loop.js, server.js) through code references, tests excluded.
    A reference is an identifier equal to another source file's stem (import, require, spawn of '<stem>.py'). Over-approximates (a
    word that happens to equal a stem counts), so WIRED here means 'reachable', not 'proven to execute'."""
    stems = {}
    texts = {}
    for f, t in corpus(root):
        rel = str(f.relative_to(root)).replace("\\", "/")
        if rel.startswith("tests/"):
            continue
        stems.setdefault(f.stem, []).append(rel)
        texts[rel] = t
    refs = {rel: ({w for w in TOKEN.findall(t)} & stems.keys()) - {Path(rel).stem} for rel, t in texts.items()}
    seen, frontier = set(), [r for r in texts if r in LOOP_ROOTS]
    while frontier:
        cur = frontier.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for st in refs.get(cur, ()):
            frontier.extend(stems[st])
    return seen, texts


def classify(modules, root=ROOT):
    reached, texts = reachability(root)
    tests = {}
    for f, t in corpus(root):
        rel = str(f.relative_to(root)).replace("\\", "/")
        if rel.startswith("tests/"):
            tests[rel] = t
    out = []
    for rel in sorted(modules):
        p = resolve(rel, root)
        if p is None:
            out.append({"module": rel, "status": "MISSING", "callers": []})
            continue
        prel = str(p.relative_to(root)).replace("\\", "/")
        pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(p.stem) + r"(?![A-Za-z0-9_])")
        callers = [r for r, t in texts.items() if r != prel and Path(r).name != p.name and pat.search(t)]
        if prel in reached:
            status = "WIRED"
        elif callers:
            status = "MANUAL"
        else:
            status = "DORMANT"
        out.append({"module": rel, "status": status, "callers": callers[:4]})
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rows = classify(cited().keys())
    if "--json" in argv:
        sys.stdout.write(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
        return 0
    from collections import Counter
    c = Counter(r["status"] for r in rows)
    L = [f"CONSTITUTION WIRING: {len(rows)} cited modules: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items()))]
    for st in ("MISSING", "DORMANT", "MANUAL"):
        for r in rows:
            if r["status"] == st:
                L.append(f"[{st}] {r['module']}" + (f"  <- {', '.join(r['callers'])}" if r["callers"] else ""))
    sys.stdout.buffer.write(("\n".join(L) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
