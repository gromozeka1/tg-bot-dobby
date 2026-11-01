from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from dobby.config import PROJECT_ROOT, get_settings

BACKUP_PREFIX = "dobby-"


def database_path(database_url: str) -> Path:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        raise ValueError("Database backups are currently supported only for SQLite.")
    if not url.database or url.database == ":memory:":
        raise ValueError("A file-backed SQLite database is required for backups.")
    path = Path(url.database)
    return path if path.is_absolute() else PROJECT_ROOT / path


def backup_database(
    source: Path,
    backup_dir: Path,
    *,
    keep: int = 14,
    now: datetime | None = None,
) -> Path:
    if keep < 1:
        raise ValueError("At least one backup must be retained.")
    if not source.is_file():
        raise FileNotFoundError(f"Database file does not exist: {source}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    now = now or datetime.now(UTC)
    timestamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = backup_dir / f"{BACKUP_PREFIX}{timestamp}.sqlite3"
    temporary = destination.with_suffix(".sqlite3.tmp")
    try:
        with closing(sqlite3.connect(source)) as source_connection:
            with closing(sqlite3.connect(temporary)) as backup_connection:
                source_connection.backup(backup_connection)
                result = backup_connection.execute("PRAGMA quick_check").fetchone()
                if result is None or result[0] != "ok":
                    raise sqlite3.DatabaseError(f"Backup integrity check failed: {result}")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)

    backups = sorted(
        backup_dir.glob(f"{BACKUP_PREFIX}*.sqlite3"),
        key=lambda path: path.name,
        reverse=True,
    )
    for old_backup in backups[keep:]:
        old_backup.unlink()
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and verify a SQLite online backup.")
    parser.add_argument("--keep", type=int, default=14, help="Number of backups to retain.")
    args = parser.parse_args()

    settings = get_settings()
    source = database_path(settings.sync_database_url)
    destination = backup_database(source, settings.backups_dir, keep=args.keep)
    print(f"Verified backup created: {destination}")


if __name__ == "__main__":
    main()
