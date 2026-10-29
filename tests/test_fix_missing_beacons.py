"""scripts/fix_missing_beacons.py: a dry run writes nothing, --apply adds the
observable beacon once, keeps line endings, and gf-pageview.js counts as a
beacon. Temp directory only."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fix_missing_beacons as fmb  # noqa: E402


class Beacons(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.site = self.dir.name
        self.pages = {
            "bare.html": b"<html>\r\n<head>\r\n<title>x</title>\r\n</head>\r\n<body></body>\r\n</html>\r\n",
            "lf.html": b"<html>\n<head></head>\n<body></body>\n</html>\n",
            "has.html": b'<html><head><script src="assets/gf-pageview.js" defer></script></head></html>',
            "nohead.html": b"<p>fragment</p>",
        }
        for n, b in self.pages.items():
            with open(os.path.join(self.site, n), "wb") as fh:
                fh.write(b)

    def tearDown(self):
        self.dir.cleanup()

    def read(self, n):
        with open(os.path.join(self.site, n), "rb") as fh:
            return fh.read()

    def test_dry_run_writes_nothing(self):
        fmb.main(["--site", self.site])
        for n, b in self.pages.items():
            self.assertEqual(self.read(n), b, n)

    def test_apply_adds_the_tag_once_and_keeps_line_endings(self):
        fmb.main(["--site", self.site, "--apply"])
        bare = self.read("bare.html")
        self.assertEqual(bare.count(fmb.TAG), 1)
        self.assertNotIn(b"\n", bare.replace(b"\r\n", b""))
        self.assertEqual(bare.replace(fmb.TAG + b"\r\n", b""), self.pages["bare.html"])
        self.assertNotIn(b"\r", self.read("lf.html"))
        self.assertEqual(self.read("has.html"), self.pages["has.html"])
        self.assertEqual(self.read("nohead.html"), self.pages["nohead.html"])
        fmb.main(["--site", self.site, "--apply"])
        self.assertEqual(self.read("bare.html").count(fmb.TAG), 1)


if __name__ == "__main__":
    unittest.main()
