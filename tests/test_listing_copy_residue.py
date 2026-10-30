"""Product listing copy must carry no template residue (2026-10-22).

Scans the tracked listing files of every product for unfilled placeholders,
income-guarantee phrases and fused template tokens like the
"APPLICATIONImplementation" leftover found on the live systeme.io guide.
Static, read-only.

    python -m pytest tests/test_listing_copy_residue.py -q
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from affiliate.content_qa import _BANNED_PHRASES, _FUSED_TOKEN  # noqa: E402

PLACEHOLDER = re.compile(r"\[(?:TODO|TBD|INSERT|PLACEHOLDER)[^\]]*\]|\{\{[^}]+\}\}|lorem ipsum", re.I)
# Real names that look fused but are correct; each needs a reason.
KNOWN_NAMES = {
    "CAMAudit": "camaudit.com, a CAM reconciliation service cited as a source in GF-P10-08",
    "QUICKFix": "a competing Gumroad seller's brand in B12-004's competitor evidence",
}


# Files whose names match the listing pattern but hold machine records, not
# listing copy; each needs a reason.
NOT_COPY = {
    "data/listing_page_checks.json": "product_registry page-check results keyed by Gumroad product ids "
                                     "(base64 ids look like fused tokens)",
    "docs/factory/LISTING_REPAIR_PREFLIGHT_2026-10-29.md": "engineering preflight report quoting Gumroad "
                                                           "product ids (base64) next to each repair",
}


def listing_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / p for p in out.splitlines()
            if re.search(r"listing(_copy)?[^/]*\.(md|txt|json)$", p, re.I) and p not in NOT_COPY]


class TestListingCopyResidue(unittest.TestCase):
    def test_no_placeholder_banned_phrase_or_fused_token(self):
        files = listing_files()
        self.assertGreater(len(files), 10, "listing file discovery found almost nothing; pattern is stale")
        problems = []
        for f in files:
            text = f.read_text(encoding="utf-8", errors="replace")
            rel = f.relative_to(ROOT).as_posix()
            problems += [f"{rel}: placeholder {m.group(0)[:30]!r}" for m in PLACEHOLDER.finditer(text)]
            problems += [f"{rel}: banned phrase {p!r}" for p in _BANNED_PHRASES if p in text.lower()]
            problems += [f"{rel}: fused token {t!r}" for t in _FUSED_TOKEN.findall(text) if t not in KNOWN_NAMES]
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
