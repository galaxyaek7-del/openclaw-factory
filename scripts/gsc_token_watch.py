#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — GSC token local intake (one-shot).

Founder pastes ONLY the google-site-verification content token into
.gsc_inbox/token.txt (local file, gitignored, never committed), then runs:
    python scripts/gsc_token_watch.py

Pipeline: validate -> secret-scan -> inject into UTF-16 index.html ->
single-file commit -> push -> live-token verify -> READY_FOR_GOOGLE_VERIFY.

Security: token never printed, never logged, never in ledger, never in git.
Inbox file is DELETED after successful deploy. Dry-run closed: this script
is new code, verified once at build time with synthetic tokens only.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

FACTORY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(FACTORY_DIR, ".gsc_inbox", "token.txt")
TARGET = os.path.join(FACTORY_DIR, "index.html")
PAGES_BASE = "https://galaxyaek7-del.github.io/openclaw-factory"
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
SECRET_PATTERNS = [
    r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bxox[baprs]-[A-Za-z0-9-]+\b",
    r"\bghp_[A-Za-z0-9]{20,}\b",
    r"\bsk-(live|test)-[A-Za-z0-9]+\b",
    r"gsk_[A-Za-z0-9]{10,}",
    r"pdl_(live|test)_apikey",
]


def fail(msg):
    print(json.dumps({"success": False, "error": msg}, ensure_ascii=False))
    return 1


def run_git(args):
    p = subprocess.run(["git", "-C", FACTORY_DIR] + args,
                       capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError("git failed: %s" % ((p.stderr or "")[:200]))
    return p.stdout.strip()


def main():
    if not os.path.isfile(INBOX):
        return fail("inbox empty: paste ONLY the content token into .gsc_inbox/token.txt, then re-run")
    with open(INBOX, "r", encoding="utf-8") as fh:
        raw_inbox = fh.read().strip()
    m = re.search(r'content="([^"]+)"', raw_inbox)
    token = m.group(1).strip() if m else raw_inbox
    if not TOKEN_RE.match(token):
        return fail("token format invalid (expected 16-128 chars A-Za-z0-9_-)")
    for pat in SECRET_PATTERNS:
        if re.search(pat, token):
            return fail("token matches a secret pattern -- refusing")

    with open(TARGET, "rb") as fh:
        raw = fh.read()
    try:
        text = raw.decode("utf-16")
    except UnicodeDecodeError:
        return fail("index.html is not UTF-16 -- manual review required")
    if "google-site-verification" in text:
        return fail("a verification tag already exists -- manual review required")
    m = re.search(r"<head[^>]*>", text, re.I)
    if not m:
        return fail("no <head> in index.html -- manual review required")
    tag = '<meta name="google-site-verification" content="%s" />' % token
    out = text.replace(m.group(0), m.group(0) + "\n    " + tag, 1)
    with open(TARGET, "wb") as fh:
        fh.write(out.encode("utf-16"))

    try:
        run_git(["add", "index.html"])
        names = run_git(["diff", "--cached", "--name-only"]).splitlines()
        if names != ["index.html"]:
            raise RuntimeError("staged set is not exactly index.html")
        run_git(["commit", "-m", "Add Google Search Console verification tag"])
        sha = run_git(["rev-parse", "HEAD"])
        push = subprocess.run(["git", "-C", FACTORY_DIR, "push", "origin", "main"],
                              capture_output=True, text=True, timeout=180)
        if push.returncode != 0:
            raise RuntimeError("push failed: %s" % ((push.stderr or "")[:200]))
    except Exception as e:
        run_git(["reset", "HEAD", "index.html"])
        run_git(["checkout", "--", "index.html"])
        return fail("deploy failed, rolled back: %s" % str(e)[:200])

    import time
    time.sleep(150)
    try:
        with urllib.request.urlopen(PAGES_BASE + "/index.html", timeout=60) as r:
            body = r.read().decode("utf-8", errors="replace")
            status = r.status
    except Exception as e:
        return fail("pushed %s but live check failed: %s" % (sha, repr(e)[:150]))
    if status != 200 or token not in body:
        return fail("live page lacks the token (http=%s) -- check Pages build" % status)

    try:
        os.remove(INBOX)
    except OSError:
        pass
    print(json.dumps({"success": True, "commit": sha,
                      "state": "READY_FOR_GOOGLE_VERIFY",
                      "next": "founder presses VERIFY in Search Console"},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
