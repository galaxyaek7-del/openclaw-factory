"""scripts/backup_local_data.py: gzip copies with a restore check, once a day,
secrets never copied, only its own directories pruned. Temp dirs only."""
import gzip
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import backup_local_data as b  # noqa: E402

NOW = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)


class LocalBackup(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.dest = self.root / "backups"
        (self.root / "data").mkdir()
        (self.root / "data" / "inquiries.jsonl").write_bytes(b'{"a": 1}\n')
        (self.root / "data" / "nostr_key.json").write_text('{"secret": "x"}', encoding="utf-8")
        self.files = ["data/inquiries.jsonl", "data/absent.jsonl", "data/nostr_key.json", ".env"]

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_copies_are_restorable_and_secrets_refused(self):
        r = b.run(NOW, self.root, self.dest, self.files)
        self.assertEqual(r["action"], "backed_up")
        d = self.dest / "local-2026-10-31"
        m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(list(m["files"]), ["data/inquiries.jsonl"])
        self.assertEqual(m["missing"], ["data/absent.jsonl"])
        self.assertEqual(sorted(m["refused_secret"]), [".env", "data/nostr_key.json"])
        self.assertEqual(gzip.decompress((d / m["files"]["data/inquiries.jsonl"]["copy"]).read_bytes()), b'{"a": 1}\n')
        self.assertEqual(b.verify(d), [])

    def test_a_corrupt_copy_is_detected(self):
        b.run(NOW, self.root, self.dest, self.files)
        d = self.dest / "local-2026-10-31"
        (d / "data__inquiries.jsonl.gz").write_bytes(gzip.compress(b"tampered"))
        self.assertEqual(b.verify(d), ["data/inquiries.jsonl: hash mismatch"])

    def test_once_per_day(self):
        self.assertEqual(b.once(NOW, self.root, self.dest, files=self.files)["action"], "backed_up")
        self.assertEqual(b.once(NOW.replace(hour=20), self.root, self.dest, files=self.files)["action"], "none")

    def test_prunes_only_its_own_directories(self):
        other = self.dest / "20261020T000000"
        other.mkdir(parents=True)
        for i in range(16):
            b.run(NOW + timedelta(days=i), self.root, self.dest, self.files, keep=14)
        kept = sorted(p.name for p in self.dest.iterdir())
        self.assertEqual(len([k for k in kept if k.startswith("local-")]), 14)
        self.assertIn("20261020T000000", kept)
        self.assertNotIn("local-2026-10-31", kept)

    def test_the_real_list_names_no_secret_and_the_folder_is_ignored(self):
        self.assertFalse([f for f in b.FILES if b.SECRET.search(f)])
        import subprocess
        r = subprocess.run(["git", "check-ignore", "-q", "--no-index", "data/_backups/local-2026-10-31/x.gz"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
