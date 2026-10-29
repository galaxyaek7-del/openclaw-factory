"""scripts/set_cloudflare_analytics.py: refuses a bad token, writes nothing in a
dry run, inserts one beacon, is idempotent, and --remove restores the bytes.
Temp directory only; the real site is never touched."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import set_cloudflare_analytics as cf  # noqa: E402

TOKEN = "0123456789abcdef0123456789abcdef"


class CloudflareBeacon(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.site = self.dir.name
        os.makedirs(os.path.join(self.site, "sub"))
        self.orig = {
            "a.html": b"<html>\r\n<head>\r\n<title>a</title>\r\n</head>\r\n<body></body></html>\r\n",
            os.path.join("sub", "b.html"): b"<html>\n<head></head>\n<body></body></html>\n",
            "frag.html": b"<p>no head</p>",
        }
        for n, b in self.orig.items():
            with open(os.path.join(self.site, n), "wb") as fh:
                fh.write(b)

    def tearDown(self):
        self.dir.cleanup()

    def read(self, n):
        with open(os.path.join(self.site, n), "rb") as fh:
            return fh.read()

    def run_cf(self, *args):
        return cf.main(list(args) + ["--site", self.site])

    def test_bad_tokens_are_refused(self):
        for bad in ("abc", "<script>", TOKEN + "00", "g" * 32):
            self.assertEqual(self.run_cf("--token", bad, "--apply"), 2, bad)
        self.assertEqual(self.read("a.html"), self.orig["a.html"])

    def test_dry_run_writes_nothing(self):
        self.run_cf("--token", TOKEN)
        for n, b in self.orig.items():
            self.assertEqual(self.read(n), b)

    def test_apply_is_idempotent_and_remove_restores_the_bytes(self):
        self.run_cf("--token", TOKEN, "--apply")
        a = self.read("a.html")
        self.assertEqual(a.count(b"beacon.min.js"), 1)
        self.assertIn(TOKEN.encode(), a)
        self.assertNotIn(b"\n", a.replace(b"\r\n", b""))
        self.assertNotIn(b"\r", self.read(os.path.join("sub", "b.html")))
        other = "f" * 32
        self.run_cf("--token", other, "--apply")
        a = self.read("a.html")
        self.assertEqual(a.count(b"beacon.min.js"), 1)
        self.assertNotIn(TOKEN.encode(), a)
        self.run_cf("--remove", "--apply")
        for n, b in self.orig.items():
            self.assertEqual(self.read(n), b, n)


if __name__ == "__main__":
    unittest.main()
