#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Staged-scope guard (V71, Tier-1 safe).

Prevents recurrence of the V70 139f32a-class mistake: a bare `git commit`
in a tree holding foreign staged entries silently merged 4 files that had
no merge authorization.

Before any commit:
1. read staged files explicitly;
2. compare against the intended change set;
3. abort (no commit) on any mismatch, showing exact paths;
4. never use `git commit -a` or any all-inclusive form (this module only
   accepts an explicit path list -- unlimited `-a` has no code path here);
5. after commit, verify the exact commit scope matches intent.

Read-only until the final verified commit; the commit itself is an
ordinary local commit (reversible via revert/reset while unpushed).
"""
import subprocess

REPO = None  # default: caller cwd; tests inject a temp repo


class ScopeMismatchError(RuntimeError):
    pass


def _git(args, cwd):
    r = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)
    return r


def read_staged(cwd=None):
    r = _git(["diff", "HEAD", "--cached", "--name-only"], cwd)
    return sorted(l.strip() for l in r.stdout.splitlines() if l.strip())


def check_scope(intended, cwd=None):
    """Compare staged set vs intended set. Returns dict; ok only on exact match."""
    staged = set(read_staged(cwd))
    want = set(intended)
    unexpected = sorted(staged - want)
    missing = sorted(want - staged)
    return {"ok": not unexpected and not missing,
            "staged": sorted(staged), "intended": sorted(want),
            "unexpected_staged": unexpected, "missing_intended": missing}


def commit_scope(rev="HEAD", cwd=None):
    r = _git(["show", "--pretty=format:", "--name-only", rev], cwd)
    return sorted(l.strip() for l in r.stdout.splitlines() if l.strip())


def safe_commit(message, intended_paths, cwd=None):
    """Commit exactly intended_paths. Aborts before touching git history
    on any staged/intended mismatch; verifies scope after committing."""
    check = check_scope(intended_paths, cwd)
    if not check["ok"]:
        raise ScopeMismatchError(
            "refusing commit: unexpected_staged=%s missing_intended=%s" % (
                check["unexpected_staged"], check["missing_intended"]))
    r = _git(["commit", "-m", message, "--"] + list(intended_paths), cwd)
    if r.returncode != 0:
        raise RuntimeError("git commit failed: %s" % (r.stderr or r.stdout)[:300])
    sha = _git(["rev-parse", "HEAD"], cwd).stdout.strip()
    actual = commit_scope(sha, cwd)
    if set(actual) != set(intended_paths):
        raise ScopeMismatchError(
            "post-commit scope mismatch: committed=%s intended=%s" % (actual, list(intended_paths)))
    return {"sha": sha, "scope": actual}
