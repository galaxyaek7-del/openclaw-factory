#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily local snapshot of source files that git does not track (2026-11-06). Never pushes, never touches main or the working tree.

STABILITY_REPORT 2026-11-06 found ~600 source files (scripts, tests, decision_engine, prospecting, root tools) that were never
committed: no history, no restore if one is deleted or overwritten. They stay untracked on purpose (the public repository must not
carry them), so they are snapshotted on a LOCAL-ONLY branch, `local/untracked-source`, built with a temporary index:

    python scripts/untracked_source_snapshot.py --once      # loop step, at most once a day; prints one JSON line
    python scripts/untracked_source_snapshot.py --now

A snapshot is skipped (and reported) when a file in it looks like a secret (key-shaped strings). The branch's parent chain keeps history:
each snapshot = previous snapshot tree + changed files. Restore one file: git show local/untracked-source:path/to/file > path.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANCH = "local/untracked-source"
STATE = ROOT / "data" / "untracked_snapshot_state.json"
EXT = re.compile(r"\.(py|js|ps1|bat|sh)$")
SKIP = re.compile(r"^(tests/_endurance_tmp|node_modules|books/(?!_batch\d+_src/)|data/|reports/)")  # product GENERATORS (books/_batch*_src/*.py) are source; the products themselves stay out
WHERE = re.compile(r"^([^/]+\.(py|js|ps1|bat|sh)|scripts/|tests/|decision_engine/|prospecting/|lib/|channels/|ai_capability/|social_distribution/|affiliate/|books/_batch\d+_src/)")
SECRET = re.compile(r"gsk_[A-Za-z0-9]{20,}|bot[0-9]{8,}:[A-Za-z0-9_-]{30,}|sk_live_[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC )?PRIVATE KEY-----[\s\S]{20,}")


def git(*a, root=ROOT, env=None, inp=None):
    return subprocess.run(["git", *a], cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, input=inp)


def wanted(paths):
    return [p for p in paths if EXT.search(p) and not SKIP.match(p) and WHERE.match(p)]


def untracked(root=ROOT):
    found = [l for l in git("ls-files", "-o", "--exclude-standard", root=root).stdout.splitlines() if l.strip()]
    # books/ is git-ignored (paid products stay out of the public repo) so ls-files never lists the product GENERATORS in it;
    # they are source and are added explicitly, but only .py files that git does not already track.
    tracked = set(git("ls-files", "--", "books", root=root).stdout.splitlines())
    for p in sorted(Path(root).glob("books/_batch*_src/*.py")):
        rel = p.relative_to(root).as_posix()
        if rel not in tracked and rel not in found:
            found.append(rel)
    return wanted(found)


def secret_files(files, root=ROOT):
    bad = []
    for f in files:
        try:
            if SECRET.search((Path(root) / f).read_text(encoding="utf-8", errors="ignore")):
                bad.append(f)
        except OSError:
            pass
    return bad


def snapshot(root=ROOT, branch=BRANCH):
    files = untracked(root)
    if not files:
        return {"action": "none", "detail": "no untracked source files"}
    bad = secret_files(files, root)
    if bad:
        return {"action": "blocked", "detail": f"{len(bad)} file(s) look like they contain a secret: {', '.join(bad[:3])}; snapshot skipped"}
    parent = git("rev-parse", "--verify", "-q", branch, root=root).stdout.strip() or git("rev-parse", "HEAD", root=root).stdout.strip()
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(d) / "idx"))
        git("read-tree", parent, root=root, env=env)
        r = git("add", "-f", "--", *files, root=root, env=env)
        if r.returncode != 0:
            return {"action": "failed", "detail": r.stderr.strip()[:160]}
        tree = git("write-tree", root=root, env=env).stdout.strip()
    if tree == git("rev-parse", f"{parent}^{{tree}}", root=root).stdout.strip():
        return {"action": "none", "detail": f"snapshot already current ({len(files)} files)"}
    msg = f"Local-only snapshot of untracked source ({len(files)} files) {datetime.now(timezone.utc).isoformat(timespec='minutes')}\n\nNot for pushing."
    c = git("commit-tree", tree, "-p", parent, "-m", msg, root=root).stdout.strip()
    git("branch", "-f", branch, c, root=root)
    return {"action": "snapshot", "detail": f"{len(files)} untracked source files saved on {branch} ({c[:8]})"}


def run_once(now=None, state=STATE, force=False, root=ROOT):
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()
    try:
        last = json.loads(Path(state).read_text(encoding="utf-8")).get("last_day")
    except (OSError, ValueError):
        last = None
    if last == today and not force:
        return {"action": "none", "detail": f"snapshot already done for {today}"}
    res = snapshot(root)
    if res["action"] in ("snapshot", "none"):
        Path(state).parent.mkdir(parents=True, exist_ok=True)
        Path(state).write_text(json.dumps({"last_day": today, "result": res["detail"]}), encoding="utf-8")
    return res


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        r = run_once(force="--now" in argv)
    except Exception as e:  # noqa: BLE001
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:160]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
