"""Restore a SQLite database file from a backup (no UI)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from app.database.db_backup import backup_database
from app.services.app_logging import get_logger

log = get_logger()


def restore_database_from_backup(backup_file: str | Path, db_path: str | Path) -> Path:
    """Replace ``db_path`` with the contents of ``backup_file`` (a SQLite database file).

    If ``db_path`` already exists, it is copied first via the SQLite backup API to a sibling
    file named ``<stem>_pre_restore_YYYYMMDD_HHMMSS.db`` before being overwritten.

    Callers must **close all open connections** to ``db_path`` before calling (required on
    Windows so the file can be removed/replaced).
    """
    src_backup = Path(backup_file).resolve()
    target = Path(db_path).resolve()

    if src_backup == target:
        raise ValueError("backup_file and db_path must be different paths")

    if not src_backup.is_file():
        raise FileNotFoundError(f"Backup file not found: {src_backup}")

    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        if not target.is_file():
            raise IsADirectoryError(f"Database path is not a file: {target}")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety = target.parent / f"{target.stem}_pre_restore_{stamp}{target.suffix}"
        backup_database(target, safety)
        target.unlink()

    src = sqlite3.connect(str(src_backup))
    try:
        dst = sqlite3.connect(str(target))
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    log.info("SQLite file restore succeeded: %s", target)
    return target
