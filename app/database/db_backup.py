"""Isolated SQLite file backup using the sqlite3 backup API."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def backup_database(db_path: str | Path, backup_path: str | Path) -> Path:
    """Copy a SQLite database to ``backup_path`` using ``Connection.backup`` (not file copy)."""
    src_path = Path(db_path).resolve()
    dst_path = Path(backup_path).resolve()
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    src = sqlite3.connect(str(src_path))
    try:
        dst = sqlite3.connect(str(dst_path))
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return dst_path
