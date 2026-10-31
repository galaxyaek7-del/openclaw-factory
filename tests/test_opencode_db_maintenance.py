import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import opencode_db_maintenance as m  # noqa: E402

SCHEMA = [
    "CREATE TABLE project (id text PRIMARY KEY, title text NOT NULL)",
    "CREATE TABLE session (id text PRIMARY KEY, project_id text NOT NULL, "
    "title text NOT NULL, FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE)",
    "CREATE TABLE credential (id text PRIMARY KEY, secret text NOT NULL)",
    "CREATE TABLE todo (session_id text NOT NULL, content text NOT NULL)",
    "CREATE TABLE message (id text PRIMARY KEY, session_id text NOT NULL, data text NOT NULL, "
    "FOREIGN KEY (session_id) REFERENCES session(id) ON DELETE CASCADE)",
    "CREATE TABLE part (id text PRIMARY KEY, message_id text NOT NULL, data text NOT NULL)",
    "CREATE TABLE event (id text PRIMARY KEY, aggregate_id text NOT NULL, data text NOT NULL)",
]


def make_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        for statement in SCHEMA:
            conn.execute(statement)
        conn.execute("INSERT INTO project VALUES ('p1', 'factory')")
        conn.execute("INSERT INTO project VALUES ('p2', 'other')")
        for i in range(3):
            conn.execute("INSERT INTO session VALUES (?, 'p1', ?)", (f"s{i}", f"session {i}"))
        conn.execute("INSERT INTO credential VALUES ('c1', 'token-value')")
        conn.execute("INSERT INTO todo VALUES ('s0', 'keep me')")
        blob = "x" * 20000
        for i in range(5):
            conn.execute("INSERT INTO message VALUES (?, ?, ?)", (f"m{i}", "s0", blob))
        for i in range(5):
            conn.execute("INSERT INTO part VALUES (?, ?, ?)", (f"pt{i}", f"m{i}", blob))
        for i in range(10):
            conn.execute("INSERT INTO event VALUES (?, ?, ?)", (f"e{i}", "s0", blob))
        conn.commit()
    finally:
        conn.close()


class TestReport(unittest.TestCase):
    def test_report_counts_history_and_metadata_without_modifying(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "opencode.db"
            make_db(db)
            before = db.stat().st_size

            info = m.report(db)

            self.assertEqual(info["kept"]["session"], 3)
            self.assertEqual(info["kept"]["credential"], 1)
            self.assertEqual(info["dropped"]["message"]["rows"], 5)
            self.assertEqual(info["dropped"]["event"]["rows"], 10)
            self.assertGreater(info["dropped"]["event"]["payload_bytes"], 100000)
            self.assertEqual(db.stat().st_size, before)
            self.assertFalse((Path(tmp) / "opencode.db.rebuild").exists())

    def test_report_on_missing_database_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(m.MaintenanceRefused):
                m.report(Path(tmp) / "nope.db")


class TestRebuild(unittest.TestCase):
    @mock.patch.object(m, "_opencode_running", return_value=False)
    def test_rebuild_keeps_metadata_and_drops_history(self, _running):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "opencode.db"
            make_db(db)
            old_size = db.stat().st_size

            result = m.rebuild(db)

            self.assertEqual(result["kept_rows"]["session"], 3)
            self.assertEqual(result["kept_rows"]["project"], 2)
            self.assertEqual(result["kept_rows"]["credential"], 1)
            self.assertEqual(result["kept_rows"]["todo"], 1)
            self.assertGreater(result["reclaimed_bytes"], 0)
            self.assertLess(result["new_size_bytes"], old_size)
            self.assertFalse((Path(tmp) / "opencode.db.old").exists())
            self.assertFalse((Path(tmp) / "opencode.db.rebuild").exists())

            conn = sqlite3.connect(str(db))
            try:
                self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
                self.assertEqual(conn.execute("SELECT secret FROM credential").fetchone()[0], "token-value")
                self.assertEqual(conn.execute("SELECT count(*) FROM session").fetchone()[0], 3)
                existing = {
                    r[0]
                    for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                }
                for table in m.HISTORY_TABLES:
                    if table not in existing:
                        continue
                    self.assertEqual(
                        conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0],
                        0,
                        f"{table} should be empty after rebuild",
                    )
            finally:
                conn.close()

    @mock.patch.object(m, "_opencode_running", return_value=False)
    def test_keep_backup_preserves_old_file(self, _running):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "opencode.db"
            make_db(db)
            result = m.rebuild(db, keep_backup=True)
            backup = Path(result["backup"])
            self.assertTrue(backup.is_file())
            self.assertEqual(result["reclaimed_bytes"], 0)

    @mock.patch.object(m, "_opencode_running", return_value=False)
    def test_refuses_when_previous_backup_exists(self, _running):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "opencode.db"
            make_db(db)
            (Path(tmp) / "opencode.db.old").write_bytes(b"stale")
            with self.assertRaises(m.MaintenanceRefused):
                m.rebuild(db)
            self.assertFalse((Path(tmp) / "opencode.db.rebuild").exists())
            self.assertEqual(m.report(db)["kept"]["session"], 3)


    @mock.patch.object(m, "_opencode_running", return_value=True)
    def test_refuses_while_opencode_is_running(self, _running):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "opencode.db"
            make_db(db)
            before = db.stat().st_size
            with self.assertRaises(m.MaintenanceRefused):
                m.rebuild(db)
            self.assertEqual(db.stat().st_size, before)
            self.assertFalse((Path(tmp) / "opencode.db.rebuild").exists())


class TestCli(unittest.TestCase):
    def test_report_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "opencode.db"
            make_db(db)
            self.assertEqual(m.main(["--report", "--db", str(db)]), 0)

    def test_missing_database_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(m.main(["--report", "--db", str(Path(tmp) / "nope.db")]), 2)


if __name__ == "__main__":
    unittest.main()
