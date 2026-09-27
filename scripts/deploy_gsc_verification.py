#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deploy a founder-supplied Google Search Console HTML verification file.

Galaxy Forge runs its public site on GitHub Pages (project site:
https://galaxyaek7-del.github.io/openclaw-factory/). Google's HTML-file
ownership method requires the exact file Google generated to be served at
the property root -- i.e. this repo's root -- byte-exact, then a human
clicks Verify inside Search Console.

What this script automates (everything technically permissible):
  validate filename/content -> secret-scan -> byte-exact copy to repo root
  -> git add ONLY that file -> commit -> push (no force) -> verify live
  URL returns 200 with the token -> append evidence row.

What it NEVER does: invent a token, modify the token, touch any other
file, force-push, rewrite history, or claim Google ownership verified
(the human Verify click + Google confirmation remain a Founder Gate).

Usage:
  python scripts/deploy_gsc_verification.py --file <path> [--dry-run]
                                            [--inbox DIR] [--wait-secs N]
--dry-run performs validation only (steps 1-3): zero disk/repo/network
mutation outside reading the candidate file.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

FACTORY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES_BASE = "https://galaxyaek7-del.github.io/openclaw-factory"
FILENAME_RE = re.compile(r"^google[a-z0-9]+\.html$")
MAX_BYTES = 5 * 1024
# A verification file must never smuggle credentials. These patterns are
# deliberately broad: a false positive only asks the founder to re-check,
# while a false negative could publish a secret to a public repo.
SECRET_PATTERNS = [
    r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bxox[baprs]-[A-Za-z0-9-]+\b",
    r"\bghp_[A-Za-z0-9]{20,}\b",
    r"\bsk-(live|test)-[A-Za-z0-9]+\b",
    r"(?i)(api[_-]?key|passwd|password)\s*[:=]\s*\S{8,}",
]


def fail(msg):
    print(json.dumps({"success": False, "error": msg}, ensure_ascii=False))
    return 1


def run_git(args):
    p = subprocess.run(["git", "-C", FACTORY_DIR] + args,
                       capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), (p.stderr or "")[:300]))
    return p.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None)
    ap.add_argument("--inbox", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wait-secs", type=int, default=150)
    a = ap.parse_args()

    candidate = a.file
    if not candidate and a.inbox:
        cands = [os.path.join(a.inbox, f) for f in sorted(os.listdir(a.inbox))
                 if FILENAME_RE.match(f)]
        candidate = cands[0] if cands else None
    if not candidate or not os.path.isfile(candidate):
        return fail("no Google verification file found (use --file PATH or --inbox DIR)")

    fname = os.path.basename(candidate)
    if not FILENAME_RE.match(fname):
        return fail("filename %r does not match Google's google<token>.html format" % fname)
    with open(candidate, "rb") as fh:
        raw = fh.read()
    if not raw or len(raw) > MAX_BYTES:
        return fail("file size %d bytes is outside the sane range for a verification file" % len(raw))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return fail("file is not valid UTF-8")
    if "google-site-verification" not in text:
        return fail("content lacks the google-site-verification marker -- not a Google file")
    for pat in SECRET_PATTERNS:
        if re.search(pat, text):
            return fail("secret-like pattern matched (%s) -- refusing to publish" % pat)
    if a.dry_run:
        print(json.dumps({"success": True, "dry_run": True, "filename": fname,
                          "bytes": len(raw), "checks": ["filename", "utf8", "marker", "secrets"]},
                         ensure_ascii=False))
        return 0

    dest = os.path.join(FACTORY_DIR, fname)
    if os.path.exists(dest):
        with open(dest, "rb") as fh:
            if fh.read() == raw:
                print(json.dumps({"success": True, "already_deployed": True,
                                  "filename": fname}, ensure_ascii=False))
                return 0
        return fail("a different file already exists at repo root under that name -- founder decision required")
    with open(dest, "wb") as fh:
        fh.write(raw)
    staged = run_git(["add", fname])
    names = run_git(["diff", "--cached", "--name-only"]).splitlines()
    if names != [fname]:
        run_git(["reset", "HEAD", fname])
        os.remove(dest)
        return fail("staged set is not exactly the verification file -- aborted and rolled back")
    run_git(["commit", "-m", "Add Google Search Console verification file"])
    sha = run_git(["rev-parse", "HEAD"])
    push = subprocess.run(["git", "-C", FACTORY_DIR, "push", "origin", "main"],
                          capture_output=True, text=True, timeout=180)
    if push.returncode != 0:
        return fail("git push failed: %s" % ((push.stderr or "")[:300]))
    url = PAGES_BASE + "/" + fname
    # P1: poll-until-live instead of a fixed sleep. Pages builds take
    # ~1-4 min; continuing the moment the token is observable saves the
    # remainder of the window. Bounded: 10 polls x 30s, then fail loud.
    token_m = re.search(r'content="([^"]+)"', text)
    token = token_m.group(1) if token_m else None
    budget = max(30, a.wait_secs)
    status, body, waited = None, "", 0
    while True:
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                body = r.read().decode("utf-8", errors="replace")
                status = r.status
        except Exception as e:
            status, body = None, ""
            if waited >= budget:
                return fail("pushed as %s but live URL check failed: %s" % (sha, repr(e)[:200]))
        if status == 200 and (not token or token in body):
            break
        if waited >= budget:
            break
        time.sleep(30)
        waited += 30
    if status != 200 or (token and token not in body):
        return fail("live URL did not return the token after %ds (http=%s)" % (waited, status))
    print(json.dumps({"success": True, "commit": sha, "url": url,
                      "http": status, "token_present": True,
                      "note": "file deployed; GOOGLE_OWNERSHIP_VERIFIED stays UNKNOWN until the human Verify click"},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
