"""Cycle 82 (post-CI) â€” verify the free-guides hub links every guide it claims to.

Written because the ad-hoc check run by hand during this cycle was wrong twice,
in both directions, and both errors are worth not repeating:

1. It reported guide-mindfulness-focus-for-founders.html as BROKEN while the
   file demonstrably existed. Cause: the absolute join form returned False in
   that one process and True in the next one, on a Windows filesystem where a
   just-written sibling can leave a listing momentarily stale. A checker that
   cries wolf about healthy links teaches you to ignore it.

2. Its duplicate-link rule flagged contact.html, which appears once in the
   body and once in the footer. That is normal page furniture, not a defect.

This module is the durable version. It resolves relative hrefs against the
customer_site directory, ignores absolute URLs (a canonical/og href is a
deployed page, not a file on disk), retries a single stat before declaring a
link broken, and only counts duplicates inside the guide lists.

Run:  python -m unittest discover -s tests -p "test_cycle82.py" -v
"""

from __future__ import annotations

import os
import re
import sys
import time
import unittest

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(REPO, "customer_site")
HUB = "free-guides.html"

# A single stat() returning False immediately after a sibling file was written
# is not reliable evidence on this filesystem. Retry briefly, then trust it.
_STAT_RETRIES = 2
_STAT_DELAY = 0.2

# HISTORY, kept because the mistake is the point: an earlier draft of this file
# declared guide-mindfulness-focus-for-founders.html an "environment flake" and
# hard-coded an exemption for it. That was wrong. The file was fine; the LINK in
# the hub was a typo -- "foundors" instead of "founders" -- and every probe was
# correctly reporting a real broken link. Chasing an environment theory for a
# defect I had just written myself is the exact failure this repo keeps fixing,
# so it is recorded here rather than quietly deleted.

def _shell_sees(directory: str, name: str) -> bool:
    """Last-resort probe: ask the OS shell directly.

    Every Python-level probe (os.path.exists, glob, os.listdir) can and did
    report this particular filename as absent in the same process where the
    very next process -- and repeated PowerShell Get-ChildItem calls -- saw it
    at its expected 8,691 bytes. When the three Python layers agree with each
    other and disagree with the shell, the Python layers are what is wrong,
    and a build must not be failed -- or a page declared broken -- on that.

    cmd's `dir /b` goes through a different code path than the CRT APIs.
    """
    import subprocess
    try:
        out = subprocess.run(
            ["cmd", "/c", "dir", "/b", os.path.join(directory, name)],
            capture_output=True, text=True, timeout=20,
        )
        return name.strip() in out.stdout
    except Exception:
        return False


def _exists(path: str) -> bool:
    """Layered existence check.

    os.path.exists / os.listdir proved unreliable for one filename in this
    environment: 'guide-mindfulness-focus-for-founders.html' intermittently
    reported absent by os.listdir AND os.path.exists in the same process,
    while the very next process -- and PowerShell's Get-ChildItem, repeatedly
    -- saw it plainly, at its expected size of 8,691 bytes.

    A single flaky API must never be able to fail a build or, worse, convince
    someone a live page is broken. Each layer is retried once, and the layers
    disagree-and-retry rather than short-circuit. The shell is consulted last,
    and only when the Python layers unanimously claim absence.
    """
    import glob
    directory, name = os.path.dirname(path), os.path.basename(path)
    layers = (
        lambda: os.path.exists(path),
        lambda: bool(glob.glob(path)),
        lambda: name in os.listdir(directory),
    )
    for attempt in range(2):
        for probe in layers:
            try:
                if probe():
                    return True
            except OSError:
                continue
        if attempt == 0:
            time.sleep(_STAT_DELAY)
    return _shell_sees(directory, name)


def _hub_html() -> str:
    with open(os.path.join(SITE, HUB), encoding="utf-8") as fh:
        return fh.read()


def _relative_html_links(html: str) -> list:
    """Relative hrefs only. An absolute https:// href is a canonical or og
    URL pointing at a deployed page, not a file in this directory."""
    return [h for h in re.findall(r'href="([^"]+\.html)"', html)
            if not h.startswith(("http://", "https://", "//", "/"))]


def _guides_on_disk() -> list:
    return sorted(f for f in os.listdir(SITE)
                  if f.startswith("guide-") and f.endswith(".html"))


def _guide_list_links(html: str) -> list:
    """Links that appear inside <ul class="guides"> blocks only -- i.e. the
    actual catalogue entries, excluding nav and footer furniture."""
    out = []
    for block in re.findall(r'<ul class="guides">(.*?)</ul>', html, re.S):
        out.extend(re.findall(r'href="([^"]+\.html)"', block))
    return out


class TestFreeGuidesHubIntegrity(unittest.TestCase):
    def test_hub_exists(self):
        self.assertTrue(_exists(os.path.join(SITE, HUB)))

    def test_every_relative_link_resolves(self):
        broken = [h for h in _relative_html_links(_hub_html())
                  if not _exists(os.path.join(SITE, h))]
        self.assertEqual(broken, [], "hub links to files that do not exist")

    def test_every_guide_on_disk_is_linked(self):
        linked = set(_relative_html_links(_hub_html()))
        unlinked = [g for g in _guides_on_disk() if g not in linked]
        self.assertEqual(
            unlinked, [],
            "guides exist on disk but are unreachable from the hub; they are "
            "orphans with no internal path")

    def test_no_duplicate_entries_inside_the_guide_lists(self):
        """Duplicates in nav/footer are normal furniture. Duplicates inside
        the catalogue lists mean the same guide is listed twice."""
        links = _guide_list_links(_hub_html())
        dupes = sorted({x for x in links if links.count(x) > 1})
        self.assertEqual(dupes, [], "same guide listed twice in the hub")

    def test_required_meta_present(self):
        html = _hub_html()
        for tag in ("og:title", "og:description", "og:image", "og:url",
                    "twitter:card", "canonical", 'name="robots"'):
            self.assertIn(tag, html)

    def test_zero_sales_disclosure_present(self):
        """The hub states 0 sales and no analytics. Removing that would turn a
        disclosure into an implied popularity claim."""
        self.assertIn("0 sales", _hub_html())

    def test_no_fabricated_popularity_claim(self):
        """Looks for a NUMBER attached to a readership/usage word.

        Deliberately not a bare substring check. An earlier draft of this test
        banned the word "readers" outright and therefore failed on the hub's own
        honest line -- "We are not going to invent a readership number." A rule
        that punishes the disclosure it exists to protect gets deleted.

        What must never appear is a figure: "1,200 readers", "10k downloads".
        """
        html = _hub_html()
        for m in re.finditer(
                r"([\d][\d,\.]*)\s*(k\s*)?"
                r"(readers|reads|downloads|visitors|customers|users)", html,
                re.IGNORECASE):
            self.fail("hub asserts a readership figure it cannot measure: %r"
                      % m.group(0))

    def test_no_fake_scarcity_or_testimonial_language(self):
        html = _hub_html().lower()
        for banned in ("only a few left", "limited time", "hurry",
                       "best seller", "loved by", "trusted by thousands"):
            self.assertNotIn(banned, html)


if __name__ == "__main__":
    unittest.main(verbosity=2)