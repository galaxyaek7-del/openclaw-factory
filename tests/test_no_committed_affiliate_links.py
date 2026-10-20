#!/usr/bin/env python3
"""Fail if a real tracked affiliate link is committed.

The systeme.io URL embeds the partner id. The repository is public. A source
draft may keep a placeholder; only a rendered, gitignored file may hold the
real link.

This scans HEAD (what is actually committed), not the working tree, and matches
the real id shape (an optional "sa", then at least 30 lowercase hex characters, after "sa="). Test fixtures use
uppercase "saTEST..." and do not match.

One legacy file is allowlisted, dated, and disclosed. The allowlist asserts the
file still exists, so fixing the page forces the entry to be removed rather
than silently staying forever.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Pre-existing exposure: the real link has been in this public page since
# commit e341d28 (~2026-08), before the never-commit rule was enforced.
# The id is already public in git history; removing the line does not
# un-expose it. Rotation is a founder action.
LEGACY_ALLOWED = {
    "customer_site/guide-systemeio-affiliate.html": "2026-10-20: pre-existing since e341d28; rotate the id before removing this entry",
}

REAL_LINK_RE = re.compile(r"sa=(sa)?[0-9a-f]{30,}\b")


def committed_hits():
    done = subprocess.run(
        ["git", "grep", "-nE", REAL_LINK_RE.pattern, "HEAD"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    # git grep exits 1 when there is no match; that is a clean result.
    if done.returncode not in (0, 1):
        raise RuntimeError(done.stderr.strip() or "git grep failed")
    hits = []
    for line in (done.stdout or "").splitlines():
        _, path, lineno, text = line.split(":", 3)
        hits.append((path, int(lineno), text))
    return hits


def test_no_new_real_affiliate_link_is_committed():
    hits = committed_hits()
    unexpected = [h for h in hits if h[0] not in LEGACY_ALLOWED]
    assert not unexpected, (
        "real affiliate link committed in %s; render it into a gitignored file instead"
        % ", ".join("%s:%d" % (h[0], h[1]) for h in unexpected))


def test_the_known_exposure_is_still_the_only_exception_and_is_disclosed():
    hits = committed_hits()
    paths = {h[0] for h in hits}
    assert paths == set(LEGACY_ALLOWED), (
        "the legacy allowlist no longer matches reality; remove the entry once the page is fixed. "
        "found: %s" % sorted(paths))
    assert all(reason.startswith("2026-10-20") for reason in LEGACY_ALLOWED.values())
