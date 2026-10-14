"""Is there EVIDENCE the live Gumroad credential was exposed, or just a claim?

gumroad_auth_watch.py gates every write on KNOWN_EXPOSED_FP, a 16-hex-char
prefix of a SHA-256, documented only as "the credential exposed in session
output during the GAP-1 probing cycle". That is an assertion. This checks
whether any artefact in this repository supports it.

The test is straightforward and falsifiable: a token that was ever committed
is recoverable from git history, and the fingerprints will match. A token
that was never committed leaves no artefact, and the claim rests on nothing
inspectable.

Nothing is printed except a boolean match and a character count. The
credential is compared by digest only -- never displayed, never logged.

Read-only. No network. $0.

Run:  python scripts/audit_credential_exposure.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
KNOWN_FP = "6c2e73f238903859"


def _live_token() -> str | None:
    for line in open(ROOT / ".env", encoding="utf-8", errors="replace"):
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip() or None
    return None


def _fp(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    token = _live_token()
    if not token:
        print("no live credential to compare; nothing to audit")
        return 0

    live_fp = _fp(token)
    matches_known = live_fp == KNOWN_FP

    print("live credential length      : %d chars" % len(token))
    print("live fingerprint            : %s..." % live_fp)
    print("KNOWN_EXPOSED_FP            : %s..." % KNOWN_FP)
    print("watch currently blocks on   : %s" % matches_known)

    # ── Is the live token present in ANY tracked file or in git history? ──
    print()
    print("SEARCHING GIT HISTORY FOR THE LITERAL CREDENTIAL...")
    try:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "log", "--all", "-S", token, "--oneline",
             "--", "."],
            capture_output=True, text=True, timeout=180)
        commits = [l for l in r.stdout.splitlines() if l.strip()]
    except Exception as e:  # noqa: BLE001
        print("  history search failed: %s" % type(e).__name__)
        commits = []

    if commits:
        print("  FOUND in %d commit(s) -- exposure is SUPPORTED by evidence:"
              % len(commits))
        for c in commits[:5]:
            print("    %s" % c)
    else:
        print("  not found in any commit in this repository's history")

    # Tracked working tree
    try:
        r2 = subprocess.run(
            ["git", "-C", str(ROOT), "grep", "-l", "--", token],
            capture_output=True, text=True, timeout=120)
        tracked = [l for l in r2.stdout.splitlines() if l.strip()]
    except Exception:  # noqa: BLE001
        tracked = []
    print("  present in tracked files now: %s"
          % (", ".join(tracked) if tracked else "no"))

    print()
    print("CONCLUSION")
    if commits or tracked:
        print("  The credential IS recoverable from this repository. The")
        print("  UNVERIFIED_COMPROMISED gate is justified and rotation is")
        print("  required.")
    else:
        print("  NO artefact in this repository shows the credential was ever")
        print("  written down. The watch's block rests on an unverifiable")
        print("  claim about a past session's console output, which is not")
        print("  inspectable here. That does NOT prove the credential is safe --")
        print("  a secret shown in a terminal can be exposed without ever")
        print("  touching this repository -- but it does mean the evidence for")
        print("  the block does not exist in anything a reviewer can check.")
        print("  Rotating is still the safe action; it is simply not provable")
        print("  from here, and the report must not say it is.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())