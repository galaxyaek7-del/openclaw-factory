"""scripts/fix_site_accessibility_20261030.py on a temporary site: dry run
writes nothing, --apply adds only the two attributes, is idempotent, keeps
line endings, and leaves labelled or hidden fields alone."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fix_site_accessibility_20261030 as fsa  # noqa: E402

PAGE = (b'<html lang="en"><head><title>t</title></head><body><h1>t</h1>\r\n'
        b'<form>\r\n'
        b'<input type="text" name="website" class="hp-field" tabindex="-1" autocomplete="off">\r\n'
        b'<input name="email" type="email" placeholder="Email">\r\n'
        b'<input id="lookupInput" placeholder="req_xxxxxxxx">\r\n'
        b'<input id="code" placeholder="ab_cd">\r\n'
        b'<label for="n">Name</label><input id="n" placeholder="Your name">\r\n'
        b'<label>Q <input name="q" placeholder="Search"></label>\r\n'
        b'<input name="z" placeholder="Zip" aria-label="Postcode">\r\n'
        b'<input type="text" name="website" tabindex="-1" aria-hidden="true">\r\n'
        b'<input type="hidden" name="t" placeholder="x">\r\n'
        b'</form></body></html>\r\n')


class FixSiteAccessibility(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.site = Path(self.dir.name)
        (self.site / "p.html").write_bytes(PAGE)

    def tearDown(self):
        self.dir.cleanup()

    def test_dry_run_writes_nothing(self):
        fsa.main(["--site", str(self.site)])
        self.assertEqual((self.site / "p.html").read_bytes(), PAGE)

    def test_apply_adds_only_the_expected_attributes(self):
        fsa.main(["--site", str(self.site), "--apply"])
        out = (self.site / "p.html").read_bytes()
        self.assertIn(b'tabindex="-1" autocomplete="off" aria-hidden="true">', out)
        self.assertIn(b'placeholder="Email" aria-label="Email">', out)
        self.assertIn(b'placeholder="req_xxxxxxxx" aria-label="Request ID">', out)
        self.assertIn(b'<input id="code" placeholder="ab_cd">', out)          # example value, no name: manual
        self.assertIn(b'<input id="n" placeholder="Your name">', out)         # has <label for>
        self.assertIn(b'<label>Q <input name="q" placeholder="Search"></label>', out)  # wrapped
        self.assertEqual(out.count(b"aria-label="), 3)                        # Email, Request ID, existing Postcode
        self.assertEqual(out.count(b'aria-hidden="true"'), 2)
        self.assertNotIn(b"\n", out.replace(b"\r\n", b""))                     # line endings kept
        fsa.main(["--site", str(self.site), "--apply"])
        self.assertEqual((self.site / "p.html").read_bytes(), out)             # idempotent

    def test_check_reports_fewer_warnings_after_the_repair(self):
        import check
        before = check.check_path(self.site)["warnings"]
        fsa.run(self.site, apply=True)
        after = check.check_path(self.site)["warnings"]
        self.assertLess(after, before)


if __name__ == "__main__":
    unittest.main()
