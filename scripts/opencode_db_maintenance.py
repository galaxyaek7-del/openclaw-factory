"""Offline maintenance for the opencode session database.

Why this exists: on 2026-10-30 the factory's own health check reported
`disk: 3.1GB free of 254.9GB (1.2%) -> critical` on every tick. The cause was
not this repository (about 1 GB total). It was
`%USERPROFILE%\\.local\\share\\opencode\\opencode.db` at 139.33 GB, because the
`event` table stores a full copy of every streaming `message.part.updated`
payload, so one large tool output costs its own size times the number of
deltas it streamed in (the five largest sessions alone were 73 GB).

The founder approved the remedy explicitly: keep credentials, accounts,
projects and session titles; drop message/part/event history. That is
irreversible for chat history and reversible for nothing else, so this module
is manual-only, defaults to a read-only report, and refuses to run while the
database is still open (a rename of a locked file fails on Windows, which is
the guard).

This is deliberately NOT wired into `factory_loop.js` or any Mission Control
endpoint: the factory must never delete a human's session history on its own.

Usage (close opencode first, then run from a normal terminal):

    python scripts/opencode_db_maintenance.py --report
    python scripts/opencode_db_maintenance.py --apply

`--keep-backup` renames the old database to `<name>.old` instead of deleting
it, which reclaims no space until the founder removes it.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

DEFAULT_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"

# Tables whose only content is conversation history. Dropped by the rebuild.
HISTORY_TABLES = ("message", "part", "event", "session_message", "session_input")


class MaintenanceRefused(RuntimeError):
    """Raised when the rebuild cannot proceed safely."""


def _table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def _count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]


def _payload_estimate(conn: sqlite3.Connection, table: str, rows: int) -> int:
    """Rough payload size from a 2x2000-row sample.

    A full `sum(length(data))` over the real event table reads 100+ GB and
    takes tens of minutes, so the report never does that; it samples the
    oldest and newest rows and scales by the row count. Labelled an estimate
    on purpose.
    """
    cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
    if "data" not in cols or rows == 0:
        return 0
    first = conn.execute(f'SELECT avg(length(data)) FROM (SELECT data FROM "{table}" LIMIT 2000)').fetchone()[0]
    last = conn.execute(
        f'SELECT avg(length(data)) FROM (SELECT data FROM "{table}" ORDER BY rowid DESC LIMIT 2000)'
    ).fetchone()[0]
    samples = [x for x in (first, last) if x is not None]
    if not samples:
        return 0
    return int(sum(samples) / len(samples) * rows)


def report(db_path: Path | str = DEFAULT_DB) -> dict:
    """Read-only description of what a rebuild would keep and drop."""
    path = Path(db_path)
    if not path.is_file():
        raise MaintenanceRefused(f"database not found: {path}")
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=30)
    try:
        tables = _table_names(conn)
        kept = [t for t in tables if t not in HISTORY_TABLES]
        dropped = [t for t in tables if t in HISTORY_TABLES]
        return {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "kept": {t: _count(conn, t) for t in kept},
            "dropped": {
                t: {
                    "rows": _count(conn, t),
                    "payload_bytes": _payload_estimate(conn, t, _count(conn, t)),
                }
                for t in dropped
            },
        }
    finally:
        conn.close()


def _schema_statements(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL "
        "AND name NOT LIKE 'sqlite_%' "
        "ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 "
        "WHEN 'view' THEN 2 ELSE 3 END"
    ).fetchall()
    return [r[0] for r in rows]


def _opencode_running() -> bool | None:
    """True/False when detectable, None when this platform cannot be checked."""
    if os.name == "nt":
        try:
            out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq opencode.exe", "/NH"],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return "opencode.exe" in out.stdout.lower()
    try:
        out = subprocess.run(["pgrep", "-f", "opencode"], capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.returncode == 0


def rebuild(db_path: Path | str = DEFAULT_DB, keep_backup: bool = False) -> dict:
    """Build a fresh database holding every non-history table, then swap it in.

    Refuses (and leaves the original untouched) if opencode is still running,
    if the schema copy fails, or if integrity/foreign-key checks fail.
    """
    path = Path(db_path)
    if not path.is_file():
        raise MaintenanceRefused(f"database not found: {path}")
    if _opencode_running() is True:
        raise MaintenanceRefused(
            "opencode.exe is running; close it completely (all windows/terminals) and retry"
        )
    staging = path.with_name(path.name + ".rebuild")
    if staging.exists():
        staging.unlink()

    src = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=30)
    try:
        tables = _table_names(src)
        schema = _schema_statements(src)
        kept = [t for t in tables if t not in HISTORY_TABLES]
        expected = {t: _count(src, t) for t in kept}

        dst = sqlite3.connect(f"file:{staging.as_posix()}?mode=rwc", uri=True)
        try:
            dst.execute("PRAGMA journal_mode=DELETE")
            dst.execute("PRAGMA foreign_keys=OFF")
            for statement in schema:
                dst.execute(statement)
            dst.execute(
                "ATTACH DATABASE ? AS old", (f"file:{path.as_posix()}?mode=ro",)
            )
            for table in kept:
                dst.execute(f'INSERT INTO main."{table}" SELECT * FROM old."{table}"')
            dst.commit()
            dst.execute("DETACH DATABASE old")

            integrity = dst.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise MaintenanceRefused(f"integrity_check failed on rebuild: {integrity}")
            fk_problems = dst.execute("PRAGMA foreign_key_check").fetchall()
            if fk_problems:
                raise MaintenanceRefused(
                    f"foreign_key_check found {len(fk_problems)} problem(s); first: {fk_problems[0]}"
                )
            for table, rows in expected.items():
                got = _count(dst, table)
                if got != rows:
                    raise MaintenanceRefused(f"{table}: copied {got} rows, expected {rows}")
        finally:
            dst.close()
    finally:
        src.close()

    backup = path.with_name(path.name + ".old")
    if backup.exists():
        staging.unlink()
        raise MaintenanceRefused(
            f"a previous backup already exists at {backup}; remove it before rebuilding again"
        )
    try:
        os.replace(path, backup)
    except OSError as exc:
        staging.unlink(missing_ok=True)
        raise MaintenanceRefused(
            "the database is still open (rename refused); close opencode and retry: "
            f"{exc}"
        ) from exc

    os.replace(staging, path)
    for suffix in ("-wal", "-shm"):
        side = path.with_name(path.name + suffix)
        if side.exists():
            side.unlink()

    new_size = path.stat().st_size
    old_size = backup.stat().st_size
    if keep_backup:
        backup_path = str(backup)
        reclaimed = 0
    else:
        backup.unlink()
        backup_path = None
        reclaimed = old_size - new_size
    return {
        "path": str(path),
        "old_size_bytes": old_size,
        "new_size_bytes": new_size,
        "reclaimed_bytes": reclaimed,
        "backup": backup_path,
        "kept_rows": expected,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default=os.environ.get("OPENCODE_DB") or str(DEFAULT_DB))
    parser.add_argument("--report", action="store_true", help="read-only summary (default)")
    parser.add_argument("--apply", action="store_true", help="perform the rebuild")
    parser.add_argument(
        "--keep-backup",
        action="store_true",
        help="keep the old database as <name>.old instead of deleting it",
    )
    args = parser.parse_args(argv)

    if not args.apply:
        try:
            info = report(args.db)
        except MaintenanceRefused as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
        print(f"database: {info['path']}")
        print(f"size: {info['size_bytes'] / 1e9:.2f} GB")
        print("kept tables:")
        for table, rows in info["kept"].items():
            print(f"  {rows:>9}  {table}")
        print("dropped tables:")
        for table, meta in info["dropped"].items():
            print(
                f"  {meta['rows']:>9}  {table}  "
                f"({meta['payload_bytes'] / 1e9:.2f} GB payload)"
            )
        print("run with --apply to rebuild (irreversible for chat history)")
        return 0

    try:
        result = rebuild(args.db, keep_backup=args.keep_backup)
    except MaintenanceRefused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(f"rebuilt: {result['path']}")
    print(f"old size: {result['old_size_bytes'] / 1e9:.2f} GB")
    print(f"new size: {result['new_size_bytes'] / 1e9:.2f} GB")
    print(f"reclaimed: {result['reclaimed_bytes'] / 1e9:.2f} GB")
    if result["backup"]:
        print(f"backup kept at: {result['backup']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
