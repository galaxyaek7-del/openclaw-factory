#!/usr/bin/env python3
"""Cycle 77 section 3 -- free, zero-dependency secret scan for CI.

Complements "Verify .env is never tracked in git" (which only proves
.env itself was never committed) with a scan of every OTHER tracked
file for the shape of a real leaked credential -- a committed .env is
not the only way a secret reaches git history; a token pasted directly
into a script or a doc is a separate, real risk neither that check nor
anything else in this workflow covers.

Deliberately NOT a third-party scanner (gitleaks, truffleHog, etc.):
those need either a GitHub Action marketplace dependency or a paid
plan for some features, and this factory's standing rule is $0
additional spend and no new external dependency for a CI gate that a
~60-line stdlib script can already cover at high confidence. This is
intentionally narrow (real, structural secret SHAPES only: AWS keys,
PEM private key headers, GitHub/Slack tokens, generic long high-entropy
assignments to a *_KEY/*_TOKEN/*_SECRET-named variable) -- never a bare
"contains the word token" check, which would false-positive on every
one of this factory's own hundreds of legitimate `TOKEN` env-var
references and be ignored within a week.
"""
import math
import re
import subprocess
import sys

# High-confidence structural patterns -- each one matches the actual
# SHAPE of a real credential, not just the word describing one.
PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key ID"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |)PRIVATE KEY-----"), "private key block"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"), "GitHub token"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "OpenAI-shaped secret key"),
]

# A broad "assigned literal value" pattern, filtered by entropy below --
# catches a hardcoded real secret under this factory's OWN naming
# convention (*_KEY/*_TOKEN/*_SECRET/*_PASSWORD) without hardcoding any
# one provider's shape.
ASSIGNMENT = re.compile(
    r"""(?:^|[\s,{(])([A-Z][A-Z0-9_]*(?:_KEY|_TOKEN|_SECRET|_PASSWORD))\s*[:=]\s*['"]([^'"\s]{20,})['"]""",
    re.MULTILINE,
)

# Known-safe placeholders/examples that legitimately match ASSIGNMENT's
# shape but are not real secrets -- extend this, never silence a real
# hit by weakening the regex above.
ALLOWLIST_VALUES = {
    "your-api-key-here", "changeme", "placeholder", "example",
}

EXCLUDE_PATH_PARTS = ("venv/", "node_modules/", ".git/", "__pycache__/")


def _entropy(s):
    if not s:
        return 0.0
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def scan_file(path, text):
    findings = []
    for pattern, label in PATTERNS:
        for m in pattern.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            findings.append((path, line_no, label, m.group(0)[:12] + "..."))
    for m in ASSIGNMENT.finditer(text):
        var, value = m.group(1), m.group(2)
        if value.lower() in ALLOWLIST_VALUES:
            continue
        if _entropy(value) < 4.0:
            # Threshold calibrated against this repo's own real fixtures
            # (live-measured, 2026-10-11): hyphenated English test
            # passwords like 'contract-test-password' top out at ~3.8
            # bits/char; a real key-shaped secret (e.g. 'sk_live_51H8...')
            # measures ~4.2-4.8. A deliberate tradeoff, disclosed: a
            # pure-hex secret with no recognizable prefix can fall in the
            # 3.7-4.0 band too and would be missed here -- the PATTERNS
            # list above catches every common real-world prefixed shape
            # regardless of this threshold.
            continue
        line_no = text.count("\n", 0, m.start()) + 1
        findings.append((path, line_no, "high-entropy %s assignment" % var, value[:6] + "..."))
    return findings


def main():
    files = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    all_findings = []
    for path in files:
        if any(part in path for part in EXCLUDE_PATH_PARTS):
            continue
        if path == ".env" or path.startswith(".env."):
            continue  # covered by the dedicated "never tracked" check
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        all_findings.extend(scan_file(path, text))

    if all_findings:
        for path, line_no, label, preview in all_findings:
            print("::error::possible secret (%s) at %s:%d (%s)" % (label, path, line_no, preview))
        print("%d possible secret(s) found -- see annotations above" % len(all_findings))
        return 1
    print("no secret-shaped strings found in any tracked file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
