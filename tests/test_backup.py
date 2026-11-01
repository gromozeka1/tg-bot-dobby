from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from scripts.backup_db import backup_database, database_path


def _create_database(path: Path, value: str) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES (?)", (value,))


def test_backup_contains_consistent_sqlite_data(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    backup_dir = tmp_path / "backups"
    _create_database(source, "saved")

    result = backup_database(
        source,
        backup_dir,
        now=datetime(2026, 11, 1, tzinfo=UTC),
    )

    with sqlite3.connect(result) as connection:
        assert connection.execute("PRAGMA quick_check").fetchone() == ("ok",)
        assert connection.execute("SELECT value FROM sample").fetchone() == ("saved",)
    assert list(backup_dir.glob("*.tmp")) == []


def test_backup_includes_committed_wal_data(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    backup_dir = tmp_path / "backups"
    connection = sqlite3.connect(source)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('wal-data')")
        connection.commit()

        result = backup_database(source, backup_dir)

        with sqlite3.connect(result) as backup:
            assert backup.execute("SELECT value FROM sample").fetchone() == ("wal-data",)
    finally:
        connection.close()


def test_backup_retention_removes_oldest_backups(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    backup_dir = tmp_path / "backups"
    _create_database(source, "saved")
    start = datetime(2026, 11, 1, tzinfo=UTC)

    for offset in range(3):
        backup_database(source, backup_dir, keep=2, now=start + timedelta(days=offset))

    backups = sorted(backup_dir.glob("dobby-*.sqlite3"))
    assert len(backups) == 2
    assert backups[-1].name.endswith("20261103T000000000000Z.sqlite3")


def test_database_path_rejects_non_sqlite_urls() -> None:
    with pytest.raises(ValueError, match="only for SQLite"):
        database_path("postgresql://localhost/dobby")


def test_backup_requires_existing_database(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        backup_database(tmp_path / "missing.sqlite3", tmp_path / "backups")
