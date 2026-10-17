"""Master Sprint Plan C: the EXISTING Search Console inbox watcher.

factory_loop.js maybeDeployGscVerification() watches gsc_inbox/ every tick
and hands a single google*.html file to scripts/deploy_gsc_verification.py
--inbox. No second watcher was built; these tests pin the two halves.

Neither test touches the real gsc_inbox/ (the live factory loop watches it):
the Python half runs against a temp inbox in --dry-run, and the JS half runs
with fs.readdirSync stubbed and spawn made to throw if reached.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "deploy_gsc_verification.py"
GOOD = "google0123456789abcdef.html"


class TestGscWatcher(unittest.TestCase):
    def setUp(self):
        self.inbox = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.inbox, ignore_errors=True)

    def _dry_inbox(self):
        p = subprocess.run([sys.executable, str(SCRIPT), "--inbox", str(self.inbox), "--dry-run"],
                           capture_output=True, text=True, timeout=120, cwd=str(ROOT))
        return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])

    def test_inbox_mode_picks_only_the_google_file_and_writes_nothing(self):
        code, r = self._dry_inbox()
        self.assertEqual(code, 1)
        self.assertIn("no Google verification file", r["error"])
        (self.inbox / "README.md").write_text("drop the file here", encoding="utf-8")
        (self.inbox / GOOD).write_text(f"google-site-verification: {GOOD}", encoding="utf-8")
        code, r = self._dry_inbox()
        self.assertEqual((code, r["success"], r["filename"]), (0, True, GOOD))
        self.assertFalse((ROOT / GOOD).exists())

    def test_js_watcher_holds_on_two_different_files_and_idles_on_none(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        js = r"""
const fs = require('fs');
const cp = require('child_process');
cp.spawn = () => { throw new Error('spawn must not be reached'); };
const realReaddir = fs.readdirSync;
let listing = [];
fs.readdirSync = (d, ...rest) => (String(d).endsWith('gsc_inbox') ? listing : realReaddir(d, ...rest));
const fl = require('./factory_loop.js');
(async () => {
  const out = {};
  listing = ['README.md'];
  out.none = await fl.maybeDeployGscVerification();
  listing = ['google1111111111111111.html', 'google2222222222222222.html'];
  out.two = await fl.maybeDeployGscVerification();
  console.log(JSON.stringify(out));
  process.exit(0);
})().catch(e => { console.log(JSON.stringify({ error: String(e) })); process.exit(0); });
"""
        p = subprocess.run([node, "-e", js], capture_output=True, text=True, encoding="utf-8",
                           timeout=120, cwd=str(ROOT))
        out = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertNotIn("error", out, p.stderr[-500:])
        self.assertEqual(out["none"]["action"], "none")
        self.assertEqual(out["two"]["action"], "held")


if __name__ == "__main__":
    unittest.main()
